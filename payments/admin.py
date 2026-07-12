from django.contrib import admin

from payments.models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "transaction_type",
        "amount_cents",
        "platform_fee_cents",
        "status",
        "created_at",
    ]
    list_filter = ["transaction_type", "status"]
    readonly_fields = ["created_at"]
