from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import models, transaction, IntegrityError
from django.db.models import Max

from module_shop import models as module_shop_models

from module_product.image_storage import finalize_product_image, product_image_upload_to

User = get_user_model()


class Category(models.Model):
    shop = models.ForeignKey(module_shop_models.Shop, on_delete=models.CASCADE, related_name="categories")
    branch = models.ForeignKey(
        module_shop_models.Branch,
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
        ordering = ("sort_order", "title")

    def __str__(self) -> str:
        return self.title


class Product(models.Model):
    shop = models.ForeignKey(module_shop_models.Shop, on_delete=models.CASCADE)
    branch = models.ForeignKey(
        module_shop_models.Branch,
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
    # Per-branch product identifier from management; unique within branch.
    second_id = models.PositiveIntegerField()
    price = models.PositiveIntegerField()
    score = models.PositiveIntegerField()
    image = models.ImageField(upload_to=product_image_upload_to, null=True, blank=True)
    remote_image_url = models.URLField(max_length=500, blank=True, null=True)
    is_offerable = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("branch", "second_id")
        indexes = [
            models.Index(fields=["shop", "is_active"], name="product_shop_active_idx"),
            models.Index(fields=["branch"], name="product_branch_idx"),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if self.second_id is None:
            for _attempt in range(5):
                with transaction.atomic():
                    branch_filter = {"branch": self.branch} if self.branch_id else {}
                    max_second_id = Product.objects.filter(**branch_filter).aggregate(m=Max("second_id"))["m"]
                    self.second_id = 0 if max_second_id is None else int(max_second_id) + 1
                    try:
                        super().save(*args, **kwargs)
                        break
                    except IntegrityError:
                        self.second_id = None
                        continue
            else:
                raise IntegrityError("Could not allocate a unique second_id after retries.")
        else:
            super().save(*args, **kwargs)

        if finalize_product_image(self):
            super().save(update_fields=["image"])

    @property
    def image_url(self):
        if self.image:
            base = getattr(settings, "PUBLIC_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
            return f"{base}{self.image.url}"
        if self.remote_image_url:
            return self.remote_image_url
        return None


class UserSpecialOffer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="useroffer_set")
    product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE,
        limit_choices_to={"is_offerable": True, "is_active": True},
    )
    offer_rate = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["user", "product"], name="user_offer_user_product_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - {self.product.title}"


class SpecialOfferTransaction(models.Model):
    """
    Immutable ledger of user score changes (earn/spend), including special offers.
    """

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
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        product_title = self.product.title if self.product_id else "-"
        return f"{self.user.username} - {product_title} - {self.created_at}"
