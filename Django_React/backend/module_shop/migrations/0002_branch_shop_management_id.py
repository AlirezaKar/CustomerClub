# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("module_shop", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="shop",
            name="management_id",
            field=models.PositiveIntegerField(blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="branch",
            name="management_id",
            field=models.PositiveIntegerField(blank=True, null=True, unique=True),
        ),
        migrations.AddIndex(
            model_name="shop",
            index=models.Index(fields=["management_id"], name="shop_management_id_idx"),
        ),
        migrations.AddIndex(
            model_name="branch",
            index=models.Index(fields=["management_id"], name="branch_management_id_idx"),
        ),
        migrations.AddIndex(
            model_name="branch",
            index=models.Index(fields=["shop", "is_active"], name="branch_shop_active_idx"),
        ),
    ]
