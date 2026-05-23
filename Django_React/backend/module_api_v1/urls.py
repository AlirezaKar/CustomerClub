from django.conf import settings
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views


urlpatterns= [
    path("jwt/token/", TokenObtainPairView.as_view(), name="jwt_token"),
    path("jwt/token/refresh/", TokenRefreshView.as_view(), name="jwt_token_refresh"),

    # path("user/", views.UserView.as_view(), name= "module_account_user"),
    # path("user/<str:phone_number>/", views.UserDetailView.as_view(), name= "module_account_user_detail"),
    # path("user/", views.UserView.as_view(), name= "module_account_user"),
    path("public/shops/", views.PublicShopsView.as_view(), name="public_shops"),
    path("user/signup/", views.UserSignup.as_view(), name= "module_account_user_signup"),
    path("user/login/", views.UserLogin.as_view(), name= "module_account_user_login"),
    path("user/nfc/register/", views.NfcRegisterView.as_view(), name="user_nfc_register"),
    path("user/nfc/login/", views.NfcAuthLoginView.as_view(), name="user_nfc_login"),
    path("user/nfc/unlink/", views.NfcUnlinkView.as_view(), name="user_nfc_unlink"),
    path("user/nfc/status/", views.NfcStatusView.as_view(), name="user_nfc_status"),
    path("nfc-login/", views.NfcLoginView.as_view(), name= "nfc_login"),
    path("nfc-complete/", views.NfcCompleteView.as_view(), name= "nfc_complete"),
    path("user/submit-offer/", views.UserSubmitOffer.as_view(), name= "module_account_user_submit_offer"),
    path("update-user-properties/", views.UpdateUserProperties.as_view(), name= "module_account_update_user_properties"),
    path("shops/", views.Shops.as_view(), name= "module_shop_shops"),
    path("shop/settings/", views.ShopSettings.as_view(), name= "module_shop_shop_settings"),
    path("shop/settings/score/", views.ShopSettingsScore.as_view(), name= "module_shop_shop_settings_score"),
    path("shop/settings/products/", views.ShopSettingsProducts.as_view(), name= "module_shop_shop_settings_products"),
    path("shop/settings/products/<int:product_id>/", views.ShopSettingsProductDetail.as_view(), name= "module_shop_shop_settings_product_detail"),
    path("shop/settings/categories/", views.ShopCategories.as_view(), name= "module_shop_shop_settings_categories"),
    path("shop/settings/categories/<int:category_id>/", views.ShopCategoryDetail.as_view(), name= "module_shop_shop_settings_category_detail"),

    path("add-items-test/", views.AddItemsTest.as_view(), name= "add_items_test"),
]

if getattr(settings, "ENABLE_OPENAPI", False):
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

    urlpatterns += [
        path("schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "schema/swagger/",
            SpectacularSwaggerView.as_view(url_name="module_api_v1:schema"),
            name="swagger",
        ),
    ]
