"""
Category and Product models compatible with main CustomerClub project.
"""
from django.contrib.auth import get_user_model
from django.db import models
from module_product.image_storage import finalize_product_image, product_image_upload_to
from module_shop.models import Shop, Branch

User = get_user_model()


class Category(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="categories")
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="categories",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "module_product_category"
        ordering = ("sort_order", "title")
        indexes = [
            models.Index(fields=["shop", "is_active"], name="category_shop_active_idx"),
        ]

    def __str__(self):
        return self.title


class Product(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="products")
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="products",
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        "Category",
        on_delete=models.SET_NULL,
        related_name="products",
        blank=True,
        null=True,
    )
    title = models.CharField(max_length=255)
    # Per-branch product identifier; can repeat in **other** branches.
    second_id = models.PositiveIntegerField()
    price = models.PositiveIntegerField()
    score = models.PositiveIntegerField()
    image = models.ImageField(upload_to=product_image_upload_to, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_offerable = models.BooleanField(
        default=False,
        help_text="If true, this product can appear in customer club special offers.",
    )

    class Meta:
        db_table = "module_product_product"
        # Allow the same `second_id` to be reused in different branches,
        # but keep it unique inside a single branch.
        unique_together = ("branch", "second_id")
        indexes = [
            models.Index(fields=["shop", "is_active"], name="product_shop_active_idx"),
            models.Index(fields=["branch"], name="product_branch_idx"),
            models.Index(fields=["category"], name="product_category_idx"),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if finalize_product_image(self):
            super().save(update_fields=["image"])


class UserSpecialOffer(models.Model):
    user = models.ForeignKey(
        "module_account.EndUser",
        on_delete=models.CASCADE,
        related_name="useroffer_set",
    )
    product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE,
        limit_choices_to={"is_offerable": True, "is_active": True},
    )
    offer_rate = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "module_product_userspecialoffer"
        unique_together = ("user", "product")
        indexes = [
            models.Index(fields=["user", "product"], name="user_offer_user_product_idx"),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.product.title}"


class SpecialOfferTransaction(models.Model):
    """Immutable ledger of user score changes (earn/spend), including special offers."""

    REASON_SPECIAL_OFFER = "special_offer"
    REASON_PURCHASE = "purchase"
    REASON_ADMIN_ADJUST = "admin_adjust"

    REASONS = (
        (REASON_SPECIAL_OFFER, "Special offer"),
        (REASON_PURCHASE, "Purchase"),
        (REASON_ADMIN_ADJUST, "Admin adjust"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="special_offer_transactions")
    delta = models.IntegerField()
    reason = models.CharField(max_length=32, choices=REASONS)
    product = models.ForeignKey(
        "Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="special_offer_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "module_product_specialoffertransaction"
        ordering = ("-created_at", "-id")

    def __str__(self):
        product_title = self.product.title if self.product_id else "-"
        return f"{self.user_id} - {product_title} - {self.created_at}"
