from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from module_shop.models import Shop

User = get_user_model()

class Command(BaseCommand):
    help = "Fix permissions for existing shop managers and assigned managers"

    def handle(self, *args, **options):
        content_type = ContentType.objects.get_for_model(Shop)
        
        # Ensure the permission exists
        permission, created = Permission.objects.get_or_create(
            codename='can_manage_assigned_shops',
            name='Can manage shops assigned to user (multi-shop access)',
            content_type=content_type,
        )
        
        for shop in Shop.objects.all():
            if shop.manager_id:
                shop.manager.user_permissions.add(permission)

            for manager in shop.managed_by.all():
                manager.user_permissions.add(permission)
        
        self.stdout.write(self.style.SUCCESS('Successfully fixed permissions'))