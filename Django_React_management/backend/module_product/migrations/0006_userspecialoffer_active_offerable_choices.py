from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("module_product", "0005_specialoffertransaction_score_ledger"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userspecialoffer",
            name="product",
            field=models.ForeignKey(
                limit_choices_to={"is_offerable": True, "is_active": True},
                on_delete=django.db.models.deletion.CASCADE,
                to="module_product.product",
            ),
        ),
    ]
