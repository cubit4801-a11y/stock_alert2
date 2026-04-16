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
        label='Target Price'
    )
    price_low = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label='Low Price'
    )
    price_high = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label='High Price'
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