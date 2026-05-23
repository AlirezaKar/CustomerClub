from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("module_product", "0002_align_with_management"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="second_id",
            field=models.PositiveIntegerField(),
        ),
    ]
