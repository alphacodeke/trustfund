from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="MpesaPayment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("phone_number", models.CharField(db_index=True, max_length=15)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("checkout_request_id", models.CharField(max_length=100, unique=True)),
                ("merchant_request_id", models.CharField(max_length=100)),
                ("mpesa_receipt", models.CharField(blank=True, max_length=50, null=True)),
                ("result_desc", models.TextField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("success", "Success"),
                            ("failed",  "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name":        "M-Pesa Payment",
                "verbose_name_plural": "M-Pesa Payments",
                "ordering":            ["-created_at"],
            },
        ),
    ]
