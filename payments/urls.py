from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("stk-push/",  views.initiate_payment,    name="stk-push"),
    path("callback/",  views.mpesa_callback,       name="callback"),
    path("sponsor/",   views.sponsor_payment_page, name="sponsor-page"),
]
