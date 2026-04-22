from django.core.management.base import BaseCommand
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from accounts.models import StockAlert
from accounts.nepse_utils import get_all_stocks
from collections import defaultdict


class Command(BaseCommand):
    help = 'Check stock alerts and send email notifications'

    def handle(self, *args, **kwargs):
        self.stdout.write('Checking alerts...')

        try:
            stocks = get_all_stocks()
        except Exception as e:
            self.stdout.write(f'Failed to fetch stocks: {e}')
            return

        # Build price lookup dict
        stock_prices = {}
        for stock in stocks:
            symbol = stock['symbol']
            ltp = stock.get('ltp', 0)
            stock_prices[symbol] = ltp

        self.stdout.write(f'Loaded {len(stock_prices)} stock prices.')

        alerts = StockAlert.objects.filter(status='active').select_related('user')
        self.stdout.write(f'Found {alerts.count()} active alerts.')

        triggered = 0

        # ✅ FIX 1: Group triggered alerts per user so we send ONE email per user
        # with ALL triggered alerts listed — avoids Gmail blocking multiple emails
        user_triggered_alerts = defaultdict(list)

        for alert in alerts:
            symbol = alert.stock_symbol.upper().strip()
            ltp = stock_prices.get(symbol, None)

            # ✅ FIX 2: Log when symbol not found — helps debug missing symbols
            if ltp is None:
                self.stdout.write(f'  SKIP: {symbol} not found in market data.')
                continue

            if ltp == 0:
                self.stdout.write(f'  SKIP: {symbol} has LTP=0.')
                continue

            should_trigger = False

            if alert.alert_type == 'above' and alert.target_price:
                should_trigger = ltp >= float(alert.target_price)
                self.stdout.write(
                    f'  CHECK [{symbol}] LTP={ltp} >= target={alert.target_price}? {should_trigger}'
                )
            elif alert.alert_type == 'below' and alert.target_price:
                should_trigger = ltp <= float(alert.target_price)
                self.stdout.write(
                    f'  CHECK [{symbol}] LTP={ltp} <= target={alert.target_price}? {should_trigger}'
                )
            elif alert.alert_type == 'between':
                if alert.price_low and alert.price_high:
                    should_trigger = float(alert.price_low) <= ltp <= float(alert.price_high)
                    self.stdout.write(
                        f'  CHECK [{symbol}] {alert.price_low} <= LTP={ltp} <= {alert.price_high}? {should_trigger}'
                    )

            if should_trigger:
                # ✅ FIX 3: Mark alert as triggered IMMEDIATELY to prevent re-firing every 5 min
                alert.status = 'triggered'
                alert.save(update_fields=['status'])

                user_triggered_alerts[alert.user].append({
                    'symbol': symbol,
                    'ltp': ltp,
                    'alert_type': alert.alert_type,
                    'target_price': alert.target_price,
                    'price_low': alert.price_low,
                    'price_high': alert.price_high,
                    'notes': alert.notes,
                })
                self.stdout.write(f'  TRIGGERED: {symbol} for user {alert.user.email}')

        # ✅ FIX 4: Send ONE email per user with ALL their triggered alerts
        for user, triggered_list in user_triggered_alerts.items():
            try:
                subject = f'NEPSE Alert: {len(triggered_list)} stock alert(s) triggered!'

                # Plain text version
                text_lines = [
                    f'Hello {user.first_name or user.username},',
                    f'',
                    f'The following {len(triggered_list)} alert(s) have been triggered:',
                    f'',
                ]
                for i, a in enumerate(triggered_list, 1):
                    text_lines.append(f'{i}. {a["symbol"]}')
                    text_lines.append(f'   Current LTP: Rs. {a["ltp"]}')
                    text_lines.append(f'   Alert Type : {a["alert_type"]}')
                    if a['alert_type'] == 'between':
                        text_lines.append(f'   Range      : Rs. {a["price_low"]} - Rs. {a["price_high"]}')
                    else:
                        text_lines.append(f'   Target     : Rs. {a["target_price"]}')
                    if a['notes']:
                        text_lines.append(f'   Notes      : {a["notes"]}')
                    text_lines.append('')

                text_lines.append('Login to your dashboard to manage alerts.')
                text_lines.append('— NEPSE Stock Alert System')

                text_body = '\n'.join(text_lines)

                # HTML version
                html_rows = ''
                for a in triggered_list:
                    if a['alert_type'] == 'between':
                        condition = f'Between Rs. {a["price_low"]} – Rs. {a["price_high"]}'
                    elif a['alert_type'] == 'above':
                        condition = f'Above Rs. {a["target_price"]}'
                    else:
                        condition = f'Below Rs. {a["target_price"]}'

                    color = '#16a34a' if a['alert_type'] == 'above' else '#dc2626'
                    html_rows += f"""
                    <tr>
                        <td style="padding:10px;border-bottom:1px solid #e5e7eb;font-weight:bold;">{a['symbol']}</td>
                        <td style="padding:10px;border-bottom:1px solid #e5e7eb;">Rs. {a['ltp']}</td>
                        <td style="padding:10px;border-bottom:1px solid #e5e7eb;">{condition}</td>
                        <td style="padding:10px;border-bottom:1px solid #e5e7eb;color:{color};">✅ Triggered</td>
                    </tr>
                    """

                html_body = f"""
                <html>
                <body style="font-family:Arial,sans-serif;background:#f9fafb;padding:20px;">
                  <div style="max-width:600px;margin:auto;background:white;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
                    <div style="background:#1e3a5f;padding:20px;color:white;">
                      <h2 style="margin:0;">📈 NEPSE Stock Alert</h2>
                      <p style="margin:5px 0 0;">Hello {user.first_name or user.username}!</p>
                    </div>
                    <div style="padding:20px;">
                      <p style="font-size:16px;">
                        <strong>{len(triggered_list)} alert(s)</strong> have been triggered:
                      </p>
                      <table style="width:100%;border-collapse:collapse;font-size:14px;">
                        <thead>
                          <tr style="background:#f3f4f6;">
                            <th style="padding:10px;text-align:left;">Symbol</th>
                            <th style="padding:10px;text-align:left;">LTP (Rs.)</th>
                            <th style="padding:10px;text-align:left;">Condition</th>
                            <th style="padding:10px;text-align:left;">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {html_rows}
                        </tbody>
                      </table>
                      <p style="margin-top:20px;color:#6b7280;font-size:13px;">
                        Login to your dashboard to set new alerts or reactivate old ones.
                      </p>
                    </div>
                    <div style="background:#f3f4f6;padding:12px;text-align:center;color:#9ca3af;font-size:12px;">
                      NEPSE Stock Alert System — Automated Notification
                    </div>
                  </div>
                </body>
                </html>
                """

                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email],
                )
                msg.attach_alternative(html_body, "text/html")
                msg.send(fail_silently=False)

                triggered += len(triggered_list)
                self.stdout.write(
                    f'✅ Email sent to {user.email} with {len(triggered_list)} alert(s): '
                    f'{[a["symbol"] for a in triggered_list]}'
                )

            except Exception as e:
                self.stdout.write(f'❌ Email failed for {user.email}: {e}')

        self.stdout.write(f'Done. {triggered} alerts triggered across {len(user_triggered_alerts)} user(s).')