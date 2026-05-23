"""
Shop, Branch, and Score models compatible with main CustomerClub project.
"""
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

User = get_user_model()


class Shop(models.Model):
    name = models.CharField(max_length=255)
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_shops_as_manager",
    )
    # Users who can manage this shop in addition to the shop manager (permission-gated)
    managed_by = models.ManyToManyField(
        User, related_name="managed_shops", blank=True
    )

    class Meta:
        db_table = "module_shop_shop"
        permissions = [
            ("can_manage_assigned_shops", "Can manage shops assigned to user (multi-shop access)"),
        ]
        indexes = [
            models.Index(fields=["manager"], name="shop_manager_idx"),
        ]

    def __str__(self):
        return self.name


class Branch(models.Model):
    """A branch/location of a shop. Users can be restricted to one or multiple branches."""
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "module_shop_branch"
        ordering = ("name",)
        permissions = [
            ("manage_all_branches", "Can manage all branches of accessible shops"),
        ]
        indexes = [
            models.Index(fields=["shop", "is_active"], name="branch_shop_active_idx"),
        ]

    def __str__(self):
        return f"{self.shop.name} — {self.name}"


class Score(models.Model):
    price_for_score = models.PositiveIntegerField(default=1000000)
    score_for_purchase = models.PositiveBigIntegerField(default=1)
    shop = models.OneToOneField(Shop, on_delete=models.CASCADE, related_name="score")

    class Meta:
        db_table = "module_shop_score"


@receiver(post_save, sender=Shop)
def create_shop_score(sender, instance, created, **kwargs):
    if created and not hasattr(instance, "score"):
        Score.objects.create(shop=instance)

@receiver(m2m_changed, sender=Shop.managed_by.through)
def add_shop_management_permission(sender, instance, action, pk_set, **kwargs):
    """
    When a user is added to Shop.managed_by, grant ``module_shop.can_manage_assigned_shops``
    so they can access assigned shops through the normal permission checks.
    """
    if action != "post_add" or not pk_set:
        return
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType

    permission, _ = Permission.objects.get_or_create(
        codename="can_manage_assigned_shops",
        content_type=ContentType.objects.get_for_model(Shop),
        defaults={
            "name": "Can manage shops assigned to user (multi-shop access)",
        },
    )
    for user_id in pk_set:
        user = User.objects.get(pk=user_id)
        user.user_permissions.add(permission)