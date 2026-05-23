from rest_framework import serializers

from . import models


class ProductSerializer(serializers.ModelSerializer):
    category_id= serializers.IntegerField(source= "category.id", read_only= True)
    category_title= serializers.CharField(source= "category.title", read_only= True)
    image_url= serializers.SerializerMethodField()

    class Meta:
        model= models.Product
        fields= (
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
        return obj.image_url


class ProductAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model= models.Product
        fields= ("id", "second_id", "title", "price", "score", "image", "image_url", "is_offerable", "is_active", "category")
        read_only_fields= ("id", "image_url")
        extra_kwargs= {
            "second_id": {"required": False, "allow_null": True},
            "image": {"required": False, "allow_null": True},
            "category": {"allow_null": True, "required": False},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        shop= self.context.get("shop")
        if shop and "category" in self.fields:
            self.fields["category"].queryset= models.Category.objects.filter(
                shop=shop,
                is_active=True,
            )

    def validate_category(self, category):
        if category is None:
            return category
        shop= self.context.get("shop")
        if shop and category.shop_id!= shop.id:
            raise serializers.ValidationError("Category must belong to the same shop.")
        return category

    def create(self, validated_data):
        shop= self.context.get("shop")
        if not shop:
            raise serializers.ValidationError("Shop context is required.")
        validated_data["shop"]= shop
        return super().create(validated_data)


class CategorySerializer(serializers.ModelSerializer):
    products= serializers.SerializerMethodField()

    class Meta:
        model= models.Category
        fields= ("id", "title", "description", "sort_order", "is_active", "products")

    def _products_queryset(self, category):
        products= category.products.all()
        request= self.context.get("request")
        shop= self.context.get("shop") or category.shop
        is_shop_owner= (
            request
            and request.user.is_authenticated
            and shop.owner_id == request.user.id
        )
        if not is_shop_owner:
            products= products.filter(is_active=True)
        return products

    def get_products(self, category):
        return ProductSerializer(self._products_queryset(category), many=True).data


class CategoryDetailSerializer(serializers.ModelSerializer):
    products= ProductSerializer(many= True, read_only= True)
    product_ids= serializers.PrimaryKeyRelatedField(
        queryset= models.Product.objects.none(),
        many= True,
        required= False,
        write_only= True,
    )

    class Meta:
        model= models.Category
        fields= ("id", "title", "description", "sort_order", "is_active", "products", "product_ids")
        read_only_fields= ("id", "products")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        shop= self.context.get("shop")
        if shop:
            self.fields["product_ids"].queryset= models.Product.objects.filter(
                shop=shop,
                is_active=True,
            )

    def validate_product_ids(self, products):
        shop= self.context.get("shop")
        if not shop:
            raise serializers.ValidationError("Shop context is required.")
        invalid_products= [product.id for product in products if product.shop_id!= shop.id]
        if invalid_products:
            raise serializers.ValidationError("All products must belong to the same shop.")
        return products

    def create(self, validated_data):
        products= validated_data.pop("product_ids", [])
        shop= self.context.get("shop")
        if not shop:
            raise serializers.ValidationError("Shop context is required.")
        category= models.Category.objects.create(shop= shop, **validated_data)
        self._apply_products(category, products)
        return category

    def update(self, instance, validated_data):
        products= validated_data.pop("product_ids", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if products is not None:
            self._apply_products(instance, products)
        return instance

    def _apply_products(self, category, products):
        product_ids= [product.id for product in products]
        models.Product.objects.filter(category= category).exclude(id__in= product_ids).update(category= None)
        for product in products:
            product.category= category
            product.save(update_fields= ["category"])


class UserOfferSerializer(serializers.ModelSerializer):
    product= ProductSerializer(read_only= True, many= False)

    class Meta:
        model= models.UserSpecialOffer
        fields= ["product", "offer_rate"]
