from django.db.models import Max
from rest_framework import serializers

from module_shop.models import Shop, Branch
from module_product.models import Category, Product
from module_account.models import BranchManager, ShopManager, User
from module_account.profile_picture import ProfilePictureError, process_profile_picture
from module_account.role_helpers import get_branch_manager
from .permissions import (
    user_can_manage_shop,
    user_can_manage_branch,
    get_accessible_branch_ids_for_shop,
    user_is_shop_manager,
    user_can_edit_product,
    user_can_toggle_product_offerable,
    get_accessible_shops,
)

class ShopSummarySerializer(serializers.ModelSerializer):
    """Minimal shop info for nested profile (avoids circular / context issues)."""

    class Meta:
        model = Shop
        fields = ("id", "name")


class ShopSerializer(serializers.ModelSerializer):
    is_shop_manager = serializers.SerializerMethodField()
    # Deprecated alias for older clients.
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = ("id", "name", "manager", "is_shop_manager", "is_owner")

    def get_is_shop_manager(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.manager_id == request.user.id

    def get_is_owner(self, obj):
        return self.get_is_shop_manager(obj)


class ShopCreateSerializer(serializers.ModelSerializer):
    """Create a shop owned by the requesting user (only when they have no accessible shops)."""

    class Meta:
        model = Shop
        fields = ("name",)

    def validate_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Name is required.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        return Shop.objects.create(manager=request.user, name=validated_data["name"])


class BranchCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ("shop", "name")

    def validate_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Name is required.")
        return value

    def validate_shop(self, shop):
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Request context is required.")
        if not user_can_manage_shop(request.user, shop):
            raise serializers.ValidationError("You cannot add branches to this shop.")
        return shop


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ("id", "shop", "name", "is_active")


class BranchWithShopSerializer(serializers.ModelSerializer):
    """Branch with shop name for profile / list views."""
    shop_name = serializers.CharField(source="shop.name", read_only=True)

    class Meta:
        model = Branch
        fields = ("id", "shop", "shop_name", "name", "is_active")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "shop", "branch", "title", "description", "sort_order", "is_active")

    def validate_shop(self, value):
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Request context is required.")
        if not user_can_manage_shop(request.user, value):
            raise serializers.ValidationError("You cannot manage this shop.")
        return value

    def validate_branch(self, value):
        if value is None:
            return value
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Request context is required.")
        shop = self.initial_data.get("shop") or (self.instance.shop_id if self.instance else None)
        shop_id = int(shop) if isinstance(shop, str) else shop
        if shop is not None and value.shop_id != shop_id:
            raise serializers.ValidationError("Branch must belong to the selected shop.")
        if not user_can_manage_branch(request.user, value):
            raise serializers.ValidationError("You cannot manage this branch.")
        return value


class ProductSerializer(serializers.ModelSerializer):
    shop_name = serializers.CharField(source="shop.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    category_title = serializers.CharField(source="category.title", read_only=True)
    can_edit = serializers.SerializerMethodField()
    can_toggle_offerable = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "shop",
            "shop_name",
            "branch",
            "branch_name",
            "category",
            "category_title",
            "title",
            "second_id",
            "price",
            "score",
            "image",
            "is_active",
            "is_offerable",
            "can_edit",
            "can_toggle_offerable",
        )
        read_only_fields = ("id", "can_edit", "can_toggle_offerable")

    def get_can_edit(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return user_can_edit_product(request.user, obj.shop)

    def get_can_toggle_offerable(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return user_can_toggle_product_offerable(request.user, obj)


class ProductOfferableSerializer(serializers.ModelSerializer):
    """Branch managers may update only ``is_offerable``."""

    class Meta:
        model = Product
        fields = ("is_offerable",)


class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
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
        extra_kwargs = {
            "second_id": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        if not attrs.get("branch"):
            raise serializers.ValidationError({"branch": "انتخاب شعبه الزامی است."})
        second_id = attrs.get("second_id")
        if second_id in (None, ""):
            attrs.pop("second_id", None)
        else:
            branch = attrs.get("branch")
            if branch:
                qs = Product.objects.filter(branch=branch, second_id=second_id)
                if qs.exists():
                    raise serializers.ValidationError(
                        {"error": "شناسه ثانویه وارد شده قبلا استفاده شده است"}
                    )
        return attrs

    def create(self, validated_data):
        if "second_id" not in validated_data:
            branch = validated_data["branch"]
            current_max = (
                Product.objects.filter(branch=branch).aggregate(m=Max("second_id")).get("m")
            )
            validated_data["second_id"] = (current_max or 0) + 1
        return super().create(validated_data)

    def validate_shop(self, value):
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Request context is required.")
        if not user_can_manage_shop(request.user, value):
            raise serializers.ValidationError("You cannot manage this shop.")
        return value

    def validate_branch(self, value):
        if value is None:
            return value
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Request context is required.")
        shop = self.initial_data.get("shop")
        if shop is not None and value.shop_id != (int(shop) if isinstance(shop, str) else shop):
            raise serializers.ValidationError("Branch must belong to the selected shop.")
        if not user_can_manage_branch(request.user, value):
            raise serializers.ValidationError("You cannot manage this branch.")
        return value


class ProductUpdateSerializer(serializers.ModelSerializer):
    """Update existing products; shop is read-only, branch must match shop and permissions."""

    class Meta:
        model = Product
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
        read_only_fields = ("shop",)

    def validate(self, attrs):
        branch = attrs.get("branch")
        if branch is None and self.instance:
            branch = self.instance.branch
        second_id = attrs.get("second_id")
        if second_id is None and self.instance:
            second_id = self.instance.second_id
        if branch and second_id is not None:
            qs = Product.objects.filter(branch=branch, second_id=second_id)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"error": "شناسه ثانویه وارد شده قبلا استفاده شده است"}
                )
        return attrs

    def validate_branch(self, value):
        if value is None:
            return value
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Request context is required.")
        product = self.instance
        if not product:
            raise serializers.ValidationError("Product instance is required for update.")
        if value.shop_id != product.shop_id:
            raise serializers.ValidationError("Branch must belong to the product's shop.")
        if not user_can_manage_branch(request.user, value):
            raise serializers.ValidationError("You cannot manage this branch.")
        return value


class ShopKeeperCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    phone_number = serializers.CharField(max_length=11)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    shop = serializers.IntegerField(required=False, allow_null=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")
        user = request.user
        shop_id = attrs.get("shop")
        owned = list(Shop.objects.filter(manager=user).order_by("id"))
        if user.is_staff and not owned:
            if shop_id is None:
                attrs["_created_for_shop"] = None
                return attrs
            shop = Shop.objects.filter(pk=shop_id).first()
            if not shop:
                raise serializers.ValidationError({"shop": "Invalid shop."})
            attrs["_created_for_shop"] = shop
            return attrs
        if not owned:
            raise serializers.ValidationError("You must own a shop to create accounts.")
        if shop_id is not None:
            shop = Shop.objects.filter(pk=shop_id, manager=user).first()
            if not shop:
                raise serializers.ValidationError({"shop": "You do not own this shop."})
            attrs["_created_for_shop"] = shop
            return attrs
        if len(owned) == 1:
            attrs["_created_for_shop"] = owned[0]
            return attrs
        raise serializers.ValidationError(
            {"shop": "Select a shop when you own more than one."}
        )

    def create(self, validated_data):
        shop = validated_data.pop("_created_for_shop", None)
        validated_data.pop("shop", None)
        password = validated_data.pop("password")
        return BranchManager.objects.create_branch_manager(
            password=password,
            created_for_shop=shop,
            **validated_data,
        )


class RegisterSerializer(serializers.Serializer):
    """Public registration (no auth required). Creates user only; no shop."""
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    phone_number = serializers.CharField(max_length=11)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        return ShopManager.objects.create_shop_manager(password=password, **validated_data)


class ProfileSerializer(serializers.ModelSerializer):
    """Current user profile: read and update (no password)."""

    role = serializers.CharField(read_only=True)
    allowed_branches = serializers.SerializerMethodField()
    managed_shops_all_branches = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()
    remove_profile_picture = serializers.BooleanField(write_only=True, required=False)
    can_create_shop_keepers = serializers.SerializerMethodField()
    owns_shop = serializers.SerializerMethodField()
    default_products_shop_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "role",
            "username",
            "phone_number",
            "email",
            "first_name",
            "last_name",
            "age",
            "gender",
            "score",
            "card_uid",
            "profile_picture",
            "profile_picture_url",
            "remove_profile_picture",
            "managed_shops_all_branches",
            "allowed_branches",
            "can_create_shop_keepers",
            "can_create_shop",
            "owns_shop",
            "default_products_shop_id",
        )
        read_only_fields = (
            "id",
            "role",
            "score",
            "profile_picture_url",
            "can_create_shop_keepers",
            "can_create_shop",
            "owns_shop",
            "default_products_shop_id",
        )

    def get_allowed_branches(self, obj):
        bm = get_branch_manager(obj)
        if not bm:
            return []
        branches = bm.allowed_branches.select_related("shop").order_by("shop__name", "name")
        return BranchWithShopSerializer(branches, many=True).data

    def get_managed_shops_all_branches(self, obj):
        bm = get_branch_manager(obj)
        if not bm:
            return []
        shops = bm.managed_shops_all_branches.order_by("name")
        return ShopSummarySerializer(shops, many=True).data

    def get_owns_shop(self, obj):
        return Shop.objects.filter(manager=obj).exists()

    def get_default_products_shop_id(self, obj):
        if Shop.objects.filter(manager=obj).exists():
            return None
        return get_accessible_shops(obj).order_by("name").values_list("id", flat=True).first()

    def get_can_create_shop_keepers(self, obj):
        if getattr(obj, "is_staff", False):
            return True
        return Shop.objects.filter(manager=obj).exists()

    def get_profile_picture_url(self, obj):
        pic = getattr(obj, "profile_picture", None)
        if not pic:
            return None
        try:
            path = pic.url
        except ValueError:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(path)
        return path

    def validate_username(self, value):
        if self.instance and User.objects.filter(username=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        if not self.instance and User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_phone_number(self, value):
        if self.instance and User.objects.filter(phone_number=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        if not self.instance and User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def validate_profile_picture(self, value):
        if value is None:
            return value
        try:
            return process_profile_picture(value)
        except ProfilePictureError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def update(self, instance, validated_data):
        remove = bool(validated_data.pop("remove_profile_picture", False))
        if remove:
            validated_data.pop("profile_picture", None)
            previous = instance.profile_picture
            if previous:
                previous.delete(save=False)
            validated_data["profile_picture"] = None
            return super().update(instance, validated_data)
        if "profile_picture" in validated_data and validated_data["profile_picture"] is not None:
            previous = instance.profile_picture
            user = super().update(instance, validated_data)
            if previous and previous.name and user.profile_picture and previous.name != user.profile_picture.name:
                previous.delete(save=False)
            return user
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop("profile_picture", None)
        data.pop("remove_profile_picture", None)
        return data


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})

    def _get_user(self):
        request = self.context.get("request")
        if request is None or not getattr(request, "user", None) or not request.user.is_authenticated:
            raise serializers.ValidationError("لطفاً وارد حساب کاربری شوید.")
        return request.user

    def validate_current_password(self, value):
        user = self._get_user()
        if not user.check_password(value):
            raise serializers.ValidationError("رمز عبور فعلی نادرست است.")
        return value

    def save(self, **kwargs):
        user = self._get_user()
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class ShopUserBranchPermissionSerializer(serializers.ModelSerializer):
    """Per-shop view of a user's branch permissions."""

    is_shop_manager = serializers.SerializerMethodField()
    is_head_manager = serializers.SerializerMethodField()
    branches = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "phone_number",
            "email",
            "role",
            "is_shop_manager",
            "is_head_manager",
            "branches",
        )

    def get_is_shop_manager(self, obj):
        shop = self.context.get("shop")
        if not shop:
            return False
        return shop.manager_id == obj.pk

    def get_is_head_manager(self, obj):
        shop = self.context.get("shop")
        if not shop:
            return False
        bm = get_branch_manager(obj)
        if not bm:
            return False
        return bm.managed_shops_all_branches.filter(pk=shop.id).exists()

    def get_branches(self, obj):
        shop = self.context.get("shop")
        if not shop:
            return []
        bm = get_branch_manager(obj)
        if not bm:
            return []
        branches = bm.allowed_branches.filter(shop=shop).order_by("name")
        return BranchSerializer(branches, many=True).data
