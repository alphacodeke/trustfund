from django.contrib import admin

from .models import MpesaPayment


@admin.register(MpesaPayment)
class MpesaPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "phone_number",
        "amount",
        "status",
        "mpesa_receipt",
        "checkout_request_id",
        "created_at",
    )
    list_filter      = ("status",)
    date_hierarchy   = "created_at"
    search_fields    = ("phone_number", "checkout_request_id", "mpesa_receipt")
    readonly_fields  = (
        "phone_number",
        "amount",
        "checkout_request_id",
        "merchant_request_id",
        "mpesa_receipt",
        "result_desc",
        "status",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        # Payments are created programmatically, never via admin
        return False

    def has_delete_permission(self, request, obj=None):
        # Prevent accidental deletion of payment records
        return False
