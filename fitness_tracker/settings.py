import os
from pathlib import Path
from decouple import config
from dotenv import load_dotenv
from pathlib import Path


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file at the project root
load_dotenv(os.path.join(BASE_DIR, '.env'))

# ------------------ SECURITY ------------------
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='your-very-insecure-default-key-change-this-in-production!')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool) # Cast to bool to interpret "False" as boolean False

# Allowed hosts for your Django application.
# *** SYNTAX FIX APPLIED HERE: Replaced non-breaking space after ['*'] ***
ALLOWED_HOSTS = ['*']  # Consider changing this to something more specific for production.

# ------------------ APPLICATIONS ------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'corsheaders',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles', # Essential for serving static files
    'core',                       # Your core application
    'django.contrib.humanize',    # Useful for human-readable numbers/dates
]

# ------------------ MIDDLEWARE ------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware', # Add this after SecurityMiddleware
    'django.middleware.security.SecurityMiddleware',
]

ROOT_URLCONF = 'fitness_tracker.urls' # Your project's main URL configuration

# ------------------ TEMPLATES ------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # DIRS specifies a list of directories where Django should look for template files
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        # APP_DIRS tells Django to look for a 'templates' folder inside each installed app.
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'fitness_tracker.wsgi.application'

# ------------------ DATABASE ------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# ------------------ AUTHENTICATION ------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'login' # URL for the login page
LOGOUT_REDIRECT_URL = 'login' # Where to redirect after logout

# ------------------ INTERNATIONALIZATION ------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata' # Set this to your local timezone
USE_I18N = True # Enable Django's internationalization system
USE_TZ = True # Enable timezone support

# ------------------ STATIC FILES (CSS, JS, Images like workout GIFs, default profile pic) ------------------
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'), # Your project-level static directory
    os.path.join(BASE_DIR, 'core', 'static'), # Explicitly tell Django to look in core/static/
]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


# ------------------ MEDIA FILES (User Uploaded Content like profile images) ------------------
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ------------------ DEFAULT PRIMARY KEY FIELD TYPE ------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ------------------ EMAIL (if used) ------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Fallback email backend for local debugging
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'no-reply@example.com'


# ------------------ GEMINI API CONFIGURATION ------------------
# 1. Gemini API key (from environment variable or keep as string during local testing)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")

# 2. Gemini model ID (change if you use another model)
GEMINI_MODEL_ID = "gemini-2.5-flash"

# 3. Full API endpoint URL (do NOT include ?key= here)
GEMINI_MODEL_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_ID}:generateContent"

# ------------------ TWILIO CONFIGURATION ------------------
# *** HARDCODED VALUES USED TO OVERRIDE CONFIG() AND RESOLVE CONFLICTS ***
TWILIO_ACCOUNT_SID = 'ACa69d18cb99152a5981b25be4ebc6217c'
TWILIO_AUTH_TOKEN = '70eb904ca27a051ec6d5f3e32a392a51'
TWILIO_PHONE_NUMBER = '+12602311267'