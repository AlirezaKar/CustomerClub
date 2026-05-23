from rest_framework import serializers

from module_product import serializers as module_product_serializers
from . import models


class ScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model= models.Score
        fields= ["price_for_score", "score_for_purchase"]

    # def create(self, validated_data):
    #     score_data= validated_data.pop("score", None)
    #     shop= models.Shop.objects.create(**validated_data)
    #     if score_data:
    #         models.Score.objects.create(shop= shop, **score_data)
    #     return shop

    # def update(self, instance, validated_data):
    #     score_data= validated_data.pop("score", None)
    #     for attr, value in validated_data.items():
    #         setattr(instance, attr, value)
    #     instance.save()

    #     if score_data:
    #         if hasattr(instance, "score"):
    #             for attr, value in score_data.items():
    #                 setattr(instance.score, attr, value)
    #             instance.score.save()
    #         else:
    #             models.Score.objects.create(shop= instance, **score_data)

    #     return instance


class ShopSerializer(serializers.ModelSerializer):
    # product_set= module_product_serializers.ProductSerializer(read_only= True, many= True)
    # score= ScoreSerializer(many= False)

    class Meta:
        model= models.Shop
        # fields= "__all__"
        # fields= ["name", "product_set", "score"]
        fields= ["id", "name"]


class ShopSettingsSerializer(serializers.ModelSerializer):
    score= ScoreSerializer(required= False)

    class Meta:
        model= models.Shop
        fields= ["id", "name", "score"]

    def update(self, instance, validated_data):
        score_data= validated_data.pop("score", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if score_data is not None:
            score_instance= getattr(instance, "score", None)
            if score_instance:
                for attr, value in score_data.items():
                    setattr(score_instance, attr, value)
                score_instance.save()
            else:
                models.Score.objects.create(shop= instance, **score_data)

        return instance