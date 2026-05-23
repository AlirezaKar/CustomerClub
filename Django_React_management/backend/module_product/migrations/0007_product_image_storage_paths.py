from django.db import migrations, models

import module_product.image_storage


def relocate_legacy_product_images(apps, schema_editor):
    Product = apps.get_model("module_product", "Product")
    from module_product.image_storage import finalize_product_image, product_image_needs_finalize

    for product in Product.objects.exclude(image="").exclude(image=None).iterator():
        if not product_image_needs_finalize(product.image.name, product.pk):
            continue
        try:
            if not product.image.storage.exists(product.image.name):
                product.image = None
                product.save(update_fields=["image"])
                continue
            if finalize_product_image(product):
                product.save(update_fields=["image"])
        except OSError:
            product.image = None
            product.save(update_fields=["image"])


class Migration(migrations.Migration):

    dependencies = [
        ("module_product", "0006_userspecialoffer_active_offerable_choices"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="image",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=module_product.image_storage.product_image_upload_to,
            ),
        ),
        migrations.RunPython(relocate_legacy_product_images, migrations.RunPython.noop),
    ]
