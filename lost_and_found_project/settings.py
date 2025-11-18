import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# The location of your root URLconf (the main urls.py file)
ROOT_URLCONF = 'lost_and_found_project.urls'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# WARNING: KEEP THIS KEY SECRET!
SECRET_KEY = 'django-insecure-33%^8t_h#99t0a(1001-t!5h$b238n91t6@#e$b!d#91d' 
# NOTE: In a real project, you would generate a unique key 
# and load it from an environment variable (e.g., using python-dotenv).

# When DEBUG=True, ALLOWED_HOSTS can be empty or ['*'] for development.
# If DEBUG=False, it must contain domain names or IP addresses.
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    # Default Django Apps...
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    'rest_framework.authtoken',
    "core",  # <-- Your new app
]

# 2. Configure the MongoDB database connection using os.environ.get
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# 1. Add your custom User Model setting
AUTH_USER_MODEL = 'core.RegUser' 

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'