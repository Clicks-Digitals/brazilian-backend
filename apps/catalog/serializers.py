from rest_framework import serializers

from apps.catalog.models import Category, Product, ProductImage, ProductVariant
from apps.core.uploads import validate_image_file
from apps.core.utils import absolute_uri, money


class CategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "name_ar",
            "slug",
            "description",
            "image",
            "parent",
            "is_active",
            "show_in_nav",
            "display_order",
            "seo_title",
            "seo_description",
            "product_count",
        )
        read_only_fields = ("id", "product_count")

    def get_image(self, obj):
        return absolute_uri(self.context.get("request"), obj.image)

    def validate_image(self, value):
        if value:
            validate_image_file(value)
        return value


class CategoryWriteSerializer(CategorySerializer):
    image = serializers.ImageField(required=False, allow_null=True)

    def validate_image(self, value):
        if value:
            validate_image_file(value)
        return value

    def to_representation(self, instance):
        return CategorySerializer(instance, context=self.context).data


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ("id", "url", "alt_text", "is_primary", "sort_order")
        read_only_fields = ("id", "url")

    def get_url(self, obj):
        return absolute_uri(self.context.get("request"), obj.image)


class ProductImageWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt_text", "is_primary", "sort_order")

    def validate_image(self, value):
        validate_image_file(value)
        return value

    def to_representation(self, instance):
        return ProductImageSerializer(instance, context=self.context).data


class VariantSerializer(serializers.ModelSerializer):
    in_stock = serializers.BooleanField(read_only=True)
    image = serializers.SerializerMethodField()
    price = serializers.DecimalField(max_digits=10, decimal_places=3, coerce_to_string=True)
    compare_at_price = serializers.DecimalField(
        max_digits=10, decimal_places=3, coerce_to_string=True, allow_null=True
    )
    on_sale = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "name",
            "sku",
            "price",
            "compare_at_price",
            "stock_quantity",
            "weight_label",
            "image",
            "is_active",
            "in_stock",
            "on_sale",
        )

    def get_image(self, obj):
        return absolute_uri(self.context.get("request"), obj.image)

    def get_on_sale(self, obj):
        return bool(obj.compare_at_price and obj.compare_at_price > obj.price)


class VariantWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "name",
            "sku",
            "price",
            "compare_at_price",
            "stock_quantity",
            "weight_label",
            "image",
            "is_active",
        )

    def validate_image(self, value):
        if value:
            validate_image_file(value)
        return value


class ProductListSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    compare_at_price = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    on_sale = serializers.SerializerMethodField()
    default_variant_id = serializers.SerializerMethodField()
    default_variant = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "slug",
            "sku",
            "name",
            "name_ar",
            "short_description",
            "tasting_notes",
            "roast_level",
            "origin",
            "is_featured",
            "is_new",
            "is_promotional",
            "is_active",
            "category",
            "primary_image",
            "price",
            "compare_at_price",
            "in_stock",
            "on_sale",
            "default_variant_id",
            "default_variant",
        )

    def _default_variant(self, obj):
        variants = list(obj.variants.all())
        active = [v for v in variants if v.is_active]
        return (active or variants or [None])[0]

    def get_category(self, obj):
        return {"id": obj.category_id, "slug": obj.category.slug, "name": obj.category.name}

    def get_primary_image(self, obj):
        images = list(obj.images.all())
        primary = next((img for img in images if img.is_primary), None) or (images[0] if images else None)
        return absolute_uri(self.context.get("request"), primary.image) if primary else None

    def get_price(self, obj):
        variant = self._default_variant(obj)
        return str(money(variant.price)) if variant else None

    def get_compare_at_price(self, obj):
        variant = self._default_variant(obj)
        if variant and variant.compare_at_price is not None:
            return str(money(variant.compare_at_price))
        return None

    def get_in_stock(self, obj):
        return any(v.in_stock for v in obj.variants.all())

    def get_on_sale(self, obj):
        return any(v.compare_at_price and v.compare_at_price > v.price for v in obj.variants.all())

    def get_default_variant_id(self, obj):
        variant = self._default_variant(obj)
        return variant.id if variant else None

    def get_default_variant(self, obj):
        variant = self._default_variant(obj)
        if not variant:
            return None
        return VariantSerializer(variant, context=self.context).data


class ProductDetailSerializer(ProductListSerializer):
    variants = VariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    related_products = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + (
            "description",
            "allow_backorder",
            "seo_title",
            "seo_description",
            "variants",
            "images",
            "related_products",
        )

    def get_related_products(self, obj):
        from apps.catalog.services import related_products_for

        return ProductListSerializer(
            related_products_for(obj),
            many=True,
            context=self.context,
        ).data


class AdminProductSerializer(serializers.ModelSerializer):
    variants = VariantWriteSerializer(many=True, required=False)
    images = ProductImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "category",
            "category_name",
            "name",
            "name_ar",
            "slug",
            "sku",
            "short_description",
            "description",
            "tasting_notes",
            "roast_level",
            "origin",
            "is_active",
            "is_featured",
            "is_new",
            "is_promotional",
            "allow_backorder",
            "seo_title",
            "seo_description",
            "published_at",
            "variants",
            "images",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "images")

    def create(self, validated_data):
        variants = validated_data.pop("variants", [])
        product = Product.objects.create(**validated_data)
        for item in variants:
            item = {k: v for k, v in item.items() if k != "id"}
            ProductVariant.objects.create(product=product, **item)
        return product

    def update(self, instance, validated_data):
        variants = validated_data.pop("variants", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if variants is not None:
            keep_ids = []
            for item in variants:
                variant_id = item.get("id")
                if variant_id:
                    variant = instance.variants.filter(pk=variant_id).first()
                    if variant:
                        for attr, value in item.items():
                            if attr != "id":
                                setattr(variant, attr, value)
                        variant.save()
                        keep_ids.append(variant.pk)
                else:
                    created = ProductVariant.objects.create(product=instance, **item)
                    keep_ids.append(created.pk)
            instance.variants.exclude(pk__in=keep_ids).delete()
        return instance
