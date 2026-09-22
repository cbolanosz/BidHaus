"""Django settings for the BidHaus project.

Every value that changes between machines is read from an environment variable,
so the repository never carries a secret or an absolute path.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Credentials live in a .env that Git ignores, never in the repository. A real
# environment variable wins over the file, so a server can set one without
# editing anything, and .env.example lists every key this file expects.
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("BIDHAUS_SECRET_KEY", "insecure-key-for-local-development")
DEBUG = os.environ.get("BIDHAUS_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.environ.get("BIDHAUS_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "accounts",
    "auctions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "bidhaus.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "bidhaus.wsgi.application"

# SQLite serialises writes with a database-level lock. IMMEDIATE takes that lock
# when the transaction begins instead of when it first writes, which is what keeps
# two concurrent bids from failing halfway through (see CLAUDE.md 4.1).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("BIDHAUS_DATABASE_PATH", BASE_DIR / "db.sqlite3"),
        "OPTIONS": {
            "timeout": 20,
            "transaction_mode": "IMMEDIATE",
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
        },
        # The test database is a file, not the in-memory default: WAL mode and the
        # lock timeout above only exist on a file, and the bidding rules are tested
        # against concurrent writers.
        "TEST": {"NAME": BASE_DIR / "test_db.sqlite3"},
    }
}

AUTH_USER_MODEL = "accounts.User"

# Where @login_required sends a visitor who is not logged in yet (FR31).
LOGIN_URL = "accounts:log_in"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = os.environ.get("BIDHAUS_TIME_ZONE", "America/Bogota")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Identity documents never live under MEDIA_ROOT: nothing must be able to serve
# them by URL. Only an administrator reads them, through a view (DBR08).
IDENTITY_DOCUMENT_ROOT = os.environ.get(
    "BIDHAUS_IDENTITY_DOCUMENT_ROOT", BASE_DIR / "private-media"
)

# The mail service BidHaus hands its notifications to (FR09, FR10, FR11).
# Mail is sent for real: the notifications are part of the product, not a
# console demonstration. Credentials come from the .env; the defaults below
# only describe how to reach the provider, never who is sending.
EMAIL_BACKEND = os.environ.get(
    "BIDHAUS_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.environ.get("BIDHAUS_EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("BIDHAUS_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("BIDHAUS_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("BIDHAUS_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("BIDHAUS_EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_TIMEOUT = int(os.environ.get("BIDHAUS_EMAIL_TIMEOUT", "10"))

# Gmail rewrites a sender that is not the authenticated account, so the account
# itself is the sensible default rather than an address nobody owns.
DEFAULT_FROM_EMAIL = os.environ.get("BIDHAUS_DEFAULT_FROM_EMAIL") or EMAIL_HOST_USER

# Where this installation answers from. An email is read outside the browser
# that opened the site, so the links it carries have to be absolute.
SITE_URL = os.environ.get("BIDHAUS_SITE_URL", "http://127.0.0.1:8000")

# A notification that could not be sent is logged instead of raised, so the bid
# that caused it is never lost. This is what makes that line visible: without a
# handler it would only reach Python's fallback and be easy to miss.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "auctions.notifications": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        }
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Currency every amount in the database is expressed in.
CURRENCY = os.environ.get("BIDHAUS_CURRENCY", "COP")
