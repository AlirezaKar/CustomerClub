from django.contrib import admin

from . import models
from django.contrib.auth.models import Group

admin.site.unregister(Group)

class UserAdmin(admin.ModelAdmin):
    exclude = (
        "phone_number_verification_code",
    )
    readonly_fields = (
        "phone_number_verification_code_last_change",
        "phone_number_verification_code_last_send",
    )

admin.site.register(models.User, UserAdmin)


@admin.register(models.NFCTag)
class NFCTagAdmin(admin.ModelAdmin):
    list_display = (
        "masked_uid",
        "user",
        "is_active",
        "created_at",
        "last_used_at",
        "failed_attempts",
        "locked_until",
    )
    list_filter = ("is_active",)
    search_fields = ("user__phone_number", "user__username")
    readonly_fields = ("uid",)

    @admin.display(description="UID")
    def masked_uid(self, obj: models.NFCTag) -> str:
        return obj.mask_uid()