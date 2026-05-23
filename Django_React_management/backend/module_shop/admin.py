from django.contrib import admin
from .models import Shop, Branch, Score


class ScoreInline(admin.StackedInline):
    model = Score
    extra = 0
    max_num = 1
    can_delete = False


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0
    fk_name = "shop"
    show_change_link = True
    fields = ("name", "is_active")


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "manager", "branch_count")
    list_filter = ("manager",)
    search_fields = ("name", "manager__username", "manager__phone_number")
    list_per_page = 25
    autocomplete_fields = ["manager", "managed_by"]

    def branch_count(self, obj):
        return obj.branches.count()

    branch_count.short_description = "Branches"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("manager")

    def get_inlines(self, request, obj):
        if obj:
            return [ScoreInline, BranchInline]
        return []


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "shop", "is_active")
    list_filter = ("shop", "is_active")
    search_fields = ("name", "shop__name")
    list_per_page = 25
    autocomplete_fields = ["shop"]
    list_select_related = ["shop"]


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ("shop", "price_for_score", "score_for_purchase")
    list_per_page = 25
    autocomplete_fields = ["shop"]
    list_select_related = ["shop"]
