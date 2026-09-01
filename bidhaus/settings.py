"""Django settings for the BidHaus project.

Every value that changes between machines is read from an environment variable,
so the repository never carries a secret or an absolute path.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

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

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Currency every amount in the database is expressed in.
CURRENCY = os.environ.get("BIDHAUS_CURRENCY", "COP")
