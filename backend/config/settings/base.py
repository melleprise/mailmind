import environ
import multiprocessing
from pathlib import Path # Import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR should point to the backend directory containing manage.py
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

# Attempt to read .env file - this might be redundant if Docker Compose env_file works
# READ_DOT_ENV_FILE = env.bool('DJANGO_READ_DOT_ENV_FILE', default=False)
# if READ_DOT_ENV_FILE:
#     env.read_env(str(BASE_DIR / ".env")) # Adjust path if your .env is elsewhere

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="!!!SET DJANGO_SECRET_KEY!!!", # Set a default for easier setup
)

# URL of the frontend application (required for verification emails, etc.)
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:8080") # Default auf Dev-URL

DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # "django.contrib.humanize", # Handy template tags
    "django.contrib.admin",
    "django.forms",
]
THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_bootstrap5",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "allauth.socialaccount",
    "django_celery_beat",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "drf_spectacular",
    "django_q",
    "channels",
    "django_prometheus",
]

LOCAL_APPS = [
    "mailmind", # Add the main mailmind app
    "mailmind.core",
    # "mailmind.users", # Assuming user functionality is in core or elsewhere
    # "mailmind.emails", # App directory doesn't seem to exist
    "mailmind.imap", # Corrected from imap_connections
    "mailmind.ai",
    "mailmind.prompt_templates",
    # "mailmind.notifications", # App directory doesn't seem to exist
    "knowledge", 
    "mailmind.api", # Hinzufügen der API-App
    "mailmind.freelance", # Hinzufügen der Freelance-App
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend', # Wieder einkommentiert für Admin-Login

    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
)
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "core.User"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
# LOGIN_REDIRECT_URL = "users:redirect"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
# LOGIN_URL = "account_login"

# django-allauth Configuration
# ------------------------------------------------------------------------------
ACCOUNT_AUTHENTICATION_METHOD = "email" # Use email for login
ACCOUNT_EMAIL_REQUIRED = True           # Email is mandatory
ACCOUNT_USERNAME_REQUIRED = False       # Username is not needed
ACCOUNT_USER_MODEL_USERNAME_FIELD = None  # Explicitly state no username field
ACCOUNT_EMAIL_VERIFICATION = "none"     # Set to "mandatory" or "optional" later
ACCOUNT_ADAPTER = "allauth.account.adapter.DefaultAccountAdapter"
# SOCIALACCOUNT_ADAPTER = "mailmind.users.adapters.SocialAccountAdapter" # If you have social login
SITE_ID = 1 # Required by allauth

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = "admin/"

# CORS Configuration
# ------------------------------------------------------------------------------
# Allow requests from the frontend development server
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8080", # Development frontend
    # Add other origins if needed (e.g., production frontend URL)
]
# If you need to send cookies or authorization headers:
CORS_ALLOW_CREDENTIALS = True
# Optional: Allow specific headers if needed beyond defaults
# CORS_ALLOW_HEADERS = list(default_headers) + ['my-custom-header']
# Optional: Allow specific methods if needed beyond defaults (GET, POST, HEAD, OPTIONS, PUT, PATCH, DELETE)
# CORS_ALLOW_METHODS = list(default_methods) + ['CONNECT']

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
    "mailmind.core.middleware.LogHeadersMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

# SECURITY
# ------------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
# Tell Django to trust the X-Forwarded-Proto header from Caddy (or other proxy)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG will be overridden in development.py and production.py
DEBUG = env.bool("DJANGO_DEBUG", False)

# ASGI & Channels Configuration
# ------------------------------------------------------------------------------
ASGI_APPLICATION = "config.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            # Use the same Redis defined in docker-compose
            "hosts": [("redis", 6379)], 
        },
    },
}

Q_CLUSTER = {
    'name': 'mailmind-dev',
    'workers': multiprocessing.cpu_count() * 2 + 1,  # Anzahl der Worker-Prozesse
    'recycle': 500,  # Maximale Anzahl von Tasks pro Worker, bevor er neu gestartet wird
    'timeout': 600,  # Timeout für Tasks in Sekunden (10 Minuten)
    'retry': 720, # Erhöht von 660, um einen größeren Puffer zu Timeout zu haben
    'compress': True,
    'save_limit': 250,
    'queue_limit': 500,
    'cpu_affinity': 1,
    'label': 'Django Q',
    'redis': {
        'host': env("REDIS_HOST", default="redis"),
        'port': env.int("REDIS_PORT", default=6379),
        'db': env.int("REDIS_DB_Q", default=0),
    }
} 

# URLs
# ------------------------------------------------------------------------------
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
# Ensure ASGI_APPLICATION points to the correct location
ASGI_APPLICATION = "config.asgi.application" 

# Default primary key field type
# https://docs.djangoproject.com/en/dev/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(BASE_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [str(BASE_DIR / "static")] # Optional: if you have project-level static files
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(BASE_DIR / "media")
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/" 