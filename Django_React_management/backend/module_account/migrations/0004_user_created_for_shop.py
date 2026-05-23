# Link staff accounts created via "New shop keeper" to a shop so they appear in branch permissions.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("module_shop", "0001_initial"),
        ("module_account", "0003_add_user_can_create_shop"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="created_for_shop",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="staff_invited_for_shop",
                to="module_shop.shop",
            ),
        ),
    ]
