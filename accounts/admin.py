from django.contrib import admin
from accounts.models import StockAlert

@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ['user', 'stock_symbol', 'alert_type', 'target_price', 'status']
    list_filter = ['status', 'alert_type']
    search_fields = ['stock_symbol']
    list_editable = ['status']  # ← lets you change status directly from the list!