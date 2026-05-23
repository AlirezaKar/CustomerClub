from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("module_account", "0008_remove_userscorelog"),
        ("module_product", "0008_alter_specialoffertransaction_delta_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userspecialoffer",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="useroffer_set",
                to="module_account.enduser",
            ),
        ),
    ]
