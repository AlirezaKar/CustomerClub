from django import forms
from django.contrib import admin

from module_account.models import EndUser

from .models import (
    Category,
    Product,
    SpecialOfferTransaction,
    UserSpecialOffer,
)


class UserSpecialOfferAdminForm(forms.ModelForm):
    class Meta:
        model = UserSpecialOffer
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = EndUser.objects.order_by("phone_number", "username")
        self.fields["product"].queryset = Product.objects.filter(
            is_offerable=True,
            is_active=True,
        ).select_related("shop", "branch")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "shop", "branch", "sort_order", "is_active")
    list_filter = ("shop", "branch", "is_active")
    search_fields = ("title",)
    list_per_page = 25
    autocomplete_fields = ["shop", "branch"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "branch",
        "category",
        "second_id",
        "price",
        "score",
        "is_active",
        "is_offerable",
    )
    list_display_links = ("title",)
    list_editable = ("is_offerable",)
    list_filter = ("branch", "is_active", "is_offerable")
    search_fields = ("title", "second_id")
    list_per_page = 25
    autocomplete_fields = ["shop", "branch", "category"]
    fields = (
        "shop",
        "branch",
        "category",
        "title",
        "second_id",
        "price",
        "score",
        "image",
        "is_active",
        "is_offerable",
    )

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        model_name = request.GET.get("model_name")
        field_name = request.GET.get("field_name")
        if model_name == "userspecialoffer" and field_name == "product":
            queryset = queryset.filter(is_offerable=True, is_active=True)
        return queryset, use_distinct


@admin.register(UserSpecialOffer)
class UserSpecialOfferAdmin(admin.ModelAdmin):
    form = UserSpecialOfferAdminForm
    list_display = ("user", "product", "offer_rate")
    list_filter = ("product__shop", "product__branch", "product__is_offerable")
    search_fields = ("user__phone_number", "user__username", "product__title")
    raw_id_fields = ("user",)
    autocomplete_fields = ("product",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = EndUser.objects.order_by("phone_number", "username")
        elif db_field.name == "product":
            kwargs["queryset"] = Product.objects.filter(
                is_offerable=True,
                is_active=True,
            ).select_related("shop", "branch")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(SpecialOfferTransaction)
class SpecialOfferTransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "delta", "reason", "product", "created_at")
    list_filter = ("reason", "created_at")
    search_fields = ("user__phone_number", "user__username", "product__title")
    raw_id_fields = ("user", "product")
    readonly_fields = ("created_at",)
    ordering = ("-created_at", "-id")
