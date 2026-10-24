from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=160)
    name_ar = models.CharField(max_length=160, blank=True)
    slug = models.SlugField(unique=True, max_length=180)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    is_active = models.BooleanField(default=True)
    show_in_nav = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    seo_title = models.CharField(max_length=180, blank=True)
    seo_description = models.CharField(max_length=320, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    class RoastLevel(models.TextChoices):
        LIGHT = "light", "Light"
        MEDIUM = "medium", "Medium"
        MEDIUM_DARK = "medium-dark", "Medium dark"
        DARK = "dark", "Dark"

    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    name = models.CharField(max_length=200)
    name_ar = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(unique=True, max_length=220)
    sku = models.CharField(max_length=64, unique=True)
    short_description = models.CharField(max_length=320, blank=True)
    description = models.TextField(blank=True)
    tasting_notes = models.CharField(max_length=255, blank=True)
    roast_level = models.CharField(max_length=20, choices=RoastLevel.choices, blank=True)
    origin = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    is_promotional = models.BooleanField(default=False)
    allow_backorder = models.BooleanField(default=False)
    seo_title = models.CharField(max_length=180, blank=True)
    seo_description = models.CharField(max_length=320, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "is_featured"]),
            models.Index(fields=["category", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def default_variant(self):
        return self.variants.filter(is_active=True).order_by("id").first()


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=180, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"{self.product.slug} image {self.pk}"


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=120)
    sku = models.CharField(max_length=64, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=3)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    weight_label = models.CharField(max_length=80, blank=True)
    image = models.ImageField(upload_to="products/variants/", blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["sku"]), models.Index(fields=["product", "is_active"])]

    def __str__(self) -> str:
        return f"{self.product.name} — {self.name}"

    @property
    def in_stock(self) -> bool:
        return self.stock_quantity > 0 or self.product.allow_backorder


class ProductAttribute(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self) -> str:
        return self.name


class ProductAttributeValue(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="attribute_values")
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.CASCADE, related_name="values")
    value = models.CharField(max_length=160)

    class Meta:
        unique_together = ("product", "attribute")

    def __str__(self) -> str:
        return f"{self.attribute.name}: {self.value}"
