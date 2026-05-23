"""Helpers for resolving role-specific user profiles and branch access."""
from django.db import IntegrityError, connection, transaction
from django.db.models import QuerySet

from module_account.models import BranchManager, ShopManager, User
from module_shop.models import Branch


def get_branch_manager(user) -> BranchManager | None:
    if not user or not getattr(user, "is_authenticated", True):
        return None
    if user.role != User.Role.BRANCH_MANAGER:
        return None
    try:
        return BranchManager.objects.get(pk=user.pk)
    except BranchManager.DoesNotExist:
        return None


def ensure_branch_manager(user) -> BranchManager | None:
    """
    Return the BranchManager profile for ``user``, creating the MTI child row if missing.
    """
    bm = get_branch_manager(user)
    if bm is not None:
        return bm
    if user.role != User.Role.BRANCH_MANAGER:
        return None
    try:
        bm = BranchManager(user_ptr=user)
        bm.save()
        return BranchManager.objects.get(pk=user.pk)
    except Exception:
        return None


def get_shop_manager(user) -> ShopManager | None:
    if not user or not getattr(user, "is_authenticated", True):
        return None
    if user.role != User.Role.SHOP_MANAGER:
        return None
    try:
        return ShopManager.objects.get(pk=user.pk)
    except ShopManager.DoesNotExist:
        return None


def ensure_shop_manager(user) -> ShopManager | None:
    """
    Return the ShopManager profile for ``user``, creating the MTI child row if missing.
    """
    sm = get_shop_manager(user)
    if sm is not None:
        return sm
    if user.role != User.Role.SHOP_MANAGER:
        return None
    shop_table = ShopManager._meta.db_table
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {shop_table} (user_ptr_id) VALUES (%s)",
                [user.pk],
            )
    except IntegrityError:
        pass
    try:
        return ShopManager.objects.get(pk=user.pk)
    except ShopManager.DoesNotExist:
        return None


@transaction.atomic
def promote_to_shop_manager(user: User) -> ShopManager | None:
    """
    Convert a branch manager account into a shop manager (same User row, swap MTI child table).
    """
    if user.role == User.Role.SHOP_MANAGER:
        return ensure_shop_manager(user)
    if user.role != User.Role.BRANCH_MANAGER:
        return None

    bm = get_branch_manager(user)
    if bm:
        bm.managed_shops_all_branches.clear()
        bm.allowed_branches.clear()
        if bm.created_for_shop_id is not None:
            bm.created_for_shop_id = None
            bm.save(update_fields=["created_for_shop_id"])

    branch_table = BranchManager._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(f"DELETE FROM {branch_table} WHERE user_ptr_id = %s", [user.pk])

    User.objects.filter(pk=user.pk).update(role=User.Role.SHOP_MANAGER)
    return ensure_shop_manager(user)


def user_allowed_branches(user) -> QuerySet[Branch]:
    bm = get_branch_manager(user)
    if bm is None:
        return Branch.objects.none()
    return bm.allowed_branches


def user_managed_shops_all_branches(user):
    bm = get_branch_manager(user)
    if bm is None:
        from module_shop.models import Shop

        return Shop.objects.none()
    return bm.managed_shops_all_branches


def user_created_for_shop_id(user):
    bm = get_branch_manager(user)
    if bm is None:
        return None
    return bm.created_for_shop_id
