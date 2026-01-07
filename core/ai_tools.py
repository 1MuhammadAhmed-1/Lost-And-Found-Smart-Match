# core/ai_tools.py
from core.models import FoundItem, LostClaim, RegUser
from datetime import date
from fuzzywuzzy import fuzz 
import uuid

# --- 1. TOOL TO REPORT A FOUND ITEM ---
def report_found_item(item_name: str, description: str, location_found: str, contact_email: str) -> str:
    """
    Records a newly found item in the database. 
    Call this when a user reports finding an item.
    
    Arguments MUST be extracted from the user's conversational message.
    """
    try:
        # NOTE: reported_by is omitted here for simplicity, assuming null=True
        FoundItem.objects.create(
            item_name=item_name,
            description=description,
            location_found=location_found,
            contact_email=contact_email,
            status='PENDING',
            date_found=date.today(),
        )
        return f"SUCCESS: Found item '{item_name}' reported and saved. Thank the user and confirm the location."
    except Exception as e:
        return f"ERROR: Failed to save found item. Database error: {e}"

# --- 2. TOOL TO SEARCH FOR MATCHES (The Smart Match Logic) ---
def search_for_matches(query: str, location: str = None) -> str:
    potential_matches = FoundItem.objects.filter(status='PENDING')
    matches = []
    full_query = f"{query} {location or ''}".strip().lower()
    
    # Simple list of common item types to prevent "Ring" matching "Phone"
    item_types = ['ring', 'phone', 'wallet', 'keys', 'bag', 'laptop', 'bottle']

    for item in potential_matches:
        item_name_lower = item.item_name.lower()
        item_text = f"{item.item_name} {item.description} {item.location_found}".lower()
        
        # 1. BRAINS: Check for Category Mismatch
        # If the user says 'phone' but the item is a 'ring', skip or penalize heavily
        category_mismatch = False
        for itype in item_types:
            if itype in full_query and itype not in item_text:
                category_mismatch = True
                break

        # 2. SCORING: Use token_set_ratio (better for partial overlaps)
        # token_sort_ratio is too sensitive to length; set_ratio is better for 'phone' matching 'blue iphone'
        score = fuzz.token_set_ratio(full_query, item_text)
        
        # 3. PENALTY: If categories definitely don't match, drop the score
        if category_mismatch:
            score -= 40 

        if score >= 50: 
            matches.append({
                "score": score,
                "item_id": item.item_id.hex,
                "name": item.item_name,
                "found_at": item.location_found,
            })
# --- 3. TOOL TO CLAIM AN ITEM (Similar to your API endpoint) ---
def claim_found_item_by_id(found_item_id_hex: str) -> str:
    """
    Marks a found item as 'CLAIMED' using its unique ID (first 8 characters are often enough).
    Only call after the user has confirmed they want to claim one of the items returned by search_for_matches.
    """
    try:
        # Find the item using the full UUID string
        item_id = uuid.UUID(found_item_id_hex)
        item = FoundItem.objects.get(item_id=item_id)
        
        if item.status == 'PENDING':
            item.status = 'CLAIMED'
            item.save()
            return f"SUCCESS: The item '{item.item_name}' has been successfully marked as CLAIMED and the process is complete. Thank the user for the claim."        
        else:
            return f"Item '{item.item_name}' is already marked as {item.status} and cannot be claimed."
            
    except FoundItem.DoesNotExist:
        return f"ERROR: No found item exists with ID starting with {found_item_id_hex[:8]}..."
    except Exception as e:
        return f"ERROR: Failed to process claim. Details: {e}"