"""Payment URL configuration."""

from django.urls import path

from payments import billing_views, views

app_name = "payments"

urlpatterns = [
    path("billing/", billing_views.billing_overview, name="billing"),
    path("billing/portal/", billing_views.billing_portal, name="billing_portal"),
    path("history/", billing_views.transaction_history, name="history"),
    path("connect/", views.connect_dashboard, name="connect_dashboard"),
    path("connect/onboard/", views.connect_onboard, name="connect_onboard"),
    path("connect/return/", views.connect_return, name="connect_return"),
    path("connect/refresh/", views.connect_refresh, name="connect_refresh"),
    path("webhook/stripe/", views.stripe_webhook, name="stripe_webhook"),
]
