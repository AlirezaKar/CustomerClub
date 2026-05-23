from django import forms
from django.contrib import admin

from module_account.models import User

from . import models


class ProductADmin(admin.ModelAdmin):
    readonly_fields = ("image_url",)
    search_fields = ("title", "second_id")


class UserSpecialOfferAdminForm(forms.ModelForm):
    class Meta:
        model = models.UserSpecialOffer
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.filter(
            is_staff=False,
            is_superuser=False,
        ).order_by("phone_number", "username")
        self.fields["product"].queryset = models.Product.objects.filter(
            is_offerable=True,
            is_active=True,
        )


@admin.register(models.UserSpecialOffer)
class UserSpecialOfferAdmin(admin.ModelAdmin):
    form = UserSpecialOfferAdminForm
    list_display = ("user", "product", "offer_rate")
    search_fields = ("user__phone_number", "user__username", "product__title")
    raw_id_fields = ("user",)
    autocomplete_fields = ("product",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(
                is_staff=False,
                is_superuser=False,
            ).order_by("phone_number", "username")
        elif db_field.name == "product":
            kwargs["queryset"] = models.Product.objects.filter(
                is_offerable=True,
                is_active=True,
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(models.Product, ProductADmin)
admin.site.register(models.SpecialOfferTransaction)
admin.site.register(models.Category)
