from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("module_shop", "0002_branch_shop_management_id"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="shop",
            name="shop_management_id_idx",
        ),
        migrations.RemoveIndex(
            model_name="branch",
            name="branch_management_id_idx",
        ),
        migrations.RemoveField(
            model_name="shop",
            name="management_id",
        ),
        migrations.RemoveField(
            model_name="branch",
            name="management_id",
        ),
    ]
