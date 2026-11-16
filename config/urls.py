from django.conf import settings
from django.contrib import admin
from django.http import HttpRequest
from django.urls import include, path, re_path
from django.views.static import serve as django_serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def serve_media(request: HttpRequest, path: str):
    response = django_serve(request, path, document_root=settings.MEDIA_ROOT)
    response["Access-Control-Allow-Origin"] = "*"
    response["Cross-Origin-Resource-Policy"] = "cross-origin"
    return response


urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.catalog.urls")),
    path("api/v1/", include("apps.commerce.urls")),
    path("api/v1/", include("apps.cms.urls")),
    path("api/v1/", include("apps.loyalty.urls")),
    re_path(r"^media/(?P<path>.*)$", serve_media),
]
