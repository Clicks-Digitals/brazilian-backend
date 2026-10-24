from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.cms.views import (
    AdminAnnouncementViewSet,
    AdminArticleViewSet,
    AdminBannerViewSet,
    AdminNewsletterViewSet,
    AdminSettingsView,
    AnnouncementListView,
    ArticleDetailView,
    ArticleListView,
    BannerListView,
    ContactView,
    LegalPageView,
    NewsletterSubscribeView,
    PublicSettingsView,
    StorefrontView,
)

router = DefaultRouter()
router.register("admin/banners", AdminBannerViewSet, basename="admin-banners")
router.register("admin/announcements", AdminAnnouncementViewSet, basename="admin-announcements")
router.register("admin/articles", AdminArticleViewSet, basename="admin-articles")
router.register("admin/newsletter", AdminNewsletterViewSet, basename="admin-newsletter")

urlpatterns = [
    path("storefront/", StorefrontView.as_view(), name="storefront"),
    path("banners/", BannerListView.as_view(), name="banners"),
    path("announcements/", AnnouncementListView.as_view(), name="announcements"),
    path("articles/", ArticleListView.as_view(), name="articles"),
    path("articles/<slug:slug>/", ArticleDetailView.as_view(), name="article-detail"),
    path("pages/<slug:slug>/", LegalPageView.as_view(), name="legal-page"),
    path("settings/", PublicSettingsView.as_view(), name="public-settings"),
    path("newsletter/", NewsletterSubscribeView.as_view(), name="newsletter"),
    path("contact/", ContactView.as_view(), name="contact"),
    path("admin/settings/", AdminSettingsView.as_view(), name="admin-settings"),
    path("", include(router.urls)),
]
