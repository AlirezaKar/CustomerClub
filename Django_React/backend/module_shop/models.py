from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Shop(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shops",
    )

    def __str__(self) -> str:
        owner_label = self.owner.username if self.owner_id else "—"
        return f"{self.name} || {owner_label}"


class Branch(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)
        indexes = [
            models.Index(fields=["shop", "is_active"], name="branch_shop_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.shop.name} — {self.name}"


class Score(models.Model):
    price_for_score = models.PositiveIntegerField(default=1000000)
    score_for_purchase = models.PositiveBigIntegerField(default=1)
    shop = models.OneToOneField(Shop, on_delete=models.CASCADE, related_name="score")

    def __str__(self) -> str:
        return f"{self.shop.name} || {self.score_for_purchase} Score : {self.price_for_score} Toman "
