from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.response import Response
from module_account.models import EndUser, User
from module_product.models import Category, Product, SpecialOfferTransaction, UserSpecialOffer
from module_shop.models import Shop

from .integration_base import IntegrationAPIView
from .persian_errors import extract_error_message, error_response, integrity_conflict_message
from .dataset_import_service import run_dataset_import
from .integration_serializers import (
    IntegrationEndUserCardSerializer,
    IntegrationEndUserRegisterSerializer,
    IntegrationEndUserSerializer,
    IntegrationKioskCategorySerializer,
    IntegrationShopSerializer,
    IntegrationSpecialOfferRedeemSerializer,
    IntegrationSpecialOfferSubmitSerializer,
    IntegrationSpecialOfferTransactionSerializer,
    IntegrationUserSpecialOfferSerializer,
)


class CustomerOffersIntegrationView(IntegrationAPIView):
    """
    Returns active customer offers for a phone number.
    Called by the main CustomerClub server (not end users).
    """

    def get(self, request):
        phone_number = (request.query_params.get("phone_number") or "").strip()
        if not phone_number:
            return error_response("phone_number query parameter is required", status.HTTP_400_BAD_REQUEST)

        shop_id = request.query_params.get("shop_id")
        if shop_id not in (None, ""):
            try:
                shop_id = int(shop_id)
            except (TypeError, ValueError):
                return Response(
                    {"error": "شناسه فروشگاه باید عدد باشد."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            shop_id = None

        offers_qs = (
            UserSpecialOffer.objects.filter(
                user__phone_number=phone_number,
                user__role=User.Role.END_USER,
                product__is_active=True,
                product__is_offerable=True,
            )
            .select_related(
                "user",
                "product",
                "product__shop",
                "product__branch",
                "product__category",
            )
            .order_by("-offer_rate", "id")
        )
        if shop_id is not None:
            offers_qs = offers_qs.filter(product__shop_id=shop_id)

        serializer = IntegrationUserSpecialOfferSerializer(
            offers_qs,
            many=True,
            context={"request": request},
        )
        return Response({"offers": serializer.data})


class ShopsIntegrationView(IntegrationAPIView):
    """
    Lists shops available on the public CustomerClub kiosk.
    Called by the main server (not end users).
    """

    def get(self, request):
        shops = Shop.objects.all().order_by("name")
        serializer = IntegrationShopSerializer(shops, many=True)
        return Response({"shops": serializer.data})


class EndUserIntegrationView(IntegrationAPIView):
    """
    End-user lookup and registration for the public CustomerClub site.
    Called by the main server (not end users).
    """

    def get(self, request):
        phone_number = (request.query_params.get("phone_number") or "").strip()
        card_uid = (
            (request.query_params.get("uid_code") or request.query_params.get("card_uid") or "")
            .strip()
            .lower()
        )
        user_id = request.query_params.get("user_id")

        if user_id not in (None, ""):
            try:
                user_id = int(user_id)
            except (TypeError, ValueError):
                return Response(
                    {"error": "شناسه کاربر باید عدد باشد."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user = EndUser.objects.filter(pk=user_id).first()
        elif phone_number:
            user = EndUser.objects.filter(phone_number=phone_number).first()
        elif card_uid:
            user = EndUser.objects.filter(card_uid__iexact=card_uid).first()
        else:
            return Response(
                {"error": "شماره تلفن، شناسه کارت، یا شناسه کاربر الزامی است."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user:
            return Response({"exists": False})

        serializer = IntegrationEndUserSerializer(user)
        return Response({"exists": True, "user": serializer.data})

    def post(self, request):
        serializer = IntegrationEndUserRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            if "phone_number" in errors:
                return Response(
                    {"error": errors["phone_number"][0]},
                    status=status.HTTP_409_CONFLICT,
                )
            if "card_uid" in errors or "uid_code" in errors:
                field_errors = errors.get("uid_code") or errors.get("card_uid")
                return Response(
                    {"error": field_errors[0]},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response(
                {"error": extract_error_message(errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = serializer.save()
        except IntegrityError as exc:
            return Response(
                {"error": integrity_conflict_message(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {"user": IntegrationEndUserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class ShopCatalogIntegrationView(IntegrationAPIView):
    """
    Active categories and products for a shop (public kiosk catalog).
    """

    def get(self, request):
        shop_id = request.query_params.get("shop_id")
        if shop_id in (None, ""):
            return error_response("shop_id query parameter is required", status.HTTP_400_BAD_REQUEST)
        try:
            shop_id = int(shop_id)
        except (TypeError, ValueError):
            return Response(
                {"error": "شناسه فروشگاه باید عدد باشد."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not Shop.objects.filter(pk=shop_id).exists():
            return Response(
                {"error": "فروشگاه یافت نشد."},
                status=status.HTTP_404_NOT_FOUND,
            )

        categories = (
            Category.objects.filter(shop_id=shop_id, is_active=True)
            .prefetch_related("products")
            .order_by("sort_order", "id")
        )
        serializer = IntegrationKioskCategorySerializer(
            categories,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


class SpecialOfferRedeemIntegrationView(IntegrationAPIView):
    """
    Validate and redeem a special offer entirely on the management server.
    Used by the stateless kiosk (no local business database).
    """

    def post(self, request):
        serializer = IntegrationSpecialOfferRedeemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": extract_error_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_id = serializer.validated_data["user_id"]
        product_id = serializer.validated_data["product_id"]

        user = EndUser.objects.filter(pk=user_id).first()
        if not user:
            return Response(
                {"error": "کاربر یافت نشد."},
                status=status.HTTP_404_NOT_FOUND,
            )

        product = Product.objects.filter(
            pk=product_id,
            is_active=True,
            is_offerable=True,
        ).first()
        if not product:
            return Response(
                {"error": "محصول یافت نشد یا قابل استفاده در پیشنهاد ویژه نیست."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not UserSpecialOffer.objects.filter(user=user, product=product).exists():
            return Response(
                {"error": "این پیشنهاد به شما تعلق ندارد."},
                status=status.HTTP_403_FORBIDDEN,
            )

        score_cost = int(product.score)
        if int(user.score) < score_cost:
            return Response(
                {"error": "امتیاز کافی نیست."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            locked_user = User.objects.select_for_update().get(pk=user.pk)
            if int(locked_user.score) < score_cost:
                return Response(
                    {"error": "امتیاز کافی نیست."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            locked_user.score -= score_cost
            locked_user.save(update_fields=["score"])
            offer_tx = SpecialOfferTransaction.objects.create(
                user=locked_user,
                delta=-score_cost,
                reason=SpecialOfferTransaction.REASON_SPECIAL_OFFER,
                product=product,
            )

        return Response(
            {
                "transaction": IntegrationSpecialOfferTransactionSerializer(offer_tx).data,
                "user": IntegrationEndUserSerializer(locked_user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class EndUserCardIntegrationView(IntegrationAPIView):
    """Link or clear NFC card UID for an end user (stateless kiosk)."""

    def post(self, request):
        serializer = IntegrationEndUserCardSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": extract_error_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_id = serializer.validated_data["user_id"]
        card_uid = serializer.validated_data.get("card_uid")

        user = EndUser.objects.filter(pk=user_id).first()
        if not user:
            return Response(
                {"error": "کاربر یافت نشد."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if card_uid and EndUser.objects.filter(card_uid__iexact=card_uid).exclude(pk=user_id).exists():
            return Response(
                {"error": "کارت قبلا ثبت شده است"},
                status=status.HTTP_409_CONFLICT,
            )

        user.card_uid = card_uid.lower() if card_uid else None
        try:
            user.save(update_fields=["card_uid"])
        except IntegrityError:
            return Response(
                {"error": "کارت قبلا ثبت شده است"},
                status=status.HTTP_409_CONFLICT,
            )
        return Response({"user": IntegrationEndUserSerializer(user).data})

    def delete(self, request):
        serializer = IntegrationEndUserCardSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": extract_error_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_id = serializer.validated_data["user_id"]
        user = EndUser.objects.filter(pk=user_id).first()
        if not user:
            return Response(
                {"error": "کاربر یافت نشد."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user.card_uid = None
        user.save(update_fields=["card_uid"])
        return Response({"user": IntegrationEndUserSerializer(user).data})


class SpecialOfferTransactionIntegrationView(IntegrationAPIView):
    """
    Mirror a special-offer redemption that already completed on the main kiosk server.
    Creates SpecialOfferTransaction and syncs score on the management database.
    """

    def post(self, request):
        serializer = IntegrationSpecialOfferSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": extract_error_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_id = serializer.validated_data["user_id"]
        product_id = serializer.validated_data["product_id"]
        user_score = serializer.validated_data["user_score"]

        user = EndUser.objects.filter(pk=user_id).first()
        if not user:
            return Response(
                {"error": "کاربر یافت نشد."},
                status=status.HTTP_404_NOT_FOUND,
            )

        product = Product.objects.filter(pk=product_id).first()
        if not product:
            return Response(
                {"error": "محصول یافت نشد."},
                status=status.HTTP_404_NOT_FOUND,
            )

        score_delta = int(user_score) - int(user.score)
        with transaction.atomic():
            locked_user = User.objects.select_for_update().get(pk=user.pk)
            locked_user.score = int(user_score)
            locked_user.save(update_fields=["score"])

            offer_tx = SpecialOfferTransaction.objects.create(
                user=locked_user,
                delta=score_delta,
                reason=SpecialOfferTransaction.REASON_SPECIAL_OFFER,
                product=product,
            )

        return Response(
            {
                "transaction": IntegrationSpecialOfferTransactionSerializer(offer_tx).data,
                "user": IntegrationEndUserSerializer(locked_user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class DatasetImportIntegrationView(IntegrationAPIView):
    """
    Import Dataset folder into management PostgreSQL.
    Used by send_dataset_to_management.py (X-Management-API-Key).
    """

    def post(self, request):
        dataset_root = (request.data.get("dataset_root") or "").strip()
        if not dataset_root:
            return error_response("dataset_root is required", status.HTTP_400_BAD_REQUEST)

        from pathlib import Path

        root = Path(dataset_root)
        if not root.is_dir():
            return error_response(f"dataset_root not found: {root}", status.HTTP_400_BAD_REQUEST)

        shop_id = request.data.get("shop_id")
        branch_id = request.data.get("branch_id")
        if shop_id not in (None, ""):
            try:
                shop_id = int(shop_id)
            except (TypeError, ValueError):
                return error_response("shop_id must be an integer", status.HTTP_400_BAD_REQUEST)
        else:
            shop_id = None
        if branch_id not in (None, ""):
            try:
                branch_id = int(branch_id)
            except (TypeError, ValueError):
                return error_response("branch_id must be an integer", status.HTTP_400_BAD_REQUEST)
        else:
            branch_id = None

        try:
            result = run_dataset_import(
                dataset_root=root,
                shop_id=shop_id,
                branch_id=branch_id,
                skip_products=bool(request.data.get("skip_products")),
                skip_offers=bool(request.data.get("skip_offers")),
                images_only=bool(request.data.get("images_only")),
                clear_offers=bool(request.data.get("clear_offers")),
                random_active=not bool(request.data.get("no_random_active")),
                seed=request.data.get("seed"),
                log=None,
            )
        except (FileNotFoundError, ValueError) as exc:
            return error_response(str(exc), status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"ok": True, "result": result}, status=status.HTTP_200_OK)
