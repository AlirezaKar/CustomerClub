"""
Account models: base User plus ShopManager, BranchManager, and EndUser roles.
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from module_account.profile_storage import finalize_profile_picture, profile_picture_upload_to

GENDERS = (
    ("male", "Male"),
    ("female", "Female"),
)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required.")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.SHOP_MANAGER)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        user = self.create_user(username, password, **extra_fields)
        ShopManager.objects.get_or_create(user_ptr=user)
        return user


class User(AbstractUser):
    """
    Base account: credentials, profile, verification, and customer-club score.
    Use ShopManager, BranchManager, or EndUser for role-specific behavior.
    """

    class Role(models.TextChoices):
        SHOP_MANAGER = "shop_manager", "Shop manager"
        BRANCH_MANAGER = "branch_manager", "Branch manager"
        END_USER = "end_user", "End user"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        db_index=True,
        default=Role.BRANCH_MANAGER,
    )
    phone_number = models.CharField(max_length=11, unique=True, blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDERS, blank=True, null=True)
    score = models.PositiveIntegerField(default=0)
    card_uid = models.CharField(max_length=255, blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to=profile_picture_upload_to,
        blank=True,
        null=True,
        verbose_name="profile picture",
    )
    phone_number_verification_code = models.PositiveBigIntegerField(blank=True, null=True)
    phone_number_verification_code_last_change = models.DateTimeField(blank=True, null=True)
    phone_number_verification_code_last_send = models.DateTimeField(blank=True, null=True)

    objects = UserManager()

    class Meta:
        indexes = [
            models.Index(fields=["phone_number"]),
            models.Index(fields=["card_uid"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return self.username or str(self.pk)

    def __repr__(self):
        role = getattr(self, "role", None) or "?"
        return f"<{self.__class__.__name__} pk={self.pk} username={self.username!r} role={role!r}>"

    def save(self, *args, **kwargs):
        # Verification codes are generated only when sending login SMS (same as main server).
        super().save(*args, **kwargs)
        if finalize_profile_picture(self):
            super().save(update_fields=["profile_picture"])

    @property
    def can_create_shop(self):
        """Whether this account may register a new shop in the management app."""
        return self.role == self.Role.SHOP_MANAGER

    def get_useroffer_set(self):
        from module_product.models import UserSpecialOffer

        return (
            UserSpecialOffer.objects.filter(
                user=self,
                product__is_active=True,
                product__is_offerable=True,
                product__score__lte=self.score,
            )
            .select_related("product")
            .order_by("-offer_rate")
        )

    def get_role_profile(self):
        """Return the role-specific model instance, or None if missing."""
        if self.role == self.Role.SHOP_MANAGER:
            try:
                return self.shopmanager
            except ShopManager.DoesNotExist:
                return None
        if self.role == self.Role.BRANCH_MANAGER:
            try:
                return self.branchmanager
            except BranchManager.DoesNotExist:
                return None
        if self.role == self.Role.END_USER:
            try:
                return self.enduser
            except EndUser.DoesNotExist:
                return None
        return None


class ShopManagerManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().filter(role=User.Role.SHOP_MANAGER)

    def create_shop_manager(self, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.SHOP_MANAGER)
        user = ShopManager(**extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user


class ShopManager(User):
    """Owns one or more shops; full shop administration."""

    objects = ShopManagerManager()

    class Meta:
        proxy = False
        verbose_name = "shop manager"
        verbose_name_plural = "shop managers"

    def save(self, *args, **kwargs):
        self.role = User.Role.SHOP_MANAGER
        super().save(*args, **kwargs)


class BranchManagerManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().filter(role=User.Role.BRANCH_MANAGER)

    def create_branch_manager(self, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.BRANCH_MANAGER)
        user = BranchManager(**extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user


class BranchManager(User):
    """Manages assigned branches (and optionally all branches of a shop)."""

    managed_shops_all_branches = models.ManyToManyField(
        "module_shop.Shop",
        related_name="all_branch_managers",
        blank=True,
    )
    allowed_branches = models.ManyToManyField(
        "module_shop.Branch",
        related_name="allowed_users",
        blank=True,
    )
    created_for_shop = models.ForeignKey(
        "module_shop.Shop",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_invited_for_shop",
    )

    objects = BranchManagerManager()

    class Meta:
        proxy = False
        verbose_name = "branch manager"
        verbose_name_plural = "branch managers"

    def save(self, *args, **kwargs):
        self.role = User.Role.BRANCH_MANAGER
        super().save(*args, **kwargs)

    def get_managed_branches(self, shop=None):
        from module_shop.models import Branch

        if shop is not None:
            full_access_branches = Branch.objects.filter(
                shop=shop,
                shop__in=self.managed_shops_all_branches.all(),
            )
            specific_branches = self.allowed_branches.filter(shop=shop)
        else:
            full_access_branches = Branch.objects.filter(
                shop__in=self.managed_shops_all_branches.all()
            )
            specific_branches = self.allowed_branches.all()

        return (full_access_branches | specific_branches).distinct()

    def get_accessible_products(self, shop=None, branch=None, only_active=True):
        from module_product.models import Product

        managed_branches = self.get_managed_branches(shop=shop)

        if branch is not None:
            if not managed_branches.filter(pk=branch.pk).exists():
                return Product.objects.none()
            qs = Product.objects.filter(branch=branch)
        else:
            qs = Product.objects.filter(branch__in=managed_branches)

        if shop is not None:
            qs = qs.filter(branch__shop=shop)

        if only_active and hasattr(Product, "is_active"):
            qs = qs.filter(is_active=True)

        return qs.distinct()


class EndUserManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().filter(role=User.Role.END_USER)

    def create_end_user(self, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.END_USER)
        user = EndUser(**extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user


class EndUser(User):
    """Customer club member: logs in on the public site for offers and score."""

    objects = EndUserManager()

    class Meta:
        proxy = False
        verbose_name = "end user"
        verbose_name_plural = "end users"

    def save(self, *args, **kwargs):
        self.role = User.Role.END_USER
        super().save(*args, **kwargs)


