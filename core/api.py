from ninja import Router, Schema, Field
from typing import List
from django.shortcuts import get_object_or_404
from .models import FoundItem, LostClaim, RegUser # Removed RegUser import if not used globally
from ninja.orm import ModelSchema # <<< NEW IMPORT

import uuid 
import datetime 

# Initialize the Router
router = Router()

# -----------------
# Pydantic Schemas
# -----------------

# core/api.py (Pydantic Schemas Section)

# Schema for the data required to create a FoundItem
class FoundItemIn(Schema):
    item_name: str
    description: str
    location_found: str
    contact_email: str # Mapped to the new field in models.py

# Schema for the data returned in the response
# Refactored Output Schema using ModelSchema
class FoundItemOut(ModelSchema):
    class Meta:
        model = FoundItem
        fields = ('item_id', 'item_name', 'description', 'location_found', 'date_found', 'status', 'contact_email')
    
# Schema for the data required to create a LostClaim
class LostClaimIn(Schema):
    item_name: str
    description: str
    location_lost: str = Field(alias='approx_location_lost') # Alias for model field
    contact_email: str
    # NOTE: You will need to handle the 'owner' field (ForeignKey) separately

# Schema for the data returned in the LostClaim response
class LostClaimOut(ModelSchema):
    class Meta:
        model = LostClaim
        fields = ('claim_id', 'item_name', 'description', 'approx_location_lost', 'date_lost', 'is_matched', 'contact_email')

# -----------------
# API Endpoints
# -----------------
    
# core/api.py (API Endpoints Section)

# core/api.py (API Endpoints Section)

# 1. Endpoint to register a new found item
# core/api.py (create_found_item function)

# 1. Endpoint to register a new found item
@router.post("/found_items", response={201: FoundItemOut})
def create_found_item(request, payload: FoundItemIn):
    reporter = request.user if request.user.is_authenticated else None
    
    found_item = FoundItem.objects.create(
        item_name=payload.item_name,
        description=payload.description,
        location_found=payload.location_found,
        contact_email=payload.contact_email,
        status='PENDING', 
        date_found=datetime.date.today(),
        reported_by=reporter 
    )
    # ModelSchema automatically handles the serialization of the model instance
    return 201, found_item # Return the model instance directly!
# ... rest of the API endpoints remain the same ...

# 2. Endpoint to register a new lost claim
@router.post("/lost_claims", response={201: LostClaimOut})
def create_lost_claim(request, payload: LostClaimIn):
    # This requires a logged-in user to set the 'owner' ForeignKey, which is NOT NULL.
    # We use request.user for this, which is available in Django views.
    
    # NOTE: You will need to ensure a user is logged in for this to work in a real setup.
    if not request.user.is_authenticated:
         # Replace with proper HTTP response in a real app
         raise Exception("Authentication required for LostClaim")
         
    lost_claim = LostClaim.objects.create(
        item_name=payload.item_name,
        description=payload.description,
        approx_location_lost=payload.location_lost,
        contact_email=payload.contact_email,
        is_matched=False,
        date_lost=datetime.date.today(),
        owner=request.user # CRITICAL: Sets the required owner field
    )
    return 201, lost_claim

# 3. Endpoint to retrieve all found items
@router.get("/found_items", response=List[FoundItemOut])
def list_found_items(request):
    """
    Retrieves a list of all reported found items.
    """
    # Query the database for all FoundItem objects
    items = FoundItem.objects.all()
    # Django Ninja automatically uses FoundItemOut schema to serialize the list
    return items

# 4. Endpoint to retrieve all lost claims
@router.get("/lost_claims", response=List[LostClaimOut])
def list_lost_claims(request):
    """
    Retrieves a list of all reported lost claims.
    """
    # Query the database for all LostClaim objects
    claims = LostClaim.objects.all()
    # Django Ninja automatically uses LostClaimOut schema to serialize the list
    return claims