from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token
# Import custom auth views from core
from mailmind.core.views import LoginView, UserRegistrationView, EmailVerificationView, UserDetailView

urlpatterns = [
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path(
        "about/",
        TemplateView.as_view(template_name="pages/about.html"),
        name="about",
    ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    # path("users/", include("mailmind.users.urls", namespace="users")), # Commented out as app does not exist
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    # Prometheus metrics
    path("", include("django_prometheus.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# API URLS
urlpatterns += [
    # API base url - Include the main API router from mailmind.api app
    path("api/v1/", include("mailmind.api.urls")), # Central API include

    # Include core and prompt_template URLs under api/v1/
    path("api/v1/core/", include("mailmind.core.urls", namespace="core")),
    path("api/v1/prompts/", include("mailmind.prompt_templates.urls", namespace="prompt_templates")),
    path("api/v1/freelance/", include("mailmind.freelance.urls")), # Füge Freelance-URLs hinzu

    # Auth endpoints using custom views (Keep these if they are not part of the api app router)
    path("api/v1/auth/login/", LoginView.as_view(), name="auth-login"),
    path("api/v1/auth/register/", UserRegistrationView.as_view(), name="auth-register"),
    path("api/v1/auth/verify-email/<str:token>/", EmailVerificationView.as_view(), name="auth-verify-email-confirm"),
    path("api/v1/auth/verify-email/", EmailVerificationView.as_view(), name="auth-verify-email-post"),
    path("api/v1/auth/user/", UserDetailView.as_view(), name="auth-user-detail"),
    # path("api/v1/auth/login/", obtain_auth_token), # Remove default DRF login view
    
    # API Schema and Docs (These usually stay at the root level)
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
]

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path(
            "500/",
            default_views.server_error,
        ),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns 