# Generated manually for score-ledger consolidation

import django.db.models.deletion
from django.db import migrations, models


def migrate_score_logs_to_transactions(apps, schema_editor):
    UserScoreLog = apps.get_model("module_account", "UserScoreLog")
    SpecialOfferTransaction = apps.get_model("module_product", "SpecialOfferTransaction")
    Product = apps.get_model("module_product", "Product")

    matched_log_ids = set()
    for tx in SpecialOfferTransaction.objects.all().iterator():
        logs = list(
            UserScoreLog.objects.filter(
                user_id=tx.user_id,
                product_id=tx.product_id,
            ).order_by("created_at", "id")
        )
        if logs:
            first_log = logs[0]
            tx.delta = first_log.delta
            tx.reason = first_log.reason
            tx.save(update_fields=["delta", "reason"])
            matched_log_ids.add(first_log.pk)
            for extra_log in logs[1:]:
                SpecialOfferTransaction.objects.create(
                    user_id=extra_log.user_id,
                    delta=extra_log.delta,
                    reason=extra_log.reason,
                    product_id=extra_log.product_id,
                    created_at=extra_log.created_at,
                )
                matched_log_ids.add(extra_log.pk)
            continue

        if tx.product_id:
            product = Product.objects.filter(pk=tx.product_id).first()
            tx.delta = -int(product.score) if product else 0
            tx.reason = "special_offer"
            tx.save(update_fields=["delta", "reason"])

    for log in UserScoreLog.objects.exclude(pk__in=matched_log_ids).iterator():
        SpecialOfferTransaction.objects.create(
            user_id=log.user_id,
            delta=log.delta,
            reason=log.reason,
            product_id=log.product_id,
            created_at=log.created_at,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("module_account", "0007_alter_branchmanager_managers_alter_enduser_managers_and_more"),
        ("module_product", "0004_remove_customer_product_offer"),
    ]

    operations = [
        migrations.AddField(
            model_name="specialoffertransaction",
            name="delta",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="specialoffertransaction",
            name="reason",
            field=models.CharField(
                choices=[
                    ("special_offer", "Special offer"),
                    ("purchase", "Purchase"),
                    ("admin_adjust", "Admin adjust"),
                ],
                default="special_offer",
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="specialoffertransaction",
            name="product",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="special_offer_transactions",
                to="module_product.product",
            ),
        ),
        migrations.RunPython(
            migrate_score_logs_to_transactions,
            migrations.RunPython.noop,
        ),
        migrations.AlterModelOptions(
            name="specialoffertransaction",
            options={"ordering": ("-created_at", "-id")},
        ),
    ]
