from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cms.models import Announcement, Article, Banner, LegalPage, NewsletterSubscriber
from apps.cms.serializers import (
    AnnouncementSerializer,
    ArticleDetailSerializer,
    ArticleListSerializer,
    ArticleWriteSerializer,
    BannerSerializer,
    BannerWriteSerializer,
    ContactMessageSerializer,
    LegalPageSerializer,
    NewsletterAdminSerializer,
    NewsletterSerializer,
)
from apps.cms.services import (
    get_store_settings,
    published_articles,
    public_announcements,
    public_banners,
    storefront_payload,
    update_store_settings,
)
from apps.core.exceptions import APIError
from apps.core.pagination import AdminPagination, DefaultPagination
from apps.core.permissions import HasPermissionCode, IsStaffUser
from apps.core.services import write_audit
from apps.core.throttles import NewsletterThrottle


class StorefrontView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(storefront_payload(request))


class BannerListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = None

    def get(self, request):
        placement = request.query_params.get("placement")
        qs = public_banners(placement)
        return Response(BannerSerializer(qs, many=True, context={"request": request}).data)


class AnnouncementListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            AnnouncementSerializer(public_announcements(), many=True, context={"request": request}).data
        )


class ArticleListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = published_articles()
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = ArticleListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class ArticleDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        article = published_articles().filter(slug=slug).first()
        if not article:
            raise APIError("Article not found.", code="not_found", status=404)
        return Response(ArticleDetailSerializer(article, context={"request": request}).data)


class LegalPageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        page = LegalPage.objects.filter(slug=slug, is_published=True).first()
        if not page:
            raise APIError("Page not found.", code="not_found", status=404)
        return Response(LegalPageSerializer(page, context={"request": request}).data)


class PublicSettingsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from apps.cms.services import settings_payload

        return Response(settings_payload(request))


class ContactView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [NewsletterThrottle]

    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Message received."}, status=status.HTTP_201_CREATED)


class NewsletterSubscribeView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [NewsletterThrottle]

    def post(self, request):
        serializer = NewsletterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        NewsletterSubscriber.objects.update_or_create(
            email=email, defaults={"is_active": True, "source": "storefront"}
        )
        return Response({"detail": "Subscribed."}, status=status.HTTP_201_CREATED)


class AdminBannerViewSet(viewsets.ModelViewSet):
    serializer_class = BannerWriteSerializer
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    pagination_class = AdminPagination
    queryset = Banner.objects.all()
    permission_map = {
        "list": "banners.view",
        "retrieve": "banners.view",
        "create": "banners.create",
        "update": "banners.edit",
        "partial_update": "banners.edit",
        "destroy": "banners.delete",
    }

    def perform_create(self, serializer):
        obj = serializer.save()
        write_audit(self.request, "create", "banner", obj.pk, {"title": obj.title})

    def perform_update(self, serializer):
        obj = serializer.save()
        write_audit(self.request, "update", "banner", obj.pk, {"title": obj.title})

    def perform_destroy(self, instance):
        write_audit(self.request, "delete", "banner", instance.pk, {"title": instance.title})
        instance.delete()


class AdminAnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    pagination_class = AdminPagination
    queryset = Announcement.objects.all()
    permission_map = {
        "list": "banners.view",
        "retrieve": "banners.view",
        "create": "banners.create",
        "update": "banners.edit",
        "partial_update": "banners.edit",
        "destroy": "banners.delete",
    }


class AdminArticleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    pagination_class = AdminPagination
    queryset = Article.objects.select_related("category", "author").all()
    search_fields = ("title", "slug", "excerpt")
    filterset_fields = ("status", "is_featured")
    permission_map = {
        "list": "articles.view",
        "retrieve": "articles.view",
        "create": "articles.create",
        "update": "articles.edit",
        "partial_update": "articles.edit",
        "destroy": "articles.delete",
    }

    def get_serializer_class(self):
        if self.action in {"list"}:
            return ArticleListSerializer
        if self.action in {"retrieve"}:
            return ArticleDetailSerializer
        return ArticleWriteSerializer

    def perform_create(self, serializer):
        obj = serializer.save(author=self.request.user)
        write_audit(self.request, "create", "article", obj.pk, {"slug": obj.slug})

    def perform_update(self, serializer):
        obj = serializer.save()
        write_audit(self.request, "update", "article", obj.pk, {"slug": obj.slug})

    def perform_destroy(self, instance):
        write_audit(self.request, "delete", "article", instance.pk, {"slug": instance.slug})
        instance.delete()


class AdminSettingsView(APIView):
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    permission_code = "settings.manage"

    def get(self, request):
        from apps.cms.services import settings_payload

        return Response(settings_payload(request))

    def patch(self, request):
        if not isinstance(request.data, dict):
            raise APIError("Invalid settings payload.", code="validation_error")
        data = update_store_settings(dict(request.data))
        write_audit(request, "update", "settings", "store", {"keys": list(request.data.keys())})
        from apps.cms.services import settings_payload

        return Response(settings_payload(request))


class AdminNewsletterViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NewsletterAdminSerializer
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    pagination_class = AdminPagination
    queryset = NewsletterSubscriber.objects.all()
    search_fields = ("email",)
    permission_map = {
        "list": "newsletter.view",
        "retrieve": "newsletter.view",
    }
