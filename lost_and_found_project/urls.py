# lost_and_found_project/urls.py - FINAL CORRECTION

from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from core.api import router as core_router # Renamed to core_router for clarity
from rest_framework.authtoken import views

# 1. Initialize the NinjaAPI
api = NinjaAPI(
    # ... metadata
)

# 2. Add the core router to the main API instance, mounted at the root ("/")
# FIX: REMOVE the "/core" prefix here. 
# The endpoints in core/api.py must be changed to include the 'core/' prefix.
api.add_router("/", core_router) # <--- CHANGE THIS LINE


urlpatterns = [
    # Django Admin Panel
    path("admin/", admin.site.urls),
    
    # 1. Django Ninja API entry point
    # This exposes all paths defined in Ninja: /api/ninja/found_items/
    path("api/ninja/", api.urls), 

    # 2. Django REST Framework Token Authentication
    path('api/token-auth/', views.obtain_auth_token) 
]