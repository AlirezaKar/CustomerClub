from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views
from .integration_views import (
    CustomerOffersIntegrationView,
    DatasetImportIntegrationView,
    EndUserCardIntegrationView,
    EndUserIntegrationView,
    ShopCatalogIntegrationView,
    ShopsIntegrationView,
    SpecialOfferRedeemIntegrationView,
    SpecialOfferTransactionIntegrationView,
)

urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("shops/", views.ShopListView.as_view(), name="shop-list"),
    path("branches/", views.BranchListView.as_view(), name="branch-list"),
    path("categories/", views.CategoryListCreateView.as_view(), name="category-list-create"),
    path("products/", views.ProductListCreateView.as_view(), name="product-list-create"),
    path("products/<int:pk>/", views.ProductDetailView.as_view(), name="product-detail"),
    path("shop-keepers/", views.ShopKeeperCreateView.as_view(), name="shop-keeper-create"),
    path("me/", views.ProfileView.as_view(), name="profile"),
    path("me/change-password/", views.ChangePasswordView.as_view(), name="change-password"),
    path("shop-branch-permissions/", views.ShopBranchPermissionView.as_view(), name="shop-branch-permissions"),
    path("check-shop-manager/", views.CheckShopManagerView.as_view(), name="check-shop-manager"),
    path("check-shop-owner/", views.CheckShopOwnerView.as_view(), name="check-shop-owner"),
    path(
        "integration/shops/",
        ShopsIntegrationView.as_view(),
        name="integration-shops",
    ),
    path(
        "integration/customer-offers/",
        CustomerOffersIntegrationView.as_view(),
        name="integration-customer-offers",
    ),
    path(
        "integration/end-users/",
        EndUserIntegrationView.as_view(),
        name="integration-end-users",
    ),
    path(
        "integration/special-offer-transactions/",
        SpecialOfferTransactionIntegrationView.as_view(),
        name="integration-special-offer-transactions",
    ),
    path(
        "integration/catalog/",
        ShopCatalogIntegrationView.as_view(),
        name="integration-catalog",
    ),
    path(
        "integration/redeem-special-offer/",
        SpecialOfferRedeemIntegrationView.as_view(),
        name="integration-redeem-special-offer",
    ),
    path(
        "integration/end-users/card/",
        EndUserCardIntegrationView.as_view(),
        name="integration-end-user-card",
    ),
    path(
        "integration/dataset-import/",
        DatasetImportIntegrationView.as_view(),
        name="integration-dataset-import",
    ),
]