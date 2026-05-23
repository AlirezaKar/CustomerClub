"""
Helpers for shop and branch access.

- Shops a user can open in the app = managed + assigned (if permitted) + branch-linked shops.
- Branches manageable for a shop = all branches if shop manager or head branch manager; else allowed branches only.
"""
from django.db.models import Q

from module_account.role_helpers import (
    get_branch_manager,
    user_allowed_branches,
    user_managed_shops_all_branches,
)
from module_account.models import BranchManager, User
from module_shop.models import Shop, Branch


def get_accessible_shop_ids(user):
    shop_ids = set(Shop.objects.filter(manager=user).values_list("id", flat=True))

    if user.has_perm("module_shop.can_manage_assigned_shops"):
        shop_ids |= set(Shop.objects.filter(managed_by=user).values_list("id", flat=True))

    shop_ids |= set(
        user_allowed_branches(user).filter(is_active=True).values_list("shop_id", flat=True)
    )
    shop_ids |= set(user_managed_shops_all_branches(user).values_list("id", flat=True))

    return shop_ids


def get_accessible_shops(user):
    shop_ids = get_accessible_shop_ids(user)
    return Shop.objects.filter(id__in=shop_ids).order_by("name")


def user_can_manage_shop(user, shop):
    if shop.manager_id == user.id:
        return True
    if user.has_perm("module_shop.can_manage_assigned_shops") and shop.managed_by.filter(pk=user.id).exists():
        return True
    if user_managed_shops_all_branches(user).filter(pk=shop.id).exists():
        return True
    if user_allowed_branches(user).filter(shop_id=shop.id, is_active=True).exists():
        return True
    return False


def get_accessible_branch_ids_for_shop(user, shop_id):
    try:
        shop = Shop.objects.only("id", "manager_id").get(pk=shop_id)
    except Shop.DoesNotExist:
        return set()

    if shop.manager_id == user.id:
        return set(
            Branch.objects.filter(shop_id=shop_id, is_active=True).values_list("id", flat=True)
        )

    full_control_shop_ids = set(
        user_managed_shops_all_branches(user).filter(id=shop_id).values_list("id", flat=True)
    )

    branch_ids = set()

    if full_control_shop_ids:
        branch_ids |= set(
            Branch.objects.filter(shop_id=shop_id, is_active=True).values_list("id", flat=True)
        )

    branch_ids |= set(
        user_allowed_branches(user).filter(shop_id=shop_id, is_active=True).values_list("id", flat=True)
    )

    return branch_ids


def user_is_shop_manager(user, shop):
    """True if this user is the shop manager (full shop administration)."""
    if shop is None:
        return False
    return shop.manager_id == user.id


# Backward-compatible alias (remove when clients use is_shop_manager only).
user_is_shop_owner = user_is_shop_manager


def user_is_shop_branches_admin(user, shop):
    """True if the user can edit branch assignments for this shop (shop manager or staff)."""
    if user.is_staff:
        return True
    return user_is_shop_manager(user, shop)


def user_can_view_branch_permissions(user, shop):
    if user_is_shop_manager(user, shop):
        return True
    if user_managed_shops_all_branches(user).filter(pk=shop.id).exists():
        return True
    if user_allowed_branches(user).filter(shop_id=shop.id, is_active=True).exists():
        return True
    if user.has_perm("module_shop.can_manage_assigned_shops") and shop.managed_by.filter(pk=user.id).exists():
        return True
    return False


def user_is_branch_manager(user):
    return getattr(user, "role", None) == User.Role.BRANCH_MANAGER


def user_can_edit_product(user, shop):
    """Full product create/update/delete (shop manager only)."""
    return user_is_shop_manager(user, shop)


def user_can_toggle_product_offerable(user, product):
    """Branch managers may only flip ``is_offerable`` on products they can access."""
    if product is None:
        return False
    if user_is_shop_manager(user, product.shop):
        return True
    if not user_is_branch_manager(user):
        return False
    if product.branch_id is None:
        return False
    return user_can_manage_branch(user, product.branch)


def user_belongs_to_shop_for_branch_permissions(shop, target_user, target_bm=None):
    """
    Whether ``target_user`` may receive branch / head-manager assignments for ``shop``.
    Returns (belongs, branch_manager_profile).
    """
    if shop is None or target_user is None:
        return False, None

    if target_bm is None:
        target_bm = ensure_branch_manager(target_user)

    if target_user.pk == shop.manager_id:
        return True, target_bm

    if target_user.managed_shops.filter(pk=shop.pk).exists():
        return True, target_bm

    if target_bm is None:
        return False, None

    if target_bm.managed_shops_all_branches.filter(pk=shop.pk).exists():
        return True, target_bm
    if target_bm.allowed_branches.filter(shop=shop).exists():
        return True, target_bm
    if target_bm.created_for_shop_id == shop.id:
        return True, target_bm

    # Branch manager invited for this shop but not yet given any branch (first save)
    if target_user.role == User.Role.BRANCH_MANAGER:
        if target_bm.created_for_shop_id is None or target_bm.created_for_shop_id == shop.id:
            return True, target_bm

    return False, target_bm


def validate_exclusive_branch_assignments(shop, target_bm, branch_ids):
    """
    Each branch may be assigned to at most one branch manager (via allowed_branches).
    Returns an error message string, or None if valid.
    """
    if not branch_ids or target_bm is None:
        return None

    for branch_id in branch_ids:
        try:
            branch = Branch.objects.get(pk=branch_id, shop=shop)
        except Branch.DoesNotExist:
            continue

        conflict = (
            BranchManager.objects.filter(allowed_branches__id=branch_id)
            .exclude(user_ptr_id=target_bm.user_ptr_id)
            .distinct()
            .first()
        )
        if conflict is None:
            continue

        label = conflict.username or conflict.phone_number or str(conflict.pk)
        return (
            f"شعبه «{branch.name}» قبلاً به {label} اختصاص داده شده است. "
            "هر شعبه فقط می‌تواند یک مدیر شعبه داشته باشد."
        )
    return None


def user_can_manage_branch(user, branch):
    if branch is None:
        return False

    if not user_can_manage_shop(user, branch.shop):
        return False

    if branch.shop.manager_id == user.id:
        return True

    if user_managed_shops_all_branches(user).filter(pk=branch.shop_id).exists():
        return True

    return user_allowed_branches(user).filter(pk=branch.id).exists()


def filter_categories_by_branch_access(user, shop_id, queryset):
    branch_ids = get_accessible_branch_ids_for_shop(user, shop_id)
    return queryset.filter(
        Q(branch__isnull=True) | Q(branch_id__in=branch_ids)
    )


def filter_products_by_branch_access(user, shop_id, queryset):
    branch_ids = get_accessible_branch_ids_for_shop(user, shop_id)
    return queryset.filter(
        Q(branch__isnull=True) | Q(branch_id__in=branch_ids)
    )


def get_accessible_branches(user):
    shop_ids = get_accessible_shop_ids(user)
    if not shop_ids:
        return Branch.objects.none()
    all_branch_ids = set()
    for shop_id in shop_ids:
        all_branch_ids |= get_accessible_branch_ids_for_shop(user, shop_id)
    if not all_branch_ids:
        return Branch.objects.none()
    return (
        Branch.objects.filter(id__in=all_branch_ids)
        .select_related("shop")
        .order_by("shop__name", "name")
    )
