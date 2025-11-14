"""
URL configuration for lost_and_found_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from core.api import router as core_router # <--- This import must find 'router'

# 1. Import your API router
from core.api import router as core_router

# 2. Initialize the NinjaAPI
api = NinjaAPI(
    title="Lost and Found Smart Match API",
    description="API for reporting and matching lost and found items on campus."
)

# 3. Add the core router to the main API instance
api.add_router("/core", core_router)


urlpatterns = [
    # Django Admin Panel
    path("admin/", admin.site.urls),
    
    # Django Ninja API entry point
    path("api/", api.urls),
]