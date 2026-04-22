from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from accounts.models import StockAlert
from accounts.nepse_utils import get_all_stocks
from collections import defaultdict


class Command(BaseCommand):
    help = 'Check stock alerts and send email notifications'

    def handle(self, *args, **kwargs):
        self.stdout.write('=' * 50)
        self.stdout.write('🔍 NEPSE Alert Checker Started')
        self.stdout.write('=' * 50)

        # ── Step 1: Fetch live market data ──────────────────
        try:
            stocks = get_all_stocks()
            self.stdout.write(f'✅ Fetched {len(stocks)} stocks from NEPSE API')
        except Exception as e:
            self.stdout.write(f'❌ Failed to fetch stocks: {e}')
            return

        # ── Step 2: Build symbol → LTP lookup ───────────────
        stock_prices = {}
        for stock in stocks:
            symbol = stock['symbol'].upper().strip()
            ltp = stock.get('ltp', 0)
            stock_prices[symbol] = ltp

        # ── Step 3: Load all active alerts ──────────────────
        alerts = StockAlert.objects.filter(status='active').select_related('user')
        total_active = alerts.count()
        self.stdout.write(f'📋 Found {total_active} active alert(s) in database')

        if total_active == 0:
            self.stdout.write('ℹ️  No active alerts — nothing to check.')
            self.stdout.write('=' * 50)
            return

        # ── Step 4: Evaluate each alert ─────────────────────
        # Group by user so we send ONE email per user (avoids spam filters)
        user_triggered_alerts = defaultdict(list)

        for alert in alerts:
            symbol = alert.stock_symbol.upper().strip()
            ltp = stock_prices.get(symbol)

            if ltp is None:
                self.stdout.write(
                    f'  ⚠️  SKIP [{symbol}] — not found in market data '
                    f'(stored as "{alert.stock_symbol}", check spelling)'
                )
                continue

            if ltp == 0:
                self.stdout.write(f'  ⚠️  SKIP [{symbol}] — LTP is 0')
                continue

            should_trigger = False
            condition_str = ''

            if alert.alert_type == 'above' and alert.target_price is not None:
                should_trigger = ltp >= float(alert.target_price)
                condition_str = f'LTP {ltp} >= target {alert.target_price}'

            elif alert.alert_type == 'below' and alert.target_price is not None:
                should_trigger = ltp <= float(alert.target_price)
                condition_str = f'LTP {ltp} <= target {alert.target_price}'

            elif alert.alert_type == 'between':
                if alert.price_low is not None and alert.price_high is not None:
                    should_trigger = float(alert.price_low) <= ltp <= float(alert.price_high)
                    condition_str = f'{alert.price_low} <= LTP {ltp} <= {alert.price_high}'
                else:
                    self.stdout.write(
                        f'  ⚠️  SKIP [{symbol}] — between alert missing price_low/price_high'
                    )
                    continue

            result = '🔔 TRIGGERED' if should_trigger else '  — not triggered'
            self.stdout.write(f'  {result} [{symbol}] ({alert.alert_type}) — {condition_str}')

            if should_trigger:
                # Mark triggered immediately — prevents re-firing on next cron run
                alert.status = 'triggered'
                alert.triggered_at = timezone.now()
                alert.save(update_fields=['status', 'triggered_at'])

                user_triggered_alerts[alert.user].append({
                    'symbol': symbol,
                    'ltp': ltp,
                    'alert_type': alert.alert_type,
                    'target_price': alert.target_price,
                    'price_low': alert.price_low,
                    'price_high': alert.price_high,
                    'notes': alert.notes,
                })

        # ── Step 5: Send ONE email per user ─────────────────
        total_triggered = sum(len(v) for v in user_triggered_alerts.values())
        self.stdout.write(
            f'\n📧 Sending emails — {total_triggered} alert(s) '
            f'across {len(user_triggered_alerts)} user(s)...'
        )

        for user, triggered_list in user_triggered_alerts.items():
            try:
                self._send_alert_email(user, triggered_list)
                symbols = [a['symbol'] for a in triggered_list]
                self.stdout.write(f'  ✅ Email sent → {user.email} | Alerts: {symbols}')
            except Exception as e:
                self.stdout.write(f'  ❌ Email FAILED → {user.email} | Error: {e}')

        self.stdout.write('=' * 50)
        self.stdout.write(f'✅ Done. {total_triggered} alert(s) triggered.')
        self.stdout.write('=' * 50)

    def _send_alert_email(self, user, triggered_list):
        """Send a single HTML email listing all triggered alerts for this user."""
        count = len(triggered_list)
        subject = (
            f'NEPSE Alert: {triggered_list[0]["symbol"]} triggered!'
            if count == 1
            else f'NEPSE Alert: {count} stocks triggered!'
        )

        # ── Plain text ───────────────────────────────────────
        lines = [
            f'Hello {user.first_name or user.username},',
            '',
            f'{count} alert(s) triggered:',
            '',
        ]
        for i, a in enumerate(triggered_list, 1):
            lines.append(f'{i}. {a["symbol"]} — LTP: Rs. {a["ltp"]}')
            if a['alert_type'] == 'between':
                lines.append(f'   Condition: Between Rs. {a["price_low"]} – Rs. {a["price_high"]}')
            elif a['alert_type'] == 'above':
                lines.append(f'   Condition: Above Rs. {a["target_price"]}')
            else:
                lines.append(f'   Condition: Below Rs. {a["target_price"]}')
            if a['notes']:
                lines.append(f'   Notes: {a["notes"]}')
            lines.append('')
        lines.append('— NEPSE Stock Alert System')
        text_body = '\n'.join(lines)

        # ── HTML rows ────────────────────────────────────────
        rows_html = ''
        notes_items = ''
        for a in triggered_list:
            if a['alert_type'] == 'between':
                condition = f"Between Rs. {a['price_low']} – Rs. {a['price_high']}"
                badge_color, badge_bg = '#7c3aed', '#ede9fe'
            elif a['alert_type'] == 'above':
                condition = f"Above Rs. {a['target_price']}"
                badge_color, badge_bg = '#065f46', '#d1fae5'
            else:
                condition = f"Below Rs. {a['target_price']}"
                badge_color, badge_bg = '#991b1b', '#fee2e2'

            rows_html += f"""
            <tr>
              <td style="padding:14px 16px;border-bottom:1px solid #e5e7eb;">
                <strong style="font-size:15px;color:#111827;">{a['symbol']}</strong>
              </td>
              <td style="padding:14px 16px;border-bottom:1px solid #e5e7eb;">
                <strong style="color:#1e3a5f;">Rs. {a['ltp']}</strong>
              </td>
              <td style="padding:14px 16px;border-bottom:1px solid #e5e7eb;">
                <span style="background:{badge_bg};color:{badge_color};padding:4px 10px;
                             border-radius:12px;font-size:13px;font-weight:600;">
                  {condition}
                </span>
              </td>
              <td style="padding:14px 16px;border-bottom:1px solid #e5e7eb;">
                <span style="background:#d1fae5;color:#065f46;padding:4px 10px;
                             border-radius:12px;font-size:13px;font-weight:600;">✅ Triggered</span>
              </td>
            </tr>"""

            if a['notes']:
                notes_items += f"""
                <div style="background:#fffbeb;border-left:3px solid #f59e0b;
                            padding:10px 14px;margin-top:8px;border-radius:4px;font-size:13px;">
                  <strong>{a['symbol']}:</strong> {a['notes']}
                </div>"""

        notes_section = (
            f'<div style="padding:16px 24px;border-top:1px solid #e5e7eb;">'
            f'<strong style="font-size:13px;color:#374151;">📝 Notes:</strong>'
            f'{notes_items}</div>'
            if notes_items else ''
        )

        html_body = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:620px;margin:30px auto;background:white;
              border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.1);">

    <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);padding:28px 24px;color:white;">
      <div style="font-size:24px;font-weight:700;margin-bottom:4px;">📈 NEPSE Stock Alert</div>
      <div style="font-size:15px;opacity:0.85;">
        Hello {user.first_name or user.username} — your alert(s) have fired!
      </div>
    </div>

    <div style="background:#eff6ff;border-bottom:1px solid #dbeafe;
                padding:14px 24px;color:#1d4ed8;font-size:15px;">
      🔔 <strong>{count} alert(s)</strong> triggered right now
    </div>

    <table style="width:100%;border-collapse:collapse;font-size:14px;">
      <thead>
        <tr style="background:#f9fafb;">
          <th style="padding:12px 16px;text-align:left;color:#6b7280;font-size:13px;border-bottom:2px solid #e5e7eb;">SYMBOL</th>
          <th style="padding:12px 16px;text-align:left;color:#6b7280;font-size:13px;border-bottom:2px solid #e5e7eb;">LTP</th>
          <th style="padding:12px 16px;text-align:left;color:#6b7280;font-size:13px;border-bottom:2px solid #e5e7eb;">CONDITION</th>
          <th style="padding:12px 16px;text-align:left;color:#6b7280;font-size:13px;border-bottom:2px solid #e5e7eb;">STATUS</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>

    {notes_section}

    <div style="background:#f9fafb;padding:20px 24px;border-top:1px solid #e5e7eb;text-align:center;">
      <p style="color:#6b7280;font-size:13px;margin:0 0 8px;">
        Log in to your dashboard to set new alerts or reactivate existing ones.
      </p>
      <div style="color:#9ca3af;font-size:12px;">NEPSE Stock Alert System — Automated Notification</div>
    </div>
  </div>
</body>
</html>"""

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)