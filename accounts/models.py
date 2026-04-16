from django.db import models
from django.contrib.auth.models import User

class StockAlert(models.Model):

    ALERT_TYPE_CHOICES = [
        ('above', 'Price Rises Above'),
        ('below', 'Price Falls Below'),
        ('between', 'Price In Between Range'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('triggered', 'Triggered'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stock_symbol = models.CharField(max_length=20)
    stock_name = models.CharField(max_length=100)
    target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_high = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    alert_type = models.CharField(max_length=10, choices=ALERT_TYPE_CHOICES, default='above')
    notes = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    triggered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.stock_symbol} - {self.alert_type}"

    class Meta:
        ordering = ['-created_at']