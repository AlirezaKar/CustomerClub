from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("module_account", "0007_alter_branchmanager_managers_alter_enduser_managers_and_more"),
        ("module_product", "0005_specialoffertransaction_score_ledger"),
    ]

    operations = [
        migrations.DeleteModel(
            name="UserScoreLog",
        ),
    ]
