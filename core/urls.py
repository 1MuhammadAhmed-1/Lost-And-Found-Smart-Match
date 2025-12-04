# core/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views   # ← ADD THIS LINE
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('found/', views.found_list, name='found_list'),
    path('lost/', views.lost_list, name='lost_list'),
    path('report-found/', views.report_found, name='report_found'),
    path('report-lost/', views.report_lost, name='report_lost'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('claim/<uuid:item_id>/', views.claim_item, name='claim_item'),
    path('api/smart-search/', views.smart_search_api, name='smart_search_api'),
]