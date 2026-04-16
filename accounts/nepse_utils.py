import warnings
warnings.filterwarnings('ignore')
from nepse_scraper import NepseScraper
from datetime import datetime, date
import pytz

# Nepal timezone
NEPAL_TZ = pytz.timezone('Asia/Kathmandu')

def get_nepal_time():
    return datetime.now(NEPAL_TZ)

def is_trading_day():
    now = get_nepal_time()
    # Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4
    # Saturday=5, Sunday=6
    return now.weekday() < 5  # Monday to Friday only

def is_market_open():
    try:
        now = get_nepal_time()
        # Market is closed on Saturday and Sunday
        if now.weekday() >= 5:
            return False
        # Market open 11:00 AM to 3:00 PM NST
        market_open = now.replace(hour=11, minute=0, second=0)
        market_close = now.replace(hour=15, minute=0, second=0)
        return market_open <= now <= market_close
    except Exception as e:
        print(f"Error checking market status: {e}")
        return False

def get_last_trading_day():
    now = get_nepal_time()
    today = now.date()
    weekday = today.weekday()
    # If Saturday go back 1 day to Friday
    if weekday == 5:
        from datetime import timedelta
        today = today - timedelta(days=1)
    # If Sunday go back 2 days to Friday
    elif weekday == 6:
        from datetime import timedelta
        today = today - timedelta(days=2)
    return today.strftime("%A, %B %d %Y")

def get_all_stocks():
    try:
        scraper = NepseScraper(verify_ssl=False)
        stocks = scraper.get_today_price()
        if not stocks:
            return []
        # Add LTP field — use lastUpdatedPrice as LTP
        for stock in stocks:
            stock['ltp'] = stock.get('lastUpdatedPrice') or stock.get('closePrice') or 0
        return stocks
    except Exception as e:
        print(f"Error fetching NEPSE data: {e}")
        return []

def get_stock_by_symbol(symbol):
    try:
        stocks = get_all_stocks()
        for stock in stocks:
            if stock['symbol'] == symbol.upper():
                return stock
        return None
    except Exception as e:
        print(f"Error fetching stock: {e}")
        return None

def get_market_status():
    return is_market_open()

def get_nepse_summary():
    try:
        stocks = get_all_stocks()
        if not stocks:
            return None
        advanced = sum(1 for s in stocks if s['closePrice'] > s['previousDayClosePrice'])
        declined = sum(1 for s in stocks if s['closePrice'] < s['previousDayClosePrice'])
        unchanged = sum(1 for s in stocks if s['closePrice'] == s['previousDayClosePrice'])
        total_turnover = sum(s.get('totalTradedValue', 0) for s in stocks)
        total_shares = sum(s.get('totalTradedQuantity', 0) for s in stocks)
        return {
            'advanced': advanced,
            'declined': declined,
            'unchanged': unchanged,
            'total_turnover': round(total_turnover, 2),
            'total_shares': total_shares,
            'last_trading_day': get_last_trading_day(),
        }
    except Exception as e:
        print(f"Error getting summary: {e}")
        return None