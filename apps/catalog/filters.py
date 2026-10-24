import django_filters
from django.db.models import F, Q

from apps.catalog.models import Product


class ProductFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category__slug")
    min_price = django_filters.NumberFilter(method="filter_min_price")
    max_price = django_filters.NumberFilter(method="filter_max_price")
    roast = django_filters.CharFilter(field_name="roast_level")
    availability = django_filters.CharFilter(method="filter_availability")
    featured = django_filters.BooleanFilter(field_name="is_featured")
    is_new = django_filters.BooleanFilter()
    on_sale = django_filters.BooleanFilter(method="filter_on_sale")

    class Meta:
        model = Product
        fields = ["category", "roast", "featured", "is_new"]

    def filter_min_price(self, queryset, name, value):
        return queryset.filter(variants__is_active=True, variants__price__gte=value).distinct()

    def filter_max_price(self, queryset, name, value):
        return queryset.filter(variants__is_active=True, variants__price__lte=value).distinct()

    def filter_availability(self, queryset, name, value):
        if value == "in_stock":
            return queryset.filter(
                Q(variants__is_active=True, variants__stock_quantity__gt=0) | Q(allow_backorder=True)
            ).distinct()
        return queryset

    def filter_on_sale(self, queryset, name, value):
        if value:
            return queryset.filter(
                variants__is_active=True,
                variants__compare_at_price__isnull=False,
                variants__compare_at_price__gt=F("variants__price"),
            ).distinct()
        return queryset
