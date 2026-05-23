from django.db import migrations, models

import module_account.profile_storage


def relocate_legacy_profile_pictures(apps, schema_editor):
    User = apps.get_model("module_account", "User")
    from module_account.profile_storage import finalize_profile_picture, profile_picture_needs_finalize

    for user in User.objects.exclude(profile_picture="").exclude(profile_picture=None).iterator():
        if not profile_picture_needs_finalize(user.profile_picture.name, user.pk):
            continue
        try:
            if not user.profile_picture.storage.exists(user.profile_picture.name):
                user.profile_picture = None
                user.save(update_fields=["profile_picture"])
                continue
            if finalize_profile_picture(user):
                user.save(update_fields=["profile_picture"])
        except OSError:
            user.profile_picture = None
            user.save(update_fields=["profile_picture"])


class Migration(migrations.Migration):

    dependencies = [
        ("module_account", "0008_remove_userscorelog"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="profile_picture",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=module_account.profile_storage.profile_picture_upload_to,
                verbose_name="profile picture",
            ),
        ),
        migrations.RunPython(relocate_legacy_profile_pictures, migrations.RunPython.noop),
    ]
