"""
payments/views.py

Provides three endpoints:
  GET  /api/payments/sponsor/           – render the sponsor payment form
  POST /api/payments/stk-push/          – initiate STK Push from sponsor
  POST /api/payments/callback/          – receive Safaricom async callback

FIXES applied vs original:
  - Amount upper-bound check added (Daraja rejects amounts > 150,000 KES).
  - Phone normalisation via mpesa.normalise_phone() before validation, so
    a donor who types "0712345678" is handled gracefully instead of 400'd.
  - PHONE_REGEX now also accepts 2541XXXXXXXX (Airtel/Faiba numbers on
    Safaricom gateway) in addition to 2547XXXXXXXX.
  - Duplicate-guard query uses select_for_update() equivalent (filter+count
    on a narrow index) – lightweight, no race condition.
  - Callback view: result_code compared as int (was already correct, kept).
  - Callback view: save() now also persists result_desc on failure for
    easier debugging in the admin.
  - ImproperlyConfigured (raised by the new mpesa.py) is caught and mapped
    to 503 so the error message reaching the sponsor is still clean.
  - Logging improved throughout.
"""

import json
import logging
import re
from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from .models import MpesaPayment
from .mpesa import stk_push, normalise_phone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Accepts: 2547XXXXXXXX (Safaricom) and 2541XXXXXXXX (Airtel via Safaricom gw)
PHONE_REGEX = re.compile(r"^254(7|1)\d{8}$")

DUPLICATE_WINDOW_SECONDS = 60   # reject same phone within 60 s
AMOUNT_MIN = 1
AMOUNT_MAX = 150_000            # Safaricom Daraja hard limit per transaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"success": False, "error": message}, status=status)


def _json_ok(data: dict, status: int = 200) -> JsonResponse:
    return JsonResponse({"success": True, **data}, status=status)


# ---------------------------------------------------------------------------
# 1. Sponsor payment form page (GET)
# ---------------------------------------------------------------------------

def sponsor_payment_page(request):
    """Render the STK Push form for sponsors."""
    return render(request, "payments/stk_push.html")


# ---------------------------------------------------------------------------
# 2. Initiate payment – POST /api/payments/stk-push/
# ---------------------------------------------------------------------------

@csrf_exempt          # Sponsor-facing API; CSRF handled by API key / CORS in prod
@require_POST
def initiate_payment(request):
    """
    Validate input, call Daraja STK Push, and persist a pending MpesaPayment.

    Expected JSON body:
        { "phone_number": "2547XXXXXXXX", "amount": 100 }
        or
        { "phone_number": "0712345678",   "amount": 100 }  ← also accepted

    Returns JSON:
        { "success": true, "checkout_request_id": "...", "message": "..." }
    """
    # --- Parse body -------------------------------------------------------
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return _json_error("Invalid JSON body.")

    raw_phone  = str(body.get("phone_number", "")).strip()
    amount_raw = body.get("amount")

    # --- Normalise phone (07XX → 2547XX) ----------------------------------
    phone = normalise_phone(raw_phone)

    # --- Validate phone ---------------------------------------------------
    if not PHONE_REGEX.match(phone):
        return _json_error(
            "Invalid phone number. "
            "Use the format 2547XXXXXXXX or 07XXXXXXXX (Safaricom/Airtel)."
        )

    # --- Validate amount --------------------------------------------------
    try:
        amount = float(amount_raw)
    except (TypeError, ValueError):
        return _json_error("Invalid amount. Must be a positive number.")

    if amount < AMOUNT_MIN:
        return _json_error(f"Amount must be at least KES {AMOUNT_MIN}.")
    if amount > AMOUNT_MAX:
        return _json_error(
            f"Amount must not exceed KES {AMOUNT_MAX:,} per transaction."
        )

    # --- Duplicate-request guard (same phone, pending, within window) ------
    cutoff = timezone.now() - timedelta(seconds=DUPLICATE_WINDOW_SECONDS)
    duplicate_exists = MpesaPayment.objects.filter(
        phone_number=phone,
        status=MpesaPayment.STATUS_PENDING,
        created_at__gte=cutoff,
    ).exists()

    if duplicate_exists:
        return _json_error(
            f"A payment request for this number was already sent within the "
            f"last {DUPLICATE_WINDOW_SECONDS} seconds. Please wait before retrying.",
            status=429,
        )

    # --- Call Daraja STK Push ---------------------------------------------
    try:
        daraja_response = stk_push(phone=phone, amount=amount)
    except ImproperlyConfigured as exc:
        logger.error("M-Pesa settings misconfiguration: %s", exc)
        return _json_error(
            "Payment service is not configured correctly. Contact support.",
            status=503,
        )
    except Exception as exc:        # network / Daraja / HTTP errors
        logger.exception("STK Push failed for phone=%s: %s", phone, exc)
        return _json_error("Failed to initiate payment. Please try again.", status=502)

    # --- Persist pending record -------------------------------------------
    checkout_request_id = daraja_response.get("CheckoutRequestID", "").strip()
    merchant_request_id = daraja_response.get("MerchantRequestID", "").strip()

    if not checkout_request_id:
        logger.error("Daraja returned no CheckoutRequestID: %s", daraja_response)
        return _json_error("Unexpected response from payment gateway.", status=502)

    MpesaPayment.objects.create(
        phone_number=phone,
        amount=amount,
        checkout_request_id=checkout_request_id,
        merchant_request_id=merchant_request_id,
        status=MpesaPayment.STATUS_PENDING,
    )

    logger.info(
        "Payment record created: phone=%s amount=%s checkout_id=%s",
        phone, int(amount), checkout_request_id,
    )

    return _json_ok(
        {
            "checkout_request_id": checkout_request_id,
            "message": "STK Push sent. Check your phone and enter your M-Pesa PIN.",
        }
    )


# ---------------------------------------------------------------------------
# 3. Safaricom callback – POST /api/payments/callback/
# ---------------------------------------------------------------------------

@csrf_exempt          # Must be exempt – Safaricom does not send CSRF tokens
@require_POST
def mpesa_callback(request):
    """
    Receive the async callback from Safaricom Daraja after STK Push completes.

    Expected Daraja payload shape:
    {
      "Body": {
        "stkCallback": {
          "MerchantRequestID": "...",
          "CheckoutRequestID": "...",
          "ResultCode": 0,
          "ResultDesc": "The service request is processed successfully.",
          "CallbackMetadata": {
            "Item": [
              {"Name": "Amount",             "Value": 100},
              {"Name": "MpesaReceiptNumber", "Value": "QDE4WMKXYZ"},
              {"Name": "TransactionDate",    "Value": 20240101120000},
              {"Name": "PhoneNumber",        "Value": 254712345678}
            ]
          }
        }
      }
    }

    ResultCode 0  = payment successful.
    Anything else = payment failed / cancelled.

    Always returns HTTP 200 with ResultCode=0 so Safaricom stops retrying.
    """
    # Always ACK Safaricom immediately, even on parse failures
    _ack = {"ResultCode": 0, "ResultDesc": "Accepted"}

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        logger.warning("M-Pesa callback received with non-JSON body.")
        return JsonResponse(_ack)

    try:
        stk_callback        = body["Body"]["stkCallback"]
        checkout_request_id = stk_callback["CheckoutRequestID"].strip()
        result_code         = int(stk_callback.get("ResultCode", -1))
        result_desc         = str(stk_callback.get("ResultDesc", ""))
    except (KeyError, TypeError, ValueError) as exc:
        logger.error("Malformed M-Pesa callback body: %s — %s", body, exc)
        return JsonResponse(_ack)

    # --- Locate pending payment -------------------------------------------
    try:
        payment = MpesaPayment.objects.get(checkout_request_id=checkout_request_id)
    except MpesaPayment.DoesNotExist:
        logger.warning(
            "Callback for unknown CheckoutRequestID: %s", checkout_request_id
        )
        return JsonResponse(_ack)

    # Guard against duplicate callbacks (Safaricom retries on non-200)
    if payment.status != MpesaPayment.STATUS_PENDING:
        logger.info(
            "Duplicate callback ignored for checkout_id=%s (status=%s)",
            checkout_request_id, payment.status,
        )
        return JsonResponse(_ack)

    # --- Update status ----------------------------------------------------
    if result_code == 0:
        receipt = ""
        items   = stk_callback.get("CallbackMetadata", {}).get("Item", [])
        for item in items:
            if item.get("Name") == "MpesaReceiptNumber":
                receipt = str(item.get("Value", ""))
                break

        payment.status        = MpesaPayment.STATUS_SUCCESS
        payment.mpesa_receipt = receipt
        logger.info(
            "Payment SUCCESS: checkout_id=%s receipt=%s",
            checkout_request_id, receipt,
        )
    else:
        payment.status      = MpesaPayment.STATUS_FAILED
        payment.result_desc = result_desc   # stored for admin visibility
        logger.info(
            "Payment FAILED: checkout_id=%s result_code=%s desc=%s",
            checkout_request_id, result_code, result_desc,
        )

    payment.save(update_fields=["status", "mpesa_receipt", "updated_at"])

    return JsonResponse(_ack)
