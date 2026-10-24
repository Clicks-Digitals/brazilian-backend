from django.contrib import admin

from apps.cms.models import (
    Announcement,
    Article,
    ArticleCategory,
    Banner,
    ContactMessage,
    LegalPage,
    NewsletterSubscriber,
    StoreSetting,
)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("text", "is_active", "display_order")


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("title", "placement", "is_active", "display_order")
    list_filter = ("placement", "is_active")


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "is_featured", "published_at")
    list_filter = ("status", "is_featured")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("related_products", "related_articles")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "created_at")
    search_fields = ("name", "email", "message")
    readonly_fields = ("name", "email", "phone", "message", "created_at")


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "source", "consented_at")
    search_fields = ("email",)


@admin.register(StoreSetting)
class StoreSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "updated_at")


@admin.register(LegalPage)
class LegalPageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "updated_at")
