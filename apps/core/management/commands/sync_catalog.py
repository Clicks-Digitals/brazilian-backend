from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from apps.cms.models import Article
from apps.core.management.commands.seed_store import CATALOG_PATH, Command as SeedCommand

AMMAN_ARTICLE_BODY = (
    "<p>In Amman, coffee is more than just a drink. It’s a morning tradition, a warm welcome, "
    "and a moment that brings people together. From the rich aroma of Turkish coffee to the "
    "comforting taste of a freshly brewed cup, coffee has always been part of our everyday stories.</p>\n"
    "<p>Through generations, one thing remains unchanged: our passion for great coffee.</p>"
)


class Command(BaseCommand):
    help = "Upsert catalog products, prices, shelf order, and images from catalog.json without touching orders."

    def handle(self, *args, **options):
        if not CATALOG_PATH.exists():
            raise SystemExit(f"Catalog not found: {CATALOG_PATH}")
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        seed = SeedCommand()
        seed.stdout = self.stdout
        seed.style = self.style
        self.stdout.write("Syncing catalog from catalog.json...")
        categories, products = seed.seed_catalog(catalog)
        amman_updated = Article.objects.filter(slug="coffee-culture-in-amman").update(content=AMMAN_ARTICLE_BODY)
        from apps.cms.models import StoreSetting

        setting = StoreSetting.objects.filter(key="store").first()
        if setting and isinstance(setting.value, dict):
            value = dict(setting.value)
            value["email"] = "nermen.k@bch-coffee.com"
            setting.value = value
            setting.save(update_fields=["value"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Catalog synced: {len(categories)} categories, {len(products)} products"
                + (f", Amman article updated ({amman_updated})." if amman_updated else ".")
            )
        )
