from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm



class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Required. Enter a valid email.")
    full_name = forms.CharField(max_length=100, required=True)

    class Meta:
        model = User
        fields = ['username', 'full_name', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['full_name']
        if commit:
            user.save()
        return user


class StockAlertForm(forms.Form):
    stock_symbol = forms.ChoiceField(
        choices=[],
        label='Symbol',
    )
    stock_name = forms.CharField(
        max_length=100,
        widget=forms.HiddenInput()
    )
    alert_type = forms.ChoiceField(
        choices=[
            ('above', 'Price Rises Above'),
            ('below', 'Price Falls Below'),
            ('between', 'Price In Between'),
        ],
        label='Alert Condition'
    )
    target_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label='Target Price',
        min_value=0.01          # ✅ Added
    )
    price_low = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label='Low Price',
        min_value=0.01          # ✅ Added
    )
    price_high = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label='High Price',
        min_value=0.01          # ✅ Added
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Add a short note for yourself'
        }),
        label='Notes'
    )

    def __init__(self, *args, stock_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if stock_choices:
            self.fields['stock_symbol'].choices = stock_choices

    def clean_target_price(self):
        price = self.cleaned_data.get('target_price')
        if price is not None and price <= 0:
            raise forms.ValidationError("❌ Target price must be greater than 0")
        return price

    def clean_price_low(self):
        price = self.cleaned_data.get('price_low')
        if price is not None and price <= 0:
            raise forms.ValidationError("❌ Low price must be greater than 0")
        return price

    def clean_price_high(self):
        price = self.cleaned_data.get('price_high')
        if price is not None and price <= 0:
            raise forms.ValidationError("❌ High price must be greater than 0")
        return price

    def clean(self):
        cleaned_data = super().clean()
        alert_type = cleaned_data.get('alert_type')
        target_price = cleaned_data.get('target_price')
        price_low = cleaned_data.get('price_low')
        price_high = cleaned_data.get('price_high')

        if alert_type in ['above', 'below']:
            if not target_price:
                raise forms.ValidationError("❌ Target price is required for this alert type")

        if alert_type == 'between':
            if not price_low or not price_high:
                raise forms.ValidationError("❌ Both Low and High prices required for Between alert")
            if price_low >= price_high:
                raise forms.ValidationError("❌ Low price must be less than High price")

        return cleaned_data