from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("module_product", "0004_alter_product_image"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="category",
            name="category_management_id_idx",
        ),
        migrations.RemoveIndex(
            model_name="product",
            name="product_management_id_idx",
        ),
        migrations.RemoveField(
            model_name="category",
            name="management_id",
        ),
        migrations.RemoveField(
            model_name="product",
            name="management_id",
        ),
        migrations.RemoveField(
            model_name="product",
            name="management_image_url",
        ),
        migrations.RemoveField(
            model_name="userspecialoffer",
            name="management_offer_id",
        ),
    ]
