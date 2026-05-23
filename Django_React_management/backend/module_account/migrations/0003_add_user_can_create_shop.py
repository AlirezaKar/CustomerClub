# Shop owner vs branch-staff: users created via "New shop keeper" cannot register a new shop in the app.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("module_account", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="can_create_shop",
            field=models.BooleanField(default=True),
        ),
    ]
