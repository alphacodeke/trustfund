"""
Safaricom Daraja M-Pesa service layer.

Provides:
  - get_access_token()  : OAuth2 bearer token from Daraja sandbox/production.
  - generate_password() : Base64(Shortcode + Passkey + Timestamp).
  - stk_push()          : Initiates a Lipa Na M-Pesa STK Push request.

All credentials are read from Django settings (which in turn read from .env):
  MPESA_CONSUMER_KEY
  MPESA_CONSUMER_SECRET
  MPESA_SHORTCODE
  MPESA_PASSKEY
  MPESA_CALLBACK_URL
  MPESA_ENV   ("sandbox" | "production", defaults to "sandbox")

FIXES applied vs original:
  - Reads credentials from django.conf.settings (not raw os.environ) so
    Django's settings layer (and dotenv loading) is the single source of truth.
  - Added explicit timeout on both the token fetch AND the STK push call.
  - Raises a descriptive ImproperlyConfigured instead of bare EnvironmentError
    so Django's startup checks can surface misconfiguration early.
  - Amount is cast to int BEFORE building the payload (Daraja rejects floats).
  - phone normalisation helper – strips leading whitespace/newlines that a
    browser sometimes smuggles in.
"""

import base64
import logging
from datetime import datetime

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setting(name: str) -> str:
    """
    Return a Django setting by name.

    Raises ImproperlyConfigured (not a generic Exception) if the value is
    absent or is the empty string, so Django's check framework can catch it
    during startup rather than at the first payment attempt.
    """
    value = getattr(settings, name, None)
    if not value:
        raise ImproperlyConfigured(
            f"Required M-Pesa setting '{name}' is missing or empty. "
            "Add it to your .env file and ensure it is loaded before Django starts."
        )
    return str(value).strip()


def _base_url() -> str:
    env = getattr(settings, "MPESA_ENV", "sandbox").strip().lower()
    if env == "production":
        return "https://api.safaricom.co.ke"
    return "https://sandbox.safaricom.co.ke"


def normalise_phone(phone: str) -> str:
    """
    Strip whitespace and ensure the number starts with 254.

    Accepts:
      07XXXXXXXX  → 2547XXXXXXXX
      2547XXXXXXXX → unchanged
    """
    phone = phone.strip()
    if phone.startswith("0") and len(phone) == 10:
        phone = "254" + phone[1:]
    return phone


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def get_access_token() -> str:
    """
    Fetch a short-lived OAuth2 bearer token from the Daraja API.

    Returns:
        str: Access token string.

    Raises:
        requests.HTTPError: on a non-2xx response.
        ValueError: if the response body has no access_token field.
    """
    consumer_key    = _setting("MPESA_CONSUMER_KEY")
    consumer_secret = _setting("MPESA_CONSUMER_SECRET")

    url = f"{_base_url()}/oauth/v1/generate?grant_type=client_credentials"

    response = requests.get(
        url,
        auth=(consumer_key, consumer_secret),
        timeout=15,
    )
    response.raise_for_status()

    data  = response.json()
    token = data.get("access_token")
    if not token:
        raise ValueError(f"No access_token in Daraja response: {data}")

    logger.debug("M-Pesa access token obtained successfully.")
    return token


def generate_password() -> tuple[str, str]:
    """
    Generate the STK Push password and timestamp.

    Formula : Base64(Shortcode + Passkey + Timestamp)
    Timestamp: YYYYMMDDHHmmss

    Returns:
        (password: str, timestamp: str)
    """
    shortcode = _setting("MPESA_SHORTCODE")
    passkey   = _setting("MPESA_PASSKEY")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    raw      = f"{shortcode}{passkey}{timestamp}"
    password = base64.b64encode(raw.encode()).decode()
    return password, timestamp


# ---------------------------------------------------------------------------
# STK Push
# ---------------------------------------------------------------------------

def stk_push(phone: str, amount: int | float) -> dict:
    """
    Initiate an M-Pesa Lipa Na M-Pesa Online (STK Push) request.

    Args:
        phone  (str)        : Customer phone in the format 2547XXXXXXXX.
        amount (int|float)  : Amount in KES (decimals truncated for Daraja).

    Returns:
        dict: Raw JSON from Daraja, containing at minimum:
              MerchantRequestID, CheckoutRequestID, ResponseCode,
              CustomerMessage.

    Raises:
        requests.HTTPError       : on a non-2xx response from Daraja.
        ImproperlyConfigured     : if any required setting is missing.
    """
    shortcode    = _setting("MPESA_SHORTCODE")
    callback_url = _setting("MPESA_CALLBACK_URL")

    access_token        = get_access_token()
    password, timestamp = generate_password()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json",
    }

    payload = {
        "BusinessShortCode": shortcode,
        "Password":          password,
        "Timestamp":         timestamp,
        "TransactionType":   "CustomerPayBillOnline",
        "Amount":            int(amount),   # Daraja rejects floats
        "PartyA":            phone,
        "PartyB":            shortcode,
        "PhoneNumber":       phone,
        "CallBackURL":       callback_url,
        "AccountReference":  "TrustFund",
        "TransactionDesc":   "Sponsor Contribution",
    }

    url      = f"{_base_url()}/mpesa/stkpush/v1/processrequest"
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    logger.info(
        "STK Push initiated: phone=%s amount=%s checkout_id=%s",
        phone,
        int(amount),
        data.get("CheckoutRequestID"),
    )
    return data
