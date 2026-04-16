import warnings
warnings.filterwarnings('ignore')
import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils import timezone
from .forms import RegisterForm, StockAlertForm
from .models import StockAlert
from .nepse_utils import get_all_stocks, get_market_status, get_nepse_summary


# ---- REGISTER VIEW ----
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to NEPSE Stock Alert, {user.first_name}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


# ---- LOGIN VIEW ----
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    try:
        stocks = get_all_stocks()
    except Exception:
        stocks = []
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name}!")
                return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


# ---- LOGOUT VIEW ----
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')


# ---- DASHBOARD VIEW ----
@login_required
def dashboard_view(request):
    alerts = StockAlert.objects.filter(user=request.user)
    try:
        is_open = get_market_status()
        summary = get_nepse_summary()
        stocks = get_all_stocks()
    except Exception:
        is_open = False
        summary = {}
        stocks = []
    now = timezone.now()

    for stock in stocks:
        ltp = stock.get('ltp', 0)
        prev = stock.get('previousDayClosePrice', 0)
        if prev and prev != 0:
            change = ltp - prev
            change_pct = (change / prev) * 100
            stock['change'] = round(change, 2)
            stock['change_pct'] = round(change_pct, 2)
        else:
            stock['change'] = 0
            stock['change_pct'] = 0

    top_stocks = stocks[:20]

    return render(request, 'accounts/dashboard.html', {
        'user': request.user,
        'alerts': alerts,
        'is_open': is_open,
        'summary': summary,
        'top_stocks': top_stocks,
        'now': now,
    })


# ---- ADD ALERT VIEW ----
@login_required
def add_alert_view(request):
    try:
        stocks = get_all_stocks()
    except Exception:
        stocks = []

    stock_choices = [('', '--- Select a Stock ---')]
    stock_data = {}
    for stock in stocks:
        symbol = stock['symbol']
        name = stock['securityName']
        ltp = stock.get('ltp', 0)
        stock_choices.append((symbol, symbol))
        stock_data[symbol] = {
            'name': name,
            'ltp': ltp
        }

    if request.method == 'POST':
        form = StockAlertForm(request.POST, stock_choices=stock_choices)
        if form.is_valid():
            alert_type = form.cleaned_data['alert_type']
            target_price = form.cleaned_data.get('target_price')
            price_high = form.cleaned_data.get('price_high')
            price_low = form.cleaned_data.get('price_low')
            notes = form.cleaned_data.get('notes')

            if alert_type in ['above', 'below'] and not target_price:
                messages.error(request, "Please enter a target price.")
            elif alert_type == 'between' and (not price_high or not price_low):
                messages.error(request, "Please enter both Low and High prices.")
            else:
                StockAlert.objects.create(
                    user=request.user,
                    stock_symbol=form.cleaned_data['stock_symbol'].upper(),
                    stock_name=form.cleaned_data['stock_name'],
                    target_price=target_price,
                    price_high=price_high,
                    price_low=price_low,
                    alert_type=alert_type,
                    notes=notes,
                )
                messages.success(request, "Stock alert created successfully!")
                return redirect('dashboard')
        else:
            messages.error(request, "Please fix the errors below.")

    else:
        initial_symbol = request.GET.get('symbol', '')
        initial_name = request.GET.get('name', '')
        initial_price = request.GET.get('price', '')
        form = StockAlertForm(
            initial={
                'stock_symbol': initial_symbol,
                'stock_name': initial_name,
                'target_price': initial_price,
            },
            stock_choices=stock_choices
        )

    stock_data_json = '<script id="stock-data-json" type="application/json">' + json.dumps(stock_data) + '</script>'

    return render(request, 'accounts/add_alert.html', {
        'form': form,
        'stock_data': stock_data,
        'stock_data_json': stock_data_json,
    })
# ---- NEPSE STOCKS VIEW ----
@login_required
def nepse_stocks_view(request):
    try:
        stocks = get_all_stocks()
        is_open = get_market_status()
    except Exception:
        stocks = []
        is_open = False
    search = request.GET.get('search', '')
    if search:
        stocks = [s for s in stocks if
                  search.upper() in s['symbol'] or
                  search.upper() in s['securityName'].upper()]
    return render(request, 'accounts/nepse_stocks.html', {
        'stocks': stocks,
        'is_open': is_open,
        'search': search,
        'total': len(stocks)
    })
# ---- DELETE ALERT VIEW ----
@login_required
def delete_alert_view(request, alert_id):
    alert = StockAlert.objects.get(id=alert_id, user=request.user)
    alert.delete()
    messages.success(request, "Alert deleted successfully!")
    return redirect('dashboard')


# ---- NEPSE STOCKS VIEW ----
@login_required
def nepse_stocks_view(request):
    try:
        stocks = get_all_stocks()
        is_open = get_market_status()
    except Exception:
        stocks = []
        is_open = False
    search = request.GET.get('search', '')
    if search:
        stocks = [s for s in stocks if
                  search.upper() in s['symbol'] or
                  search.upper() in s['securityName'].upper()]
    return render(request, 'accounts/nepse_stocks.html', {
        'stocks': stocks,
        'is_open': is_open,
        'search': search,
        'total': len(stocks)
    })