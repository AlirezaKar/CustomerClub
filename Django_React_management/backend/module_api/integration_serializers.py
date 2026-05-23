from rest_framework import serializers

from module_account.models import EndUser, User
from module_product.models import Category, Product, SpecialOfferTransaction, UserSpecialOffer
from module_shop.models import Branch, Shop


class IntegrationShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ("id", "name")


class IntegrationEndUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = EndUser
        fields = ("id", "username", "phone_number", "age", "gender", "card_uid", "score")


class IntegrationEndUserRegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=11)
    age = serializers.IntegerField(min_value=1, max_value=150)
    gender = serializers.ChoiceField(choices=[("male", "Male"), ("female", "Female")])
    card_uid = serializers.CharField(max_length=255, required=False, allow_blank=True)
    uid_code = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        card_uid = (attrs.get("card_uid") or "").strip() or None
        uid_code = (attrs.get("uid_code") or "").strip() or None
        resolved = uid_code or card_uid
        if resolved:
            resolved = resolved.lower()
            if User.objects.filter(card_uid__iexact=resolved).exists():
                raise serializers.ValidationError(
                    {"uid_code": "کارت قبلا ثبت شده است"}
                )
        attrs["card_uid"] = resolved
        return attrs

    def validate_phone_number(self, value):
        value = (value or "").strip()
        if len(value) != 11 or not value.isdigit():
            raise serializers.ValidationError("Phone number must be 11 digits.")
        if (
            User.objects.filter(phone_number=value).exists()
            or User.objects.filter(username=value).exists()
        ):
            raise serializers.ValidationError("شماره تلفن قبلا ثبت شده است.")
        return value

    def create(self, validated_data):
        phone_number = validated_data["phone_number"]
        card_uid = validated_data.get("card_uid")
        validated_data.pop("uid_code", None)
        user = EndUser.objects.create_end_user(
            username=phone_number,
            phone_number=phone_number,
            age=validated_data["age"],
            gender=validated_data["gender"],
            card_uid=card_uid,
        )
        user.set_unusable_password()
        user.save(update_fields=[])
        return user


class IntegrationSpecialOfferSubmitSerializer(serializers.Serializer):
    """Payload from the main kiosk server after it completes offer redemption."""

    user_id = serializers.IntegerField(min_value=1)
    product_id = serializers.IntegerField(min_value=1)
    user_score = serializers.IntegerField(min_value=0)


class IntegrationBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ("id", "name", "is_active")


class IntegrationCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "title", "description", "sort_order", "is_active")


class IntegrationProductSerializer(serializers.ModelSerializer):
    shop = IntegrationShopSerializer(read_only=True)
    branch = IntegrationBranchSerializer(read_only=True, allow_null=True)
    category = IntegrationCategorySerializer(read_only=True, allow_null=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "second_id",
            "title",
            "price",
            "score",
            "is_active",
            "is_offerable",
            "image_url",
            "shop",
            "branch",
            "category",
        )

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url


class IntegrationUserSpecialOfferSerializer(serializers.ModelSerializer):
    product = IntegrationProductSerializer(read_only=True)
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)

    class Meta:
        model = UserSpecialOffer
        fields = ("id", "phone_number", "offer_rate", "product")


class IntegrationSpecialOfferTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialOfferTransaction
        fields = ("id", "user", "delta", "reason", "product", "created_at")


class IntegrationKioskProductSerializer(serializers.ModelSerializer):
    """Product shape expected by the public kiosk frontend."""

    category_id = serializers.IntegerField(source="category.id", read_only=True)
    category_title = serializers.CharField(source="category.title", read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "second_id",
            "title",
            "price",
            "score",
            "image_url",
            "is_offerable",
            "is_active",
            "category_id",
            "category_title",
        )

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url


class IntegrationKioskCategorySerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "title", "description", "sort_order", "is_active", "products")

    def get_products(self, category):
        products = category.products.filter(is_active=True).order_by("second_id", "id")
        return IntegrationKioskProductSerializer(
            products,
            many=True,
            context=self.context,
        ).data


class IntegrationSpecialOfferRedeemSerializer(serializers.Serializer):
    """Redeem a special offer on the management server (stateless kiosk)."""

    user_id = serializers.IntegerField(min_value=1)
    product_id = serializers.IntegerField(min_value=1)


class IntegrationEndUserCardSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    card_uid = serializers.CharField(max_length=255, required=False, allow_blank=True)
    uid = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        resolved = (attrs.get("uid") or attrs.get("card_uid") or "").strip().lower()
        attrs["card_uid"] = resolved or None
        return attrs
