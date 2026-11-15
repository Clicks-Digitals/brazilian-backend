from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from apps.core.management.commands.seed_store import CATALOG_PATH, Command as SeedCommand


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
        self.stdout.write(
            self.style.SUCCESS(f"Catalog synced: {len(categories)} categories, {len(products)} products.")
        )
