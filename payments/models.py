from django.db import models


class MpesaPayment(models.Model):
    """
    Tracks M-Pesa STK Push transactions initiated by sponsors.

    Named MpesaPayment to avoid collision with core.Payment
    (the fund-allocation model used internally).

    CHANGES vs original:
    - Added result_desc field to persist Daraja's failure reason, making
      failed transactions debuggable directly from the admin without log
      diving.
    """

    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED  = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED,  "Failed"),
    ]

    # Payer details
    phone_number = models.CharField(max_length=15, db_index=True)
    amount       = models.DecimalField(max_digits=10, decimal_places=2)

    # Daraja response identifiers (set on creation)
    checkout_request_id = models.CharField(max_length=100, unique=True)
    merchant_request_id = models.CharField(max_length=100)

    # Populated on successful callback
    mpesa_receipt = models.CharField(max_length=50, null=True, blank=True)

    # Populated on failed callback (Daraja's human-readable reason)
    result_desc = models.TextField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = "M-Pesa Payment"
        verbose_name_plural = "M-Pesa Payments"

    def __str__(self) -> str:
        return (
            f"MpesaPayment [{self.status.upper()}] "
            f"phone={self.phone_number} "
            f"amount={self.amount} "
            f"checkout_id={self.checkout_request_id}"
        )
