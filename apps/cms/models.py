from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Announcement(models.Model):
    text = models.CharField(max_length=255)
    link_url = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    dismissible = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "-id"]

    def __str__(self) -> str:
        return self.text[:60]


class Banner(models.Model):
    class Placement(models.TextChoices):
        HERO = "hero", "Hero slider"
        PROMO = "promo", "Promotional section"
        CATEGORY = "category", "Category campaign"

    class Alignment(models.TextChoices):
        LEFT = "left", "Left"
        CENTER = "center", "Center"
        RIGHT = "right", "Right"

    title = models.CharField(max_length=180)
    subtitle = models.TextField(blank=True)
    cta_label = models.CharField(max_length=80, blank=True)
    cta_url = models.CharField(max_length=255, blank=True)
    secondary_cta_label = models.CharField(max_length=80, blank=True)
    secondary_cta_url = models.CharField(max_length=255, blank=True)
    desktop_image = models.ImageField(upload_to="banners/")
    mobile_image = models.ImageField(upload_to="banners/mobile/", blank=True)
    alignment = models.CharField(max_length=12, choices=Alignment.choices, default=Alignment.LEFT)
    placement = models.CharField(max_length=20, choices=Placement.choices, default=Placement.HERO)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "-id"]

    def __str__(self) -> str:
        return self.title


class ArticleCategory(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "article categories"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=220)
    slug = models.SlugField(unique=True, max_length=240)
    excerpt = models.CharField(max_length=400, blank=True)
    content = models.TextField()
    cover_image = models.ImageField(upload_to="articles/", blank=True)
    category = models.ForeignKey(
        ArticleCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name="articles"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    is_featured = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    related_products = models.ManyToManyField("catalog.Product", blank=True, related_name="articles")
    related_articles = models.ManyToManyField("self", blank=True)
    seo_title = models.CharField(max_length=180, blank=True)
    seo_description = models.CharField(max_length=320, blank=True)
    og_image = models.ImageField(upload_to="articles/og/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    source = models.CharField(max_length=40, default="storefront")
    consented_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-consented_at"]

    def __str__(self) -> str:
        return self.email


class StoreSetting(models.Model):
    """Singleton-style key/value store for CMS-managed storefront configuration."""

    key = models.SlugField(unique=True, max_length=80)
    value = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.key


class LegalPage(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=180)
    content = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title
