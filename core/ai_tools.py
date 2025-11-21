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
    """
    Searches the database for found items that might match a user's lost item description. 
    Use this when a user is looking for a lost item.
    
    Returns a string summary of the top matching found items.
    """
    
    # Simple filtering for pending items
    potential_matches = FoundItem.objects.filter(status='PENDING')

    matches = []
    
    # Combine query components for a better match search
    full_query = f"{query} {location or ''}".strip().lower()
    
    for item in potential_matches:
        # Calculate matching score using name and description
        item_text = f"{item.item_name} {item.description} {item.location_found}".lower()
        
        # Use a high-quality ratio score for overall similarity
        combined_score = fuzz.token_sort_ratio(full_query, item_text)
        
        # Threshold for high confidence match
        if combined_score >= 50: 
            matches.append({
                "score": combined_score,
                "item_id": item.item_id.hex, # Use hex string for simple display
                "name": item.item_name,
                "found_at": item.location_found,
            })

    # Sort and take the top 3
    matches.sort(key=lambda x: x['score'], reverse=True)
    
    if not matches:
        return "No high-confidence matches were found in the system. Suggest the user submit a formal lost claim."
        
    result_strings = [
        # CRITICAL CHANGE: Return the full UUID for the LLM to use
        f"Match Score: {m['score']}%, Item: {m['name']} found at {m['found_at']} (Item ID: {m['item_id']})"
        for m in matches[:3]
    ]
    
    return "Potential Matches Found:\n" + "\n".join(result_strings) + "\n\nUser-facing ID is the first 8 characters (e.g., 908e545b...). When calling 'claim_found_item_by_id', ALWAYS use the complete 32-character FULL_ID provided above."

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