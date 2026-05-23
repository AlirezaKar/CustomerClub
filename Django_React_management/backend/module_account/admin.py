from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group

from .models import BranchManager, EndUser, ShopManager, User

admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "role", "phone_number", "email", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "phone_number", "email")
    ordering = ("username",)
    list_per_page = 25

    fieldsets = (
        (None, {"fields": ("username", "password", "role")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        ("Contact & Profile", {"fields": ("phone_number", "age", "gender", "card_uid", "profile_picture")}),
        ("Score", {"fields": ("score",)}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "phone_number", "role", "password1", "password2"),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("groups")


class RoleUserAdmin(UserAdmin):
    """
    Admin for multi-table inheritance role models (EndUser, ShopManager, BranchManager).

    Must bypass UserAdmin.get_queryset and use each subclass model's default manager so
    changelist rows are EndUser/ShopManager/BranchManager instances (with user_ptr_id),
    not plain User rows.
    """

    def get_queryset(self, request):
        return super(UserAdmin, self).get_queryset(request).prefetch_related("groups")


@admin.register(ShopManager)
class ShopManagerAdmin(RoleUserAdmin):
    list_display = ("username", "phone_number", "email", "is_active")


@admin.register(BranchManager)
class BranchManagerAdmin(RoleUserAdmin):
    list_display = ("username", "phone_number", "email", "is_active")
    raw_id_fields = [
        "groups",
        "user_permissions",
        "managed_shops_all_branches",
        "allowed_branches",
        "created_for_shop",
    ]

    fieldsets = UserAdmin.fieldsets + (
        (
            "Branch access",
            {
                "fields": ("managed_shops_all_branches", "allowed_branches", "created_for_shop"),
            },
        ),
    )


@admin.register(EndUser)
class EndUserAdmin(RoleUserAdmin):
    list_display = ("username", "phone_number", "score", "is_active")

