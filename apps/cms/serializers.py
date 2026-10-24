from django.utils import timezone
from rest_framework import serializers

from apps.catalog.serializers import ProductListSerializer
from apps.cms.models import (
    Announcement,
    Article,
    ArticleCategory,
    Banner,
    ContactMessage,
    LegalPage,
    NewsletterSubscriber,
)
from apps.cms.services import sanitize_html, settings_payload
from apps.core.uploads import validate_image_file
from apps.core.utils import absolute_uri


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = (
            "id",
            "text",
            "link_url",
            "is_active",
            "dismissible",
            "starts_at",
            "ends_at",
            "display_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class BannerSerializer(serializers.ModelSerializer):
    desktop_image = serializers.SerializerMethodField()
    mobile_image = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = (
            "id",
            "title",
            "subtitle",
            "cta_label",
            "cta_url",
            "secondary_cta_label",
            "secondary_cta_url",
            "desktop_image",
            "mobile_image",
            "alignment",
            "placement",
            "is_active",
            "display_order",
            "starts_at",
            "ends_at",
        )
        read_only_fields = ("id",)

    def get_desktop_image(self, obj):
        return absolute_uri(self.context.get("request"), obj.desktop_image)

    def get_mobile_image(self, obj):
        return absolute_uri(self.context.get("request"), obj.mobile_image) if obj.mobile_image else None


class BannerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = (
            "id",
            "title",
            "subtitle",
            "cta_label",
            "cta_url",
            "secondary_cta_label",
            "secondary_cta_url",
            "desktop_image",
            "mobile_image",
            "alignment",
            "placement",
            "is_active",
            "display_order",
            "starts_at",
            "ends_at",
        )

    def validate_desktop_image(self, value):
        if value:
            validate_image_file(value)
        return value

    def validate_mobile_image(self, value):
        if value:
            validate_image_file(value)
        return value

    def to_representation(self, instance):
        return BannerSerializer(instance, context=self.context).data


class ArticleCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleCategory
        fields = ("id", "name", "slug", "description")


class ArticleListSerializer(serializers.ModelSerializer):
    cover_image = serializers.SerializerMethodField()
    category = ArticleCategorySerializer(read_only=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "slug",
            "excerpt",
            "cover_image",
            "category",
            "author_name",
            "status",
            "is_featured",
            "published_at",
        )

    def get_cover_image(self, obj):
        return absolute_uri(self.context.get("request"), obj.cover_image)

    def get_author_name(self, obj):
        return obj.author.full_name if obj.author_id else None


class ArticleDetailSerializer(ArticleListSerializer):
    content = serializers.SerializerMethodField()
    og_image = serializers.SerializerMethodField()
    related_products = serializers.SerializerMethodField()

    class Meta(ArticleListSerializer.Meta):
        fields = ArticleListSerializer.Meta.fields + (
            "content",
            "seo_title",
            "seo_description",
            "og_image",
            "related_products",
        )

    def get_content(self, obj):
        return sanitize_html(obj.content)

    def get_og_image(self, obj):
        return absolute_uri(self.context.get("request"), obj.og_image)

    def get_related_products(self, obj):
        from apps.cms.services import article_related_products

        return ProductListSerializer(
            article_related_products(obj),
            many=True,
            context=self.context,
        ).data


class ArticleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "slug",
            "excerpt",
            "content",
            "cover_image",
            "category",
            "author",
            "status",
            "is_featured",
            "published_at",
            "related_products",
            "related_articles",
            "seo_title",
            "seo_description",
            "og_image",
        )

    def validate_cover_image(self, value):
        if value:
            validate_image_file(value)
        return value

    def validate_og_image(self, value):
        if value:
            validate_image_file(value)
        return value

    def validate_content(self, value):
        return sanitize_html(value)

    def create(self, validated_data):
        related_products = validated_data.pop("related_products", [])
        related_articles = validated_data.pop("related_articles", [])
        if validated_data.get("status") == Article.Status.PUBLISHED and not validated_data.get(
            "published_at"
        ):
            validated_data["published_at"] = timezone.now()
        article = Article.objects.create(**validated_data)
        article.related_products.set(related_products)
        article.related_articles.set(related_articles)
        return article

    def update(self, instance, validated_data):
        related_products = validated_data.pop("related_products", None)
        related_articles = validated_data.pop("related_articles", None)
        if (
            validated_data.get("status") == Article.Status.PUBLISHED
            and not instance.published_at
            and not validated_data.get("published_at")
        ):
            validated_data["published_at"] = timezone.now()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if related_products is not None:
            instance.related_products.set(related_products)
        if related_articles is not None:
            instance.related_articles.set(related_articles)
        return instance

    def to_representation(self, instance):
        return ArticleDetailSerializer(instance, context=self.context).data


class LegalPageSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()

    class Meta:
        model = LegalPage
        fields = ("slug", "title", "content", "updated_at")

    def get_content(self, obj):
        return sanitize_html(obj.content)


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ("name", "email", "phone", "message")

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if len(name) < 2:
            raise serializers.ValidationError("Please enter your name.")
        return name

    def validate_message(self, value: str) -> str:
        body = value.strip()
        if len(body) < 4:
            raise serializers.ValidationError("Please write a short message.")
        return body


class NewsletterSerializer(serializers.Serializer):
    email = serializers.EmailField()


class NewsletterAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = ("id", "email", "is_active", "source", "consented_at")
        read_only_fields = ("id", "consented_at")


class StoreSettingsSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return settings_payload(self.context.get("request"))
