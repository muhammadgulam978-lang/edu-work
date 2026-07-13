"""
Django settings for sms project.
"""

import os
from pathlib import Path

from dotenv import load_dotenv



BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file if exists
load_dotenv(dotenv_path=os.path.join(BASE_DIR, '.env'))

# SECURITY
SECRET_KEY = 'django-insecure-1u@4sktn_vg=d#+u)*f^v9ut(jt&0&4g@s9_)-$d-l&mema=ei'
DEBUG = True

# Allowed hosts (Render URL + localhost)
ALLOWED_HOSTS = [
    'sms-2hxg.onrender.com', '127.0.0.1', 'localhost'
    ]
CSRF_TRUSTED_ORIGINS = [  "https://sms-2hxg.onrender.com" ]
# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "phonenumber_field",
    "login",
    "parent_dashboard",
    "teacher_dashboard",
    "student_profile",
    "admin_panel",
    "widget_tweaks",
    "exam_system",
    'django_apscheduler',
    'edupilot_core',
    'ai_tutor',
    
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "sms.urls"



TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            os.path.join(BASE_DIR, "login", "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                'teacher_dashboard.context_processors.lms_sidebar_context',
                'admin_panel.context_processors.user_permissions',
                'ai_tutor.context_processors.ai_tutor_fab',
            ],
        },
    },
]

WSGI_APPLICATION = "sms.wsgi.application"


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'edu_pilot_new',
        'USER': 'GM123',
        'PASSWORD': 'GM123',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise recommended storage
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

#Media files (Render does not persist; use S3 for production ideally)
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media/")

# Email backend
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'isram.amin12@gmail.com'
EMAIL_HOST_PASSWORD = 'mrdx ygfp qqqc munh'

# Authentication redirects
LOGIN_URL = "/login/"
LOGOUT_REDIRECT_URL = '/logout/'
LOGIN_REDIRECT_URL = "/admin_panel/dashboard/"


# ================= EMAIL SETTINGS =================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

EMAIL_HOST_USER = 'areebanazkhan44@gmail.com'

# Gmail App Password
EMAIL_HOST_PASSWORD = 'vkwd aztg ebhf kixz' 

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Debug
EMAIL_TIMEOUT = 30


# Groq API KEY

GROQ_API_KEY = os.getenv("GROQ_API_KEY")  

# AI Tutor LLM configuration
AI_TUTOR_PROVIDER = os.getenv("AI_TUTOR_PROVIDER", "openai")
AI_TUTOR_MODEL = os.getenv("AI_TUTOR_MODEL", "gpt-5.6-terra")
AI_TUTOR_FALLBACK_MODEL = os.getenv("AI_TUTOR_FALLBACK_MODEL", "llama-3.3-70b-versatile")
AI_TUTOR_API_KEY = os.getenv("AI_TUTOR_API_KEY", "")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
