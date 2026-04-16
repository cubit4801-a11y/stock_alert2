from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
]
from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('add-alert/', views.add_alert_view, name='add_alert'),
    path('delete-alert/<int:alert_id>/', views.delete_alert_view, name='delete_alert'),
    path('stocks/', views.nepse_stocks_view, name='nepse_stocks'),  # ← ADD THIS
]