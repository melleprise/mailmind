import environ
import os
from pathlib import Path
from .base import *  # Import base settings
import smtplib

env = environ.Env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR is already defined in base.py

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="!!!SET DJANGO_SECRET_KEY!!!",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1", "backend", "caddy", "localhost:8080"]

# CSRF Configuration for Development
# ------------------------------------------------------------------------------
# Allow requests from the frontend development server
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8080", # Development frontend origin
]

# APPS - Inherited from base.py, add development-specific apps
# ------------------------------------------------------------------------------
INSTALLED_APPS += [
    "whitenoise.runserver_nostatic", # For development serving static files
    # "debug_toolbar", # Temporär auskommentiert
    "django_extensions",
]

# MIDDLEWARE - Inherited from base.py, add development-specific middleware
# ------------------------------------------------------------------------------
# Ensure PrometheusBeforeMiddleware is first and PrometheusAfterMiddleware is last
# Find the index of PrometheusAfterMiddleware to insert DebugToolbar before it
# Temporär auskommentiert
# prometheus_after_index = -1
# try:
#     prometheus_after_index = MIDDLEWARE.index("django_prometheus.middleware.PrometheusAfterMiddleware")
# except ValueError:
#     # If PrometheusAfterMiddleware is not found, just append
#     MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")
# else:
#     MIDDLEWARE.insert(prometheus_after_index, "debug_toolbar.middleware.DebugToolbarMiddleware")

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "mailmind.core.middleware.LogHeadersMiddleware", # Re-enabled
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

# STATIC
# ------------------------------------------------------------------------------
# STATIC_ROOT, STATIC_URL, STATICFILES_DIRS, STATICFILES_FINDERS are likely defined in base.py
# If not, uncomment and define them here.
# STATIC_ROOT = str(BASE_DIR / "staticfiles")
# STATIC_URL = "/static/"
# STATICFILES_DIRS = [str(BASE_DIR / "static")]
# STATICFILES_FINDERS = [
#     "django.contrib.staticfiles.finders.FileSystemFinder",
#     "django.contrib.staticfiles.finders.AppDirectoriesFinder",
# ]

# MEDIA
# ------------------------------------------------------------------------------
# MEDIA_ROOT, MEDIA_URL are likely defined in base.py
# If not, uncomment and define them here.
# MEDIA_ROOT = str(BASE_DIR / "media")
# MEDIA_URL = "/media/"

# TEMPLATES
# ------------------------------------------------------------------------------
# TEMPLATES is likely defined in base.py. Override or extend if needed.
# TEMPLATES[0]["OPTIONS"]["context_processors"] += [...] # Example extension
# Uncommenting and defining TEMPLATES here as it's missing in base.py
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(BASE_DIR / "templates")], # Assuming templates directory
        "APP_DIRS": True, # Required for admin and app templates
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                # Add your custom context processors if any from base.py if needed
            ],
        },
    }
]

# Update TEMPLATES DIRS if it's different in development
# TEMPLATES[0]["DIRS"] = [str(BASE_DIR / "templates")]

# CRISPY FORMS - Likely configured in base.py
# Re-add crispy settings if they were removed from base.py or not present
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# FIXTURES
# ------------------------------------------------------------------------------
# FIXTURE_DIRS is likely defined in base.py
# FIXTURE_DIRS = (str(BASE_DIR / "fixtures"),)

# SECURITY
# ------------------------------------------------------------------------------
# These might be fine from base.py, override if needed for development
# SESSION_COOKIE_HTTPONLY = True
# CSRF_COOKIE_HTTPONLY = True
# X_FRAME_OPTIONS = "DENY"

# EMAIL
# ------------------------------------------------------------------------------
# Default to console backend for development
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# EMAIL_HOST, PORT, TLS, USER, PASSWORD, DEFAULT_FROM_EMAIL likely inherited or okay as default None/empty
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env("EMAIL_PORT")
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")

# ADMIN
# ------------------------------------------------------------------------------
# ADMIN_URL is likely defined in base.py
# ADMIN_URL = "admin/"

# QDRANT Configuration - Inherited from base.py or specific to dev?
# ------------------------------------------------------------------------------
QDRANT_URL = env("QDRANT_URL", default="http://qdrant:6333")
QDRANT_API_KEY = env("QDRANT_API_KEY", default=None)

# Gemini API Key - Inherited from base.py or specific to dev?
# ------------------------------------------------------------------------------
GEMINI_API_KEY = env("GEMINI_API_KEY", default=None)

# PASSWORDS
# ------------------------------------------------------------------------------
# PASSWORD_HASHERS, AUTH_PASSWORD_VALIDATORS likely inherited from base.py

# LOGGING - Override for more verbose logging in development
# ------------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"
        },
         'simple': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": "DEBUG", "handlers": ["console"]}, # Auf DEBUG setzen
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "DEBUG", # Auf DEBUG setzen
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING", # Bleibt WARNING
            "propagate": False,
        },
        "mailmind": { # Your app
            "handlers": ["console"],
            "level": "DEBUG", # Auf DEBUG setzen
            "propagate": False,
        },
        "aioimaplib": { # Keep specific level if needed
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        # Add other loggers as needed
    },
}


# django-allauth Settings - Inherited from base.py, override if needed
# ------------------------------------------------------------------------------
# ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
# ACCOUNT_AUTHENTICATION_METHOD = "email"
# ACCOUNT_EMAIL_REQUIRED = True
# ACCOUNT_USERNAME_REQUIRED = False
# ACCOUNT_USER_MODEL_USERNAME_FIELD = None
# ACCOUNT_EMAIL_VERIFICATION = "mandatory" # Maybe set to "optional" or "none" for dev?
# ACCOUNT_EMAIL_VERIFICATION = "none"
# ACCOUNT_ADAPTER = "mailmind.users.adapters.AccountAdapter"
# SOCIALACCOUNT_ADAPTER = "mailmind.users.adapters.SocialAccountAdapter"
# SOCIALACCOUNT_AUTO_SIGNUP = True
# SOCIALACCOUNT_PROVIDERS = {}
# SITE_ID = 1

# URLs - Inherited from base.py
# ------------------------------------------------------------------------------
# ROOT_URLCONF = "config.urls"
# WSGI_APPLICATION = "config.wsgi.application"
# ASGI_APPLICATION = "config.asgi.application"

# DATABASES - Override for development database
# ------------------------------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://mailmind:mailmind@postgres:5432/mailmind", # Default dev DB
    )
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True

# CACHES - Configure cache for development (e.g., dummy or local memory)
# ------------------------------------------------------------------------------
# CACHES = {
#     "default": {
#         "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
#         "LOCATION": "",
#     }
# }

# Use Redis cache (shared between processes) instead of locmem for development
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        # Use Redis container name 'redis' and DB 1 (to avoid conflict with Q/Channels potentially using 0)
        "LOCATION": env("REDIS_CACHE_URL", default="redis://redis:6379/1"), 
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Optional: Add password if your Redis requires it
            # "PASSWORD": env("REDIS_PASSWORD", default=None),
            # Optional: Add connection pool settings if needed
        }
    }
}

# django-debug-toolbar
# ------------------------------------------------------------------------------
# Temporär auskommentiert
# # https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#configure-internal-ips
# INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]
# if env("USE_DOCKER", default='no') == "yes":
#     import socket
#     hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
#     INTERNAL_IPS += [ip[:-1] + "1" for ip in ips]
#     try:
#         _, _, ips = socket.gethostbyname_ex("node")
#         INTERNAL_IPS.extend(ips)
#     except socket.gaierror:
#         # The node service is not resolved
#         pass
# 
# DEBUG_TOOLBAR_CONFIG = {
#     "DISABLE_PANELS": {
#         "debug_toolbar.panels.redirects.RedirectsPanel",
#          # Add other panels to disable if needed
#     },
#     "SHOW_TEMPLATE_CONTEXT": True,
#     # "ROOT_TAG_EXTRA_ATTRS": "hx-preserve", # For htmx compatibility if needed
# }
# # https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#middleware
# # Middleware already added above

# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/

# Celery / Django Q - Development settings
# ------------------------------------------------------------------------------
# Use synchronous execution for easier debugging in development
# Note: Q_CLUSTER settings might be in base.py, override if needed
Q_CLUSTER = {
    # Development specific settings for Django Q override/extend base
    'name': 'mailmind-dev-override', 
    'workers': 2, 
    'sync': False,  # IMPORTANT: Ensure async execution for async tasks
    # Explicitly set Redis config for development to use the service name
    'redis': {
        'host': 'redis', # Ensure it uses the service name, not localhost
        'port': 6379,
        'db': 0, # Or use env var if preferred: env.int("REDIS_DB_Q", default=0)
    }
    # Other overrides...
}

# Your specific settings
# ------------------------------------------------------------------------------
# Add any settings specific to the development environment
TEST_MODE = False # Example setting

# Django Rest Framework Settings
# ------------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        # Add SessionAuthentication if you need browser-based API access
        # 'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        # Default to authenticated users, can be overridden per view
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# drf-spectacular settings (if not already defined)
SPECTACULAR_SETTINGS = {
    'TITLE': 'MailMind API',
    'DESCRIPTION': 'API for the MailMind application',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False, # Schema served under /api/schema/
    # OTHER SETTINGS
}

# Sentry SDK (Optional, if used)
# ------------------------------------------------------------------------------
# import sentry_sdk
# from sentry_sdk.integrations.django import DjangoIntegration
# sentry_sdk.init(
#     dsn=env("SENTRY_DSN", default=None),
#     integrations=[DjangoIntegration()],
#     # Set traces_sample_rate to 1.0 to capture 100%
#     # of transactions for performance monitoring.
#     # We recommend adjusting this value in production.
#     traces_sample_rate=1.0,
#     # If you wish to associate users to errors (assuming sentry_sdk>=0.5.0)
#     send_default_pii=True
# )

EMAIL_USE_LOCALTIME = True
EMAIL_DEBUG = True
smtplib.SMTP.debuglevel = 1
