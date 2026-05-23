from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("module_account", "0002_initial"),
        ("module_product", "0007_specialoffertransaction_score_ledger"),
    ]

    operations = [
        migrations.DeleteModel(
            name="UserScoreLog",
        ),
    ]
