# lost_and_found_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

# ←←← THIS IS YOUR NINJA API INSTANCE (you already had this in your old code)
from ninja import NinjaAPI
from core.api import router as core_router  # your existing API router

api = NinjaAPI()               # ← You already had this
api.add_router("/", core_router)   # ← You already had this

urlpatterns = [
    path('admin/', admin.site.urls),

    # YOUR EXISTING NINJA API — FIXED LINE ↓
    path("api/ninja/", api.urls),                    # ← FIXED!

    # Token auth (you already use this)
    path('api/token-auth/', include('rest_framework.urls')),

    # OUR NEW BEAUTIFUL TEMPLATE VIEWS
    path('', include('core.urls')),   # ← This gives you the stunning frontend
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)