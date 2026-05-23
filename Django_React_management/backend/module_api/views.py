from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth import get_user_model
from django.db.models import Q

from module_shop.models import Shop, Branch
from module_product.models import Category, Product
from .permissions import (
    get_accessible_shops,
    user_can_manage_shop,
    get_accessible_branch_ids_for_shop,
    get_accessible_branches,
    filter_categories_by_branch_access,
    filter_products_by_branch_access,
    user_can_manage_branch,
    user_is_shop_branches_admin,
    user_can_view_branch_permissions,
    user_is_shop_manager,
    user_can_edit_product,
    user_can_toggle_product_offerable,
    validate_exclusive_branch_assignments,
    user_belongs_to_shop_for_branch_permissions,
)
from module_account.role_helpers import (
    ensure_branch_manager,
    ensure_shop_manager,
    get_branch_manager,
    promote_to_shop_manager,
)
from module_account.models import User as AccountUser
from .persian_errors import extract_error_message, error_response
from .serializers import (
    ShopSerializer,
    ShopCreateSerializer,
    BranchSerializer,
    BranchCreateSerializer,
    BranchWithShopSerializer,
    CategorySerializer,
    ProductSerializer,
    ProductCreateSerializer,
    ProductUpdateSerializer,
    ProductOfferableSerializer,
    ShopKeeperCreateSerializer,
    RegisterSerializer,
    ProfileSerializer,
    ChangePasswordSerializer,
    ShopUserBranchPermissionSerializer,
)

User = get_user_model()


class CheckShopManagerView(APIView):
    """Whether the current user has shop/branch access; flags for login redirect and UI."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        shops = get_accessible_shops(user)
        has_shop = shops.exists()
        manages_shop = Shop.objects.filter(manager=user).exists()
        shop_rows = [
            {
                "id": s.id,
                "name": s.name,
                "is_shop_manager": s.manager_id == user.id,
                "is_owner": s.manager_id == user.id,
            }
            for s in shops
        ]
        default_products_shop_id = None
        if has_shop and not manages_shop:
            default_products_shop_id = shops.order_by("name").values_list("id", flat=True).first()
        return Response(
            {
                "has_shop": has_shop,
                "owns_shop": manages_shop,
                "manages_shop": manages_shop,
                "shop_count": shops.count(),
                "shops": shop_rows if has_shop else [],
                "default_products_shop_id": default_products_shop_id,
                "role": user.role,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
            }
        )


# Backward-compatible alias for older API clients.
CheckShopOwnerView = CheckShopManagerView


class ShopListView(APIView):
    """List shops the user can manage: owned + assigned (if has can_manage_assigned_shops)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        shops = get_accessible_shops(request.user)
        serializer = ShopSerializer(shops, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        """
        Create a new shop for the current user when they do not already manage any shop.
        """
        user = request.user
        if not user.can_create_shop:
            return error_response("You are not allowed to create a shop.", status.HTTP_403_FORBIDDEN)
        if get_accessible_shops(user).exists():
            return error_response("You already manage at least one shop.", status.HTTP_403_FORBIDDEN)
        serializer = ShopCreateSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(
                {"error": extract_error_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        shop = serializer.save()
        return Response(ShopSerializer(shop).data, status=status.HTTP_201_CREATED)


class BranchListView(APIView):
    """List branches of a shop that the user can manage. Query param: shop (id)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        shop_id = request.query_params.get("shop")
        if not shop_id:
            return error_response("Query param 'shop' (shop id) is required", status.HTTP_400_BAD_REQUEST)
        try:
            shop = Shop.objects.get(pk=shop_id)
        except Shop.DoesNotExist:
            return error_response("Shop not found", status.HTTP_404_NOT_FOUND)
        if not user_can_manage_shop(request.user, shop):
            return error_response("Shop not found", status.HTTP_404_NOT_FOUND)
        branch_ids = get_accessible_branch_ids_for_shop(request.user, shop_id)
        branches = Branch.objects.filter(id__in=branch_ids).order_by("name")
        serializer = BranchSerializer(branches, many=True)
        total_in_shop = Branch.objects.filter(shop_id=shop_id, is_active=True).count()
        can_create_branches = shop.manager_id == request.user.id
        return Response(
            {
                "branches": serializer.data,
                "total_branches_in_shop": total_in_shop,
                "can_create_branches": can_create_branches,
            }
        )

    def post(self, request):
        serializer = BranchCreateSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(
                {"error": extract_error_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        shop = serializer.validated_data["shop"]
        if shop.manager_id != request.user.id:
            return error_response("Only the shop manager can create branches.", status.HTTP_403_FORBIDDEN)
        if not user_can_manage_shop(request.user, shop):
            return error_response("You cannot add branches to this shop.", status.HTTP_403_FORBIDDEN)
        branch = serializer.save(is_active=True)
        return Response(
            BranchSerializer(branch).data,
            status=status.HTTP_201_CREATED,
        )


class CategoryListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        shop_id = request.query_params.get("shop")
        if not shop_id:
            return error_response("Query param 'shop' (shop id) is required", status.HTTP_400_BAD_REQUEST)
        try:
            shop = Shop.objects.get(pk=shop_id)
        except Shop.DoesNotExist:
            return error_response("Shop not found", status.HTTP_404_NOT_FOUND)
        if not user_can_manage_shop(request.user, shop):
            return error_response("Shop not found", status.HTTP_404_NOT_FOUND)
        categories = Category.objects.filter(shop_id=shop_id).order_by("sort_order", "title")
        categories = filter_categories_by_branch_access(request.user, shop_id, categories)
        serializer = CategorySerializer(categories, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(
                {"error": extract_error_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        shop = serializer.validated_data.get("shop")
        if not user_can_manage_shop(request.user, shop):
            return error_response("Shop not found", status.HTTP_404_NOT_FOUND)
        if not user_is_shop_manager(request.user, shop):
            return error_response("Only the shop manager can create categories.", status.HTTP_403_FORBIDDEN)
        branch = serializer.validated_data.get("branch")
        if branch and not user_can_manage_branch(request.user, branch):
            return error_response("You cannot create categories for this branch.", status.HTTP_403_FORBIDDEN)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProductListCreateView(APIView):
    """
    List/create products. Products are scoped by shop and optionally by branch.
    - No branch param ("All branches"): show all products in the shop (shop-level + every branch).
    - Branch param: show only products that belong to that branch (strict per-branch).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        shop_id = request.query_params.get("shop")
        if not shop_id:
            return error_response("Query param 'shop' (shop id) is required", status.HTTP_400_BAD_REQUEST)
        try:
            shop = Shop.objects.get(pk=shop_id)
        except Shop.DoesNotExist:
            return error_response("Shop not found", status.HTTP_404_NOT_FOUND)
        if not user_can_manage_shop(request.user, shop):
            return error_response("Shop not found", status.HTTP_404_NOT_FOUND)

        products = (
            Product.objects.filter(shop_id=shop_id)
            .select_related("category", "branch")
            .order_by("branch__name", "title")
        )
        branch_id_param = request.query_params.get("branch")

        if branch_id_param:
            # Single branch: show only products that belong to this branch (no shop-level)
            try:
                branch_pk = int(branch_id_param)
            except (TypeError, ValueError):
                return error_response("Invalid branch", status.HTTP_400_BAD_REQUEST)
            branch_ids = get_accessible_branch_ids_for_shop(request.user, shop_id)
            if branch_pk not in branch_ids:
                return error_response("Branch not found", status.HTTP_404_NOT_FOUND)
            products = products.filter(branch_id=branch_pk)
        else:
            # All branches: show all products in the shop (shop-level + every branch user can access)
            products = filter_products_by_branch_access(request.user, shop_id, products)

        serializer = ProductSerializer(products, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        serializer = ProductCreateSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(
                {"error": extract_error_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        shop = serializer.validated_data.get("shop")
        if not user_can_manage_shop(request.user, shop):
            return error_response("You cannot add products to this shop.", status.HTTP_403_FORBIDDEN)
        if not user_can_edit_product(request.user, shop):
            return error_response("Only the shop manager can create products.", status.HTTP_403_FORBIDDEN)
        branch = serializer.validated_data.get("branch")
        if branch and not user_can_manage_branch(request.user, branch):
            return error_response("You cannot add products to this branch.", status.HTTP_403_FORBIDDEN)
        serializer.save()
        return Response(
            ProductSerializer(serializer.instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ProductDetailView(APIView):
    """
    Retrieve / update / delete a single product.

    This is the "product detail" page/backend:
    - GET: show all information about the product (including shop/branch/category names).
    - PATCH/PUT: edit the product.
    - DELETE: remove the product.
    Only users who can manage the product's branch (or all branches of that shop) are allowed.
    """

    permission_classes = [IsAuthenticated]

    def _get_product(self, pk):
        try:
            return (
                Product.objects.select_related("shop", "branch", "category")
                .get(pk=pk)
            )
        except Product.DoesNotExist:
            return None

    def _check_permissions(self, request, product):
        if product is None:
            return error_response("Product not found", status.HTTP_404_NOT_FOUND)
        if not user_can_manage_shop(request.user, product.shop):
            return error_response("Product not found", status.HTTP_404_NOT_FOUND)
        # Legacy products might not have a branch set (older data). In that case,
        # treat them as shop-level products and only check shop permissions.
        if product.branch is not None and not user_can_manage_branch(request.user, product.branch):
            return error_response("Product not found", status.HTTP_404_NOT_FOUND)
        return None

    def get(self, request, pk):
        product = self._get_product(pk)
        perm_error = self._check_permissions(request, product)
        if perm_error:
            return perm_error
        serializer = ProductSerializer(product, context={"request": request})
        return Response(serializer.data)

    def patch(self, request, pk):
        product = self._get_product(pk)
        perm_error = self._check_permissions(request, product)
        if perm_error:
            return perm_error
        if user_can_edit_product(request.user, product.shop):
            serializer = ProductUpdateSerializer(
                product, data=request.data, partial=True, context={"request": request}
            )
        elif user_can_toggle_product_offerable(request.user, product):
            allowed = {"is_offerable"}
            extra = {k for k in request.data.keys() if k not in allowed}
            if extra:
                return error_response(
                    "Branch managers may only change whether a product is offerable.",
                    status.HTTP_403_FORBIDDEN,
                )
            serializer = ProductOfferableSerializer(
                product, data=request.data, partial=True, context={"request": request}
            )
        else:
            return error_response("You cannot edit this product.", status.HTTP_403_FORBIDDEN)
        if not serializer.is_valid():
            return Response(
                {"error": extract_error_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(
            ProductSerializer(serializer.instance, context={"request": request}).data
        )

    def put(self, request, pk):
        product = self._get_product(pk)
        perm_error = self._check_permissions(request, product)
        if perm_error:
            return perm_error
        if not user_can_edit_product(request.user, product.shop):
            return error_response("Only the shop manager can edit products.", status.HTTP_403_FORBIDDEN)
        serializer = ProductUpdateSerializer(
            product, data=request.data, partial=False, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                {"error": extract_error_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(
            ProductSerializer(serializer.instance, context={"request": request}).data
        )

    def delete(self, request, pk):
        product = self._get_product(pk)
        perm_error = self._check_permissions(request, product)
        if perm_error:
            return perm_error
        if not user_is_shop_manager(request.user, product.shop):
            return error_response("Only the shop manager can delete products.", status.HTTP_403_FORBIDDEN)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ShopKeeperCreateView(APIView):
    """
    Create a branch manager (UI: "New shop keeper"). Shop managers or Django staff only.
    Branch managers cannot create their own shop; the shop manager assigns branches later.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not (user.is_staff or Shop.objects.filter(manager=user).exists()):
            return error_response(
                "Only shop managers or staff can create branch manager accounts.",
                status.HTTP_403_FORBIDDEN,
            )
        serializer = ShopKeeperCreateSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(
                {"error": extract_error_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = serializer.save()
        return Response(
            {"id": user.id, "username": user.username, "phone_number": user.phone_number},
            status=status.HTTP_201_CREATED,
        )


class RegisterView(APIView):
    """Public registration: creates a shop manager who may create their own shop."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": extract_error_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = serializer.save()
        return Response(
            {"id": user.id, "username": user.username, "phone_number": user.phone_number},
            status=status.HTTP_201_CREATED,
        )


class ProfileView(APIView):
    """Get or update current user profile (JSON or multipart for profile photo)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def _response_with_branches(self, user, request):
        serializer = ProfileSerializer(user, context={"request": request})
        data = dict(serializer.data)
        branches = get_accessible_branches(user)
        data["branches"] = BranchWithShopSerializer(branches, many=True).data
        return Response(data)

    def get(self, request):
        return self._response_with_branches(request.user, request)

    def patch(self, request):
        serializer = ProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        if not serializer.is_valid():
            return Response(
                {"error": extract_error_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return self._response_with_branches(serializer.instance, request)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        if not serializer.is_valid():
            return Response(
                {"error": extract_error_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response({"detail": "رمز عبور به‌روزرسانی شد."})


class ShopBranchPermissionView(APIView):
    """
    Per-shop branch permission admin.

    Shop manager: view and change who manages which branches.
    Other roles: read-only view (branch staff see only themselves in the user list).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        shop_id = request.query_params.get("shop")
        if not shop_id:
            return error_response("Query param 'shop' (shop id) is required", status.HTTP_400_BAD_REQUEST)
        try:
            shop = Shop.objects.get(pk=shop_id)
        except Shop.DoesNotExist:
            return error_response("Shop not found", status.HTTP_404_NOT_FOUND)

        if not user_can_view_branch_permissions(request.user, shop):
            return error_response("Shop not found", status.HTTP_404_NOT_FOUND)

        can_edit = user_is_shop_branches_admin(request.user, shop)

        other_shop_manager_ids = Shop.objects.exclude(pk=shop.pk).values_list(
            "manager_id", flat=True
        )
        # Users tied to this shop: manager, staff, branch managers, and assignable shop managers.
        users = (
            User.objects.filter(
                Q(pk=shop.manager_id)
                | Q(managed_shops=shop)
                | Q(branchmanager__managed_shops_all_branches=shop)
                | Q(branchmanager__allowed_branches__shop=shop)
                | Q(branchmanager__created_for_shop=shop)
                | (
                    Q(role=AccountUser.Role.SHOP_MANAGER)
                    & ~Q(pk__in=other_shop_manager_ids)
                )
            )
            .distinct()
            .order_by("username")
        )
        if not can_edit:
            users = users.filter(pk=request.user.pk)
        serializer = ShopUserBranchPermissionSerializer(
            users, many=True, context={"shop": shop}
        )
        # Also include all branches of this shop for convenience.
        branches = BranchSerializer(
            Branch.objects.filter(shop=shop, is_active=True).order_by("name"),
            many=True,
        ).data
        return Response(
            {
                "shop": ShopSerializer(shop).data,
                "branches": branches,
                "users": serializer.data,
                "can_edit_branch_permissions": can_edit,
            }
        )

    def patch(self, request):
        """
        Update branch permissions for a single user in a shop.

        Payload example:
        {
          "shop": 1,
          "user_id": 5,
          "assign_as_shop_manager": false,
          "is_head_manager": true,
          "branch_ids": [2, 3, 4]
        }
        """
        data = request.data or {}
        shop_id = data.get("shop")
        user_id = data.get("user_id")
        assign_as_shop_manager = bool(data.get("assign_as_shop_manager", False))
        is_head_manager = bool(data.get("is_head_manager", False))
        branch_ids = data.get("branch_ids", [])

        if not shop_id or not user_id:
            return error_response("Fields 'shop' and 'user_id' are required.", status.HTTP_400_BAD_REQUEST)

        try:
            shop = Shop.objects.get(pk=shop_id)
        except Shop.DoesNotExist:
            return error_response("Shop not found", status.HTTP_404_NOT_FOUND)

        if not user_is_shop_branches_admin(request.user, shop):
            return error_response("Shop not found", status.HTTP_404_NOT_FOUND)

        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return error_response("User not found", status.HTTP_404_NOT_FOUND)

        if assign_as_shop_manager:
            if target_user.pk == shop.manager_id:
                serializer = ShopUserBranchPermissionSerializer(
                    target_user, context={"shop": shop}
                )
                return Response(serializer.data)

            if target_user.role == AccountUser.Role.BRANCH_MANAGER:
                promoted = promote_to_shop_manager(target_user)
                if promoted is None:
                    return error_response(
                        "This account could not be promoted to shop manager. "
                        "Use branch permissions for branch staff, or register a new shop manager account.",
                        status.HTTP_400_BAD_REQUEST,
                    )
                target_user = promoted
            elif target_user.role != AccountUser.Role.SHOP_MANAGER:
                return error_response(
                    "Only shop manager or branch manager accounts can own a shop. "
                    "End-user accounts cannot be assigned as shop manager.",
                    status.HTTP_400_BAD_REQUEST,
                )

            if ensure_shop_manager(target_user) is None:
                return error_response(
                    "This account does not have a valid shop manager profile. "
                    "Ask them to register as a shop manager.",
                    status.HTTP_400_BAD_REQUEST,
                )
            if Shop.objects.filter(manager=target_user).exclude(pk=shop.pk).exists():
                return error_response(
                    "This user already manages another shop. "
                    "They cannot be assigned as manager of this shop.",
                    status.HTTP_400_BAD_REQUEST,
                )

            shop.manager = target_user
            shop.save(update_fields=["manager"])
            serializer = ShopUserBranchPermissionSerializer(
                target_user, context={"shop": shop}
            )
            return Response(serializer.data)

        target_bm = ensure_branch_manager(target_user)
        belongs, target_bm = user_belongs_to_shop_for_branch_permissions(
            shop, target_user, target_bm
        )
        if not belongs:
            if target_user.role == AccountUser.Role.SHOP_MANAGER:
                return error_response(
                    "برای این کاربر از گزینه «واگذاری مدیریت فروشگاه» استفاده کنید، نه مدیر ارشد شعب.",
                    status.HTTP_400_BAD_REQUEST,
                )
            return error_response(
                "این کاربر به این فروشگاه مرتبط نیست. ابتدا او را به‌عنوان فروشنده (مدیر شعبه) "
                "برای این فروشگاه ایجاد کنید.",
                status.HTTP_400_BAD_REQUEST,
            )

        if shop.manager_id == target_user.pk:
            return error_response(
                "You are the shop manager (owner). Branch permissions apply to branch manager accounts. "
                "To give someone else ownership, select a shop manager account and enable «Assign as shop manager».",
                status.HTTP_400_BAD_REQUEST,
            )

        if target_bm is None:
            return error_response(
                "Branch permissions apply only to branch manager accounts. "
                "To make this user the shop owner, they must register with the shop manager role "
                "and you must enable «Assign as shop manager».",
                status.HTTP_400_BAD_REQUEST,
            )

        if target_bm.created_for_shop_id is None:
            target_bm.created_for_shop = shop
            target_bm.save(update_fields=["created_for_shop_id"])

        if is_head_manager:
            target_bm.managed_shops_all_branches.add(shop)
        else:
            target_bm.managed_shops_all_branches.remove(shop)

        valid_branch_ids = set(
            Branch.objects.filter(shop=shop, id__in=branch_ids).values_list("id", flat=True)
        )

        if not is_head_manager:
            conflict_msg = validate_exclusive_branch_assignments(
                shop, target_bm, valid_branch_ids
            )
            if conflict_msg:
                return error_response(conflict_msg, status.HTTP_400_BAD_REQUEST)

        target_bm.allowed_branches.remove(
            *target_bm.allowed_branches.filter(shop=shop)
        )
        if valid_branch_ids:
            target_bm.allowed_branches.add(
                *Branch.objects.filter(id__in=valid_branch_ids)
            )

        target_bm.save()

        serializer = ShopUserBranchPermissionSerializer(
            target_user, context={"shop": shop}
        )
        return Response(serializer.data)

