from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from accounts.models import StockAlert
from accounts.nepse_utils import get_all_stocks


class Command(BaseCommand):
    help = 'Check stock alerts and send email notifications'

    def handle(self, *args, **kwargs):
        self.stdout.write('Checking alerts...')

        try:
            stocks = get_all_stocks()
        except Exception as e:
            self.stdout.write(f'Failed to fetch stocks: {e}')
            return

        stock_prices = {}
        for stock in stocks:
            symbol = stock['symbol']
            ltp = stock.get('ltp', 0)
            stock_prices[symbol] = ltp

        alerts = StockAlert.objects.filter(status='active')
        triggered = 0

        for alert in alerts:
            symbol = alert.stock_symbol
            ltp = stock_prices.get(symbol, 0)

            if ltp == 0:
                continue

            should_trigger = False

            if alert.alert_type == 'above' and alert.target_price:
                should_trigger = ltp >= alert.target_price
            elif alert.alert_type == 'below' and alert.target_price:
                should_trigger = ltp <= alert.target_price
            elif alert.alert_type == 'between':
                if alert.price_low and alert.price_high:
                    should_trigger = alert.price_low <= ltp <= alert.price_high

            if should_trigger:
                try:
                    send_mail(
                        subject=f'NEPSE Alert: {symbol} triggered!',
                        message=(
                            f'Your alert for {symbol} has been triggered.\n'
                            f'Current LTP: Rs. {ltp}\n'
                            f'Alert Type: {alert.alert_type}\n'
                            f'Target Price: Rs. {alert.target_price or ""}\n'
                            f'Notes: {alert.notes or ""}'
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[alert.user.email],
                        fail_silently=False,
                    )
                    alert.status = 'triggered'
                    alert.save()
                    triggered += 1
                    self.stdout.write(f'Alert triggered for {symbol} — email sent to {alert.user.email}')
                except Exception as e:
                    self.stdout.write(f'Email failed for {symbol}: {e}')

        self.stdout.write(f'Done. {triggered} alerts triggered.')