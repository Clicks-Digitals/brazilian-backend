from django.db.models import Q
from rest_framework import generics, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.filters import ProductFilter
from apps.catalog.models import Category, Product, ProductImage
from apps.catalog.serializers import (
    AdminProductSerializer,
    CategorySerializer,
    CategoryWriteSerializer,
    ProductDetailSerializer,
    ProductImageWriteSerializer,
    ProductListSerializer,
)
from apps.catalog.services import (
    admin_product_queryset,
    apply_product_ordering,
    public_category_queryset,
    public_product_queryset,
    set_primary_image,
)
from apps.core.exceptions import APIError
from apps.core.pagination import AdminPagination, DefaultPagination
from apps.core.permissions import HasPermissionCode, IsStaffUser
from apps.core.services import write_audit


class CategoryListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    pagination_class = None

    def get_queryset(self):
        return public_category_queryset()


class CategoryDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    lookup_field = "slug"

    def get_queryset(self):
        return public_category_queryset()


class ProductListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = DefaultPagination
    filterset_class = ProductFilter
    search_fields = ("name", "name_ar", "tasting_notes", "sku", "description", "short_description")

    def get_queryset(self):
        qs = public_product_queryset()
        return apply_product_ordering(qs, self.request.query_params.get("ordering"))


class ProductDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return public_product_queryset()


class SearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        qs = public_product_queryset()
        if query:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(name_ar__icontains=query)
                | Q(tasting_notes__icontains=query)
                | Q(sku__icontains=query)
                | Q(description__icontains=query)
            )
        qs = apply_product_ordering(qs, request.query_params.get("ordering") or "featured")
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = ProductListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class AdminCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategoryWriteSerializer
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    pagination_class = AdminPagination
    queryset = Category.objects.all()
    search_fields = ("name", "name_ar", "slug")
    permission_map = {
        "list": "categories.view",
        "retrieve": "categories.view",
        "create": "categories.create",
        "update": "categories.edit",
        "partial_update": "categories.edit",
        "destroy": "categories.delete",
    }

    def perform_create(self, serializer):
        obj = serializer.save()
        write_audit(self.request, "create", "category", obj.pk, {"slug": obj.slug})

    def perform_update(self, serializer):
        obj = serializer.save()
        write_audit(self.request, "update", "category", obj.pk, {"slug": obj.slug})

    def perform_destroy(self, instance):
        write_audit(self.request, "delete", "category", instance.pk, {"slug": instance.slug})
        instance.delete()


class AdminProductViewSet(viewsets.ModelViewSet):
    serializer_class = AdminProductSerializer
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    pagination_class = AdminPagination
    search_fields = ("name", "name_ar", "sku", "slug")
    filterset_fields = ("category", "is_active", "is_featured", "is_new")
    permission_map = {
        "list": "products.view",
        "retrieve": "products.view",
        "create": "products.create",
        "update": "products.edit",
        "partial_update": "products.edit",
        "destroy": "products.delete",
        "upload_images": "products.edit",
    }

    def get_queryset(self):
        return admin_product_queryset()

    def perform_create(self, serializer):
        obj = serializer.save()
        write_audit(self.request, "create", "product", obj.pk, {"sku": obj.sku})

    def perform_update(self, serializer):
        obj = serializer.save()
        write_audit(self.request, "update", "product", obj.pk, {"sku": obj.sku})

    def perform_destroy(self, instance):
        write_audit(self.request, "delete", "product", instance.pk, {"sku": instance.sku})
        instance.delete()


class AdminProductImageUploadView(APIView):
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    permission_code = "products.edit"

    def post(self, request, pk):
        product = Product.objects.filter(pk=pk).first()
        if not product:
            raise APIError("Product not found.", code="not_found", status=404)
        serializer = ProductImageWriteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        image = serializer.save(product=product)
        set_primary_image(image)
        write_audit(request, "create", "product_image", image.pk, {"product_id": product.pk})
        return Response(
            ProductImageWriteSerializer(image, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AdminProductImageDetailView(APIView):
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    permission_code = "products.edit"

    def patch(self, request, pk):
        image = ProductImage.objects.filter(pk=pk).select_related("product").first()
        if not image:
            raise APIError("Image not found.", code="not_found", status=404)
        serializer = ProductImageWriteSerializer(
            image, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        image = serializer.save()
        set_primary_image(image)
        write_audit(request, "update", "product_image", image.pk)
        return Response(ProductImageWriteSerializer(image, context={"request": request}).data)

    def delete(self, request, pk):
        image = ProductImage.objects.filter(pk=pk).first()
        if not image:
            raise APIError("Image not found.", code="not_found", status=404)
        write_audit(request, "delete", "product_image", image.pk)
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
