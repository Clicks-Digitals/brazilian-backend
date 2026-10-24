from __future__ import annotations

import hashlib
import json
import shutil
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image

from apps.accounts.constants import PERMISSION_DEFINITIONS, ROLE_PERMISSIONS
from apps.accounts.models import AdminRole, Permission, User
from apps.catalog.models import Category, Product, ProductImage, ProductVariant
from apps.cms.models import Announcement, Article, ArticleCategory, Banner, LegalPage, NewsletterSubscriber, StoreSetting
from apps.commerce.models import Discount, Order, OrderItem, OrderStatusHistory, PaymentRecord
from apps.core.utils import money

ROOT = Path(settings.BASE_DIR).resolve()
if not (ROOT / "shared" / "catalog.json").exists():
    ROOT = ROOT.parent
CATALOG_PATH = ROOT / "shared" / "catalog.json"
PRODUCTS_DIR = ROOT / "_source_assets" / "Brazillian Coffee House" / "Website Products"
LOGO_SRC = ROOT / "_source_assets" / "brand" / "logo-2.png"


def stable_stock(sku: str) -> int:
    digest = hashlib.sha256(sku.encode("utf-8")).hexdigest()
    return 8 + (int(digest, 16) % 33)


def _luminance(rgb) -> float:
    r, g, b = rgb[:3]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def optimize_jpeg(src: Path) -> ContentFile:
    image = Image.open(src)
    image.load()
    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        sample = rgba.convert("RGB").resize((1, 1))
        bg = (0, 0, 0) if _luminance(sample.getpixel((0, 0))) < 80 else (255, 255, 255)
        background = Image.new("RGB", rgba.size, bg)
        background.paste(rgba, mask=rgba.split()[-1])
        image = background
    else:
        image = image.convert("RGB")
    max_width = 1600
    if image.width > max_width:
        height = int(image.height * (max_width / image.width))
        image = image.resize((max_width, height), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85, optimize=True)
    buffer.seek(0)
    name = f"{slugify(src.stem) or 'image'}.jpg"
    return ContentFile(buffer.getvalue(), name=name)


class Command(BaseCommand):
    help = "Seed the Brazilian Coffee House catalog, CMS, users, and sample orders."

    def handle(self, *args, **options):
        if not CATALOG_PATH.exists():
            raise SystemExit(f"Catalog not found: {CATALOG_PATH}")
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        self.stdout.write("Seeding permissions and users...")
        perms = self.seed_permissions()
        self.seed_users(perms)
        self.stdout.write("Seeding catalog...")
        categories, products = self.seed_catalog(catalog)
        self.stdout.write("Seeding brand, CMS, and merchandising...")
        self.seed_logo()
        self.seed_settings(catalog)
        self.seed_banners(products)
        self.seed_announcement()
        self.seed_articles(products)
        self.seed_legal()
        self.seed_discount()
        self.seed_newsletter()
        self.stdout.write("Seeding sample orders...")
        self.seed_orders(products)
        self.stdout.write(self.style.SUCCESS("Store seed complete."))

    def seed_permissions(self):
        mapping = {}
        for code, module, action, description in PERMISSION_DEFINITIONS:
            perm, _ = Permission.objects.update_or_create(
                code=code,
                defaults={"module": module, "action": action, "description": description},
            )
            mapping[code] = perm
        return mapping

    def seed_users(self, perms):
        super_role, _ = AdminRole.objects.update_or_create(
            slug="super-admin",
            defaults={
                "name": "Super Admin",
                "description": "Full access",
                "is_system": True,
            },
        )
        super_role.permissions.set(perms.values())

        role_map = {}
        for name, codes in ROLE_PERMISSIONS.items():
            role, _ = AdminRole.objects.update_or_create(
                slug=slugify(name),
                defaults={"name": name, "description": name, "is_system": True},
            )
            role.permissions.set([perms[c] for c in codes if c in perms])
            role_map[name] = role

        def upsert_user(email, password, **extra):
            user, created = User.objects.update_or_create(email=email, defaults=extra)
            user.set_password(password)
            user.save()
            return user

        upsert_user(
            "admin@bch-coffee.com",
            "Admin12345!",
            first_name="Store",
            last_name="Admin",
            phone="06 222 3330",
            is_staff=True,
            is_superuser=True,
            is_active=True,
            user_type=User.UserType.STAFF,
            role=super_role,
        )
        upsert_user(
            "manager@bch-coffee.com",
            "Manager12345!",
            first_name="Lina",
            last_name="Haddad",
            is_staff=True,
            is_superuser=False,
            is_active=True,
            user_type=User.UserType.STAFF,
            role=role_map["Store Manager"],
        )
        upsert_user(
            "content@bch-coffee.com",
            "Content12345!",
            first_name="Maya",
            last_name="Nasser",
            is_staff=True,
            is_superuser=False,
            is_active=True,
            user_type=User.UserType.STAFF,
            role=role_map["Content Manager"],
        )
        upsert_user(
            "orders@bch-coffee.com",
            "Orders12345!",
            first_name="Omar",
            last_name="Saleh",
            is_staff=True,
            is_superuser=False,
            is_active=True,
            user_type=User.UserType.STAFF,
            role=role_map["Order Manager"],
        )
        upsert_user(
            "analyst@bch-coffee.com",
            "Analyst12345!",
            first_name="Rami",
            last_name="Issa",
            is_staff=True,
            is_superuser=False,
            is_active=True,
            user_type=User.UserType.STAFF,
            role=role_map["Analyst"],
        )
        upsert_user(
            "customer@example.com",
            "Customer12345!",
            first_name="Sara",
            last_name="Ahmad",
            phone="0795551234",
            is_staff=False,
            is_superuser=False,
            is_active=True,
            user_type=User.UserType.CUSTOMER,
            role=None,
        )

    def seed_catalog(self, catalog):
        categories = {}
        for item in catalog["categories"]:
            category, _ = Category.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "name": item["name"],
                    "name_ar": item.get("name_ar", ""),
                    "description": item.get("description", ""),
                    "is_active": True,
                    "show_in_nav": item.get("nav", True),
                    "display_order": item.get("order", 0),
                },
            )
            categories[item["slug"]] = category

        products = {}
        for item in catalog["products"]:
            category = categories[item["category"]]
            roast = item.get("roast") or ""
            product, _ = Product.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "category": category,
                    "name": item["name"],
                    "name_ar": item.get("name_ar", ""),
                    "sku": item["sku"],
                    "short_description": item.get("description", "")[:320],
                    "description": item.get("description", ""),
                    "tasting_notes": item.get("tasting") or "",
                    "roast_level": roast,
                    "origin": "Jordan / Brazil heritage",
                    "is_active": True,
                    "is_featured": bool(item.get("featured")),
                    "is_new": bool(item.get("is_new")),
                    "published_at": timezone.now(),
                },
            )
            variant, _ = ProductVariant.objects.update_or_create(
                sku=item["sku"],
                defaults={
                    "product": product,
                    "name": item.get("weight") or "Default",
                    "price": money(item["price"]),
                    "compare_at_price": money(item["compare"]) if item.get("compare") else None,
                    "stock_quantity": stable_stock(item["sku"]),
                    "weight_label": item.get("weight") or "",
                    "is_active": True,
                },
            )
            source = PRODUCTS_DIR / item["source"]
            if source.exists() and not product.images.exists():
                content = optimize_jpeg(source)
                image = ProductImage(product=product, alt_text=product.name, is_primary=True, sort_order=0)
                image.image.save(content.name, content, save=True)
            if not category.image and product.images.exists():
                src_file = product.images.first().image
                category.image.save(Path(src_file.name).name, src_file.file, save=True)
            products[item["slug"]] = product
        return categories, products

    def seed_logo(self):
        dest_dir = Path(settings.MEDIA_ROOT) / "brand"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "logo.png"
        if LOGO_SRC.exists():
            shutil.copyfile(LOGO_SRC, dest)

    def seed_settings(self, catalog):
        brand = catalog.get("brand", {})
        value = {
            "store_name": "Brazilian Coffee House",
            "store_name_ar": brand.get("name_ar", "بيت البن البرازيلي"),
            "currency": "JOD",
            "currency_symbol": "JD",
            "phone": "06 222 3330",
            "email": "info@bch-coffee.com",
            "website": brand.get("website", "https://braziliancoffeehouse.com"),
            "logo": "/media/brand/logo.png",
            "about": (
                "Brazilian Coffee House began in 1955 at Kuwait International Mill, roasting "
                "coffee for homes and cafés across the region. In 1995 the house arrived in "
                "Jordan, bringing the same craft of Turkish, filter, espresso, and specialty "
                "blends to Amman. Every tin still carries that mill heritage — slow, careful, "
                "and made to be shared."
            ),
            "established": 1955,
            "jordan_since": 1995,
            "branches": [
                {"name": "Abdali Boulevard", "city": "Amman", "phone": "06 222 3330"},
                {"name": "Sweifieh", "city": "Amman", "phone": "06 222 3330"},
                {"name": "Khalda", "city": "Amman", "phone": "06 222 3330"},
            ],
            "social": {
                "instagram": "https://instagram.com/braziliancoffeehouse",
                "facebook": "https://facebook.com/braziliancoffeehouse",
                "tiktok": "",
            },
            "delivery_fee": "2.000",
            "free_shipping_over": "25.000",
            "homepage_sections": [
                "announcement",
                "hero",
                "featured_categories",
                "featured_products",
                "promo",
                "new_arrivals",
                "journal",
            ],
        }
        StoreSetting.objects.update_or_create(key="store", defaults={"value": value})

    def _copy_banner_image(self, product: Product, filename: str) -> ContentFile | None:
        image = product.images.first()
        if not image:
            return None
        path = Path(image.image.path)
        if not path.exists():
            return None
        return ContentFile(path.read_bytes(), name=filename)

    def seed_banners(self, products):
        specs = [
            {
                "slug_product": "espresso-medium",
                "title": "Espresso, roasted for the machine",
                "subtitle": "100% Arabica espresso with chocolate and orange — the house shot since the mill days.",
                "cta_label": "Shop espresso",
                "cta_url": "/products?category=espresso",
                "placement": Banner.Placement.HERO,
                "order": 1,
                "file": "hero-espresso.jpg",
            },
            {
                "slug_product": "turkish-coffee-medium",
                "title": "The cezve, as it should be",
                "subtitle": "Medium Turkish roast with cardamom, packed for a proper cup at home.",
                "cta_label": "Shop Turkish coffee",
                "cta_url": "/products?category=turkish-coffee",
                "placement": Banner.Placement.HERO,
                "order": 2,
                "file": "hero-turkish.jpg",
            },
            {
                "slug_product": "filter-coffee-original",
                "title": "Filter coffee, origin lots",
                "subtitle": "Brazil, Colombia, Kenya, and Ethiopia — roasted for pour-over and drip.",
                "cta_label": "Shop filter",
                "cta_url": "/products?category=filter-coffee",
                "placement": Banner.Placement.HERO,
                "order": 3,
                "file": "hero-filter.jpg",
            },
        ]
        for spec in specs:
            product = products.get(spec["slug_product"])
            content = self._copy_banner_image(product, spec["file"]) if product else None
            banner = Banner.objects.filter(title=spec["title"]).first()
            if banner is None:
                banner = Banner(
                    title=spec["title"],
                    subtitle=spec["subtitle"],
                    cta_label=spec["cta_label"],
                    cta_url=spec["cta_url"],
                    placement=spec["placement"],
                    alignment=Banner.Alignment.LEFT,
                    is_active=True,
                    display_order=spec["order"],
                )
                if content:
                    banner.desktop_image.save(spec["file"], content, save=True)
                elif product and product.images.exists():
                    src = product.images.first().image
                    banner.desktop_image.save(spec["file"], src.file, save=True)
            else:
                banner.subtitle = spec["subtitle"]
                banner.cta_label = spec["cta_label"]
                banner.cta_url = spec["cta_url"]
                banner.placement = spec["placement"]
                banner.is_active = True
                banner.display_order = spec["order"]
                banner.save()
                if content and not banner.desktop_image:
                    banner.desktop_image.save(spec["file"], content, save=True)

        promo_product = products.get("drip-coffee-original") or products.get("rio-house-3-in-1")
        content = self._copy_banner_image(promo_product, "promo-drip.jpg") if promo_product else None
        promo = Banner.objects.filter(title="Drip coffee, anywhere").first()
        if promo is None:
            promo = Banner(
                title="Drip coffee, anywhere",
                subtitle="Single-serve drip bags for a clean cup on the desk, in the car, or visiting family.",
                cta_label="Try drip bags",
                cta_url="/products?category=drip-coffee",
                placement=Banner.Placement.PROMO,
                alignment=Banner.Alignment.CENTER,
                is_active=True,
                display_order=1,
            )
            if content:
                promo.desktop_image.save("promo-drip.jpg", content, save=True)
            elif promo_product and promo_product.images.exists():
                src = promo_product.images.first().image
                promo.desktop_image.save("promo-drip.jpg", src.file, save=True)
        else:
            promo.is_active = True
            promo.placement = Banner.Placement.PROMO
            promo.save()

    def seed_announcement(self):
        Announcement.objects.update_or_create(
            text="Free delivery in Amman over JD 25 — demo, editable.",
            defaults={
                "link_url": "/products",
                "is_active": True,
                "dismissible": True,
                "display_order": 0,
            },
        )

    def seed_articles(self, products):
        category, _ = ArticleCategory.objects.update_or_create(
            slug="journal",
            defaults={"name": "Journal", "description": "Coffee culture from the house mill."},
        )
        author = User.objects.filter(email="content@bch-coffee.com").first()
        articles = [
            {
                "slug": "coffee-culture-in-amman",
                "title": "Coffee culture in Amman",
                "excerpt": "From the cezve on the stove to the office espresso — how Jordan drinks coffee now.",
                "cover": "turkish-coffee-medium",
                "related": ["turkish-coffee-medium", "turkish-coffee-light", "espresso-medium"],
                "content": """
<p>Amman drinks coffee in layers. There is the morning cezve, cardamom rising through the kitchen.
There is the office machine, the visit to a parent’s house, the tin opened for guests.</p>
<p>Brazilian Coffee House has been part of that rhythm since 1995, after decades of roasting at
Kuwait International Mill. The blends are familiar on purpose: Turkish, filter, espresso, and the
sachets people keep in a drawer for unexpected company.</p>
""",
            },
            {
                "slug": "how-we-make-turkish-coffee",
                "title": "How we make Turkish coffee",
                "excerpt": "A short guide to the house Turkish roast, the grind, and a calm cezve.",
                "cover": "turkish-coffee-light",
                "related": ["turkish-coffee-light", "turkish-coffee-medium", "turkish-coffee-jordanian-blend"],
                "content": """
<p>Turkish coffee is not hurried. Use a fine grind, cold water, and a cezve that can sit on a low flame.
Sweeten in the pot if you take sugar. Add cardamom if you want the house cup.</p>
<p>Our light, medium, and dark Turkish tins are roasted for that method — not for a machine, not for a
filter. Bring it just to the rise, pour, and wait for the grounds to settle.</p>
""",
            },
            {
                "slug": "from-the-mill-to-jordan",
                "title": "From the mill to Jordan",
                "excerpt": "A heritage note: 1955 at Kuwait International Mill, 1995 in Jordan.",
                "cover": "espresso-medium",
                "related": ["espresso-medium", "espresso-dark", "filter-coffee-original"],
                "content": """
<p>The house began in 1955 at Kuwait International Mill. Forty years later the same roasting craft
arrived in Jordan. The tins changed, the cities changed, the mill memory did not.</p>
<p>That is the story we still tell in the shop: origin lots and flavored Turkish, espresso for the
machine, filter for the weekend, and Rio House for the cupboard that has to work on a busy morning.</p>
""",
            },
        ]
        now = timezone.now()
        for index, spec in enumerate(articles):
            article, created = Article.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "title": spec["title"],
                    "excerpt": spec["excerpt"],
                    "content": spec["content"].strip(),
                    "category": category,
                    "author": author,
                    "status": Article.Status.PUBLISHED,
                    "is_featured": index == 0,
                    "published_at": now - timedelta(days=index + 1),
                    "seo_title": spec["title"],
                    "seo_description": spec["excerpt"],
                },
            )
            cover_product = products.get(spec["cover"])
            if cover_product and cover_product.images.exists() and (created or not article.cover_image):
                src = cover_product.images.first().image
                article.cover_image.save(Path(src.name).name, src.file, save=True)
            related = [products[slug] for slug in spec.get("related") or [] if products.get(slug)]
            if not related and cover_product:
                related = [cover_product]
            if related:
                article.related_products.set(related)

    def seed_legal(self):
        pages = {
            "privacy": (
                "Privacy Policy",
                "<p>Brazilian Coffee House collects only what we need to fulfil orders, answer "
                "enquiries, and improve the shop. We do not sell personal data. Contact "
                "info@bch-coffee.com with privacy requests.</p>",
            ),
            "terms": (
                "Terms of Sale",
                "<p>Orders are an offer to purchase. Cash on delivery orders are confirmed by our "
                "team. Prices are in Jordanian dinars. Demonstration catalogue prices may be edited "
                "in the admin.</p>",
            ),
            "shipping": (
                "Shipping",
                "<p>We deliver in Amman. Delivery is JD 2.000, free over JD 25.000. Lead times are "
                "confirmed after the order is placed. Remote areas may require a phone confirmation.</p>",
            ),
            "returns": (
                "Returns",
                "<p>Unopened tins and sealed goods may be returned within 7 days if unused. "
                "Perishable opened coffee is not returnable. Write to info@bch-coffee.com to start a return.</p>",
            ),
        }
        for slug, (title, content) in pages.items():
            LegalPage.objects.update_or_create(
                slug=slug, defaults={"title": title, "content": content, "is_published": True}
            )

    def seed_discount(self):
        Discount.objects.update_or_create(
            code="WELCOME10",
            defaults={
                "name": "Welcome 10%",
                "discount_type": Discount.DiscountType.PERCENTAGE,
                "value": Decimal("10.000"),
                "min_order_amount": Decimal("10.000"),
                "is_active": True,
            },
        )

    def seed_newsletter(self):
        for email in ("sara@example.com", "guest@example.com", "press@bch-coffee.com"):
            NewsletterSubscriber.objects.update_or_create(
                email=email, defaults={"is_active": True, "source": "seed"}
            )

    def seed_orders(self, products):
        customer = User.objects.filter(email="customer@example.com").first()
        picks = [
            ("turkish-coffee-medium", 2),
            ("espresso-medium", 1),
            ("filter-coffee-original", 2),
            ("drip-coffee-original", 3),
        ]
        specs = [
            {
                "key": "seed-order-pending",
                "status": Order.Status.PENDING,
                "payment_status": Order.PaymentStatus.UNPAID,
                "days_ago": 1,
                "items": picks[:1],
            },
            {
                "key": "seed-order-confirmed",
                "status": Order.Status.CONFIRMED,
                "payment_status": Order.PaymentStatus.UNPAID,
                "days_ago": 3,
                "items": picks[1:3],
            },
            {
                "key": "seed-order-delivered",
                "status": Order.Status.DELIVERED,
                "payment_status": Order.PaymentStatus.PAID,
                "days_ago": 8,
                "items": picks[2:4],
            },
            {
                "key": "seed-order-cancelled",
                "status": Order.Status.CANCELLED,
                "payment_status": Order.PaymentStatus.UNPAID,
                "days_ago": 5,
                "items": picks[:2],
            },
        ]
        year = timezone.now().year
        for index, spec in enumerate(specs, start=1):
            if Order.objects.filter(idempotency_key=spec["key"]).exists():
                continue
            lines = []
            subtotal = Decimal("0.000")
            for slug, qty in spec["items"]:
                product = products.get(slug)
                if not product:
                    continue
                variant = product.variants.first()
                if not variant:
                    continue
                line_total = money(variant.price * qty)
                lines.append((product, variant, qty, line_total))
                subtotal += line_total
            delivery = Decimal("0.000") if subtotal >= Decimal("25.000") else Decimal("2.000")
            total = money(subtotal + delivery)
            order_number = f"BCH-{year}-{index:04d}"
            while Order.objects.filter(order_number=order_number).exists():
                index += 1
                order_number = f"BCH-{year}-{index:04d}"
            order = Order.objects.create(
                order_number=order_number,
                user=customer,
                email=customer.email if customer else "customer@example.com",
                customer_name=customer.full_name if customer else "Sara Ahmad",
                phone=customer.phone if customer else "0795551234",
                shipping_line1="12 Rainbow Street",
                shipping_city="Amman",
                shipping_area="Jabal Amman",
                shipping_country="Jordan",
                status=spec["status"],
                payment_status=spec["payment_status"],
                payment_method=Order.PaymentMethod.COD,
                subtotal=subtotal,
                delivery_fee=delivery,
                total=total,
                currency="JOD",
                idempotency_key=spec["key"],
            )
            Order.objects.filter(pk=order.pk).update(
                placed_at=timezone.now() - timedelta(days=spec["days_ago"])
            )
            for product, variant, qty, line_total in lines:
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    variant=variant,
                    product_name=product.name,
                    variant_name=variant.name,
                    sku=variant.sku,
                    quantity=qty,
                    unit_price=variant.price,
                    line_total=line_total,
                )
                if spec["status"] != Order.Status.CANCELLED:
                    variant.stock_quantity = max(variant.stock_quantity - qty, 0)
                    variant.save(update_fields=["stock_quantity", "updated_at"])
            OrderStatusHistory.objects.create(
                order=order, from_status="", to_status=spec["status"], note="Seeded order"
            )
            payment_status = (
                PaymentRecord.Status.COMPLETED
                if spec["payment_status"] == Order.PaymentStatus.PAID
                else PaymentRecord.Status.PENDING
            )
            PaymentRecord.objects.create(
                order=order,
                provider="cod",
                status=payment_status,
                amount=total,
                currency="JOD",
            )
