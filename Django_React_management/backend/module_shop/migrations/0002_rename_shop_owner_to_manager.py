from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("module_shop", "0001_initial"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="shop",
            name="shop_owner_idx",
        ),
        migrations.RenameField(
            model_name="shop",
            old_name="owner",
            new_name="manager",
        ),
        migrations.AddIndex(
            model_name="shop",
            index=models.Index(fields=["manager"], name="shop_manager_idx"),
        ),
    ]
