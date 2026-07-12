"""Payment URL configuration."""

from django.urls import path

from payments import views

app_name = "payments"

urlpatterns = [
    path("history/", views.transaction_history, name="history"),
    path("webhook/stripe/", views.stripe_webhook, name="stripe_webhook"),
]
