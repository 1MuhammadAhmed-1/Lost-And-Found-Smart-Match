# core/admin.py (TEMPORARY MINIMAL VERSION)

from django.contrib import admin
from .models import RegUser, FoundItem, LostClaim

# Just register the models without any custom list configuration
admin.site.register(RegUser)
admin.site.register(FoundItem)
admin.site.register(LostClaim)