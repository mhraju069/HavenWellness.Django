
import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()
from corsheaders.defaults import default_headers
try:
    import firebase_admin
    from firebase_admin import credentials
except ImportError:
    firebase_admin = None
    credentials = None

DEBUG = True
ALLOWED_HOSTS = ['*']
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://.*$",
]
SECRET_KEY = os.getenv("SECRET_KEY", "83n^4v$htzuagc^ece+qzqkb9+jwp0o%(flpbu)_)izs84np0n")
BASE_DIR = Path(__file__).resolve().parent.parent
CORS_ALLOW_HEADERS = list(default_headers) + [
    'ngrok-skip-browser-warning',
    'bypass-tunnel-reminder',
    'lang',
    'accept-language',
    'authorization',
]
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760 * 400 # 400MB
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()
]

# Ensure URLs/images generated behind reverse proxy use HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

STRIPE_TEST_PUBLIC_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_TEST_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_LIVE_PUBLIC_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_LIVE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_LIVE_MODE = False
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"
DJSTRIPE_USE_NATIVE_JSONFIELD = True

INSTALLED_APPS = [
    'modeltranslation',
    'unfold',
    'channels',
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_filters',
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'djstripe',
    'accounts',
    'services',
    'bookings',
    'others',
    'dashboards',
    'payments',
    'notifications'
]

LANGUAGES = (
    ('en', 'English'),
    ('nl', 'Dutch'),
    ('de', 'German'),
)

MODELTRANSLATION_DEFAULT_LANGUAGE = 'en'
MODELTRANSLATION_FALLBACK_LANGUAGES = ('en', 'nl', 'de')

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    'core.middleware.ForceHttpsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'core.middleware.LanguageMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ASGI_APPLICATION = 'core.asgi.application'
WSGI_APPLICATION = "core.wsgi.application"

REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [
                {
                    "address": f"redis://{REDIS_HOST}:{REDIS_PORT}",
                    "socket_timeout": None,
                }
            ],
        },
    },
}

# Celery Configuration
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

try:
    from celery.schedules import crontab
    CELERY_BEAT_SCHEDULE = {
        'send-24h-booking-reminders': {
            'task': 'notifications.tasks.send_24h_booking_reminders',
            'schedule': crontab(minute=0),  # Runs every hour at minute 0
        },
    }
except ImportError:
    CELERY_BEAT_SCHEDULE = {}



if os.getenv('USE_PSQL', 'False').lower() in ('true', '1'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'haven_wellness'),
            'USER': os.getenv('DB_USER', 'maggy'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'maggy@321'),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }
else: 
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'

USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static",]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.CursorPagination',
    'PAGE_SIZE': None,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Haven Wellness API',
    'DESCRIPTION': 'Comprehensive REST API documentation for Haven Wellness services, bookings, user accounts, dashboards, payments, and notifications.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/',
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayRequestDuration': True,
        'filter': True,
    },
}


SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30)
}


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 465))
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "True").lower() in ("true", "1")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False").lower() in ("true", "1")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")


# Firebase Admin SDK
try:
    key_path = BASE_DIR / "firebase-key.json"
    if credentials and key_path.exists() and key_path.stat().st_size > 0:
        cred = credentials.Certificate(str(key_path))
        firebase_admin.initialize_app(cred)
except Exception as e:
    print("Firebase Admin SDK initialization failed:", e)