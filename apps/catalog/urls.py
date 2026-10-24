from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.catalog.views import (
    AdminCategoryViewSet,
    AdminProductImageDetailView,
    AdminProductImageUploadView,
    AdminProductViewSet,
    CategoryDetailView,
    CategoryListView,
    ProductDetailView,
    ProductListView,
    SearchView,
)

router = DefaultRouter()
router.register("admin/products", AdminProductViewSet, basename="admin-products")
router.register("admin/categories", AdminCategoryViewSet, basename="admin-categories")

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("categories/<slug:slug>/", CategoryDetailView.as_view(), name="category-detail"),
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
    path("search/", SearchView.as_view(), name="search"),
    path(
        "admin/products/<int:pk>/images/",
        AdminProductImageUploadView.as_view(),
        name="admin-product-images",
    ),
    path(
        "admin/product-images/<int:pk>/",
        AdminProductImageDetailView.as_view(),
        name="admin-product-image-detail",
    ),
    path("", include(router.urls)),
]
