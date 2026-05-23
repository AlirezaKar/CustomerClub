# Generated manually for management server alignment

import django.db.models.deletion
import module_product.models
from django.db import migrations, models


def fill_null_second_ids(apps, schema_editor):
    Product = apps.get_model("module_product", "Product")
    Product.objects.filter(second_id__isnull=True).update(second_id=0)


class Migration(migrations.Migration):

    dependencies = [
        ("module_shop", "0002_branch_shop_management_id"),
        ("module_product", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="management_id",
            field=models.PositiveIntegerField(blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="category",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="categories",
                to="module_shop.branch",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="products",
                to="module_shop.branch",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="management_id",
            field=models.PositiveIntegerField(blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="product",
            name="management_image_url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="userspecialoffer",
            name="management_offer_id",
            field=models.PositiveIntegerField(blank=True, null=True, unique=True),
        ),
        migrations.RunPython(fill_null_second_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="product",
            name="second_id",
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterUniqueTogether(
            name="product",
            unique_together={("branch", "second_id")},
        ),
        migrations.AddIndex(
            model_name="category",
            index=models.Index(fields=["management_id"], name="category_management_id_idx"),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["management_id"], name="product_management_id_idx"),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["shop", "is_active"], name="product_shop_active_idx"),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["branch"], name="product_branch_idx"),
        ),
        migrations.AddIndex(
            model_name="userspecialoffer",
            index=models.Index(fields=["user", "product"], name="user_offer_user_product_idx"),
        ),
    ]
