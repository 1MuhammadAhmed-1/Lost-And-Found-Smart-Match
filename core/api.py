from ninja import Router, Schema, Field, NinjaAPI
from ninja.security import HttpBearer
from typing import List
from django.shortcuts import get_object_or_404
from .models import FoundItem, LostClaim, RegUser # Removed RegUser import if not used globally
from ninja.orm import ModelSchema
import uuid 
import datetime 
from core import ai_tools
from google import genai
from ninja.orm import ModelSchema

class GlobalAuth(HttpBearer):
    def authenticate(self, request, token):
        from rest_framework.authtoken.models import Token
        try:
            token_obj = Token.objects.get(key=token)
            return token_obj.user
        except Token.DoesNotExist:
            return None

# Initialize the Gemini Client
try:
    client = genai.Client()
except Exception as e:
    print(f"ERROR: Failed to initialize Gemini Client. Check GEMINI_API_KEY. {e}")
    client = None

# Mapping of tool function names (strings) to actual Python functions (objects)
# This is how the model calls the right tool
AVAILABLE_TOOLS = {
    "report_found_item": ai_tools.report_found_item,
    "search_for_matches": ai_tools.search_for_matches,
    "claim_found_item_by_id": ai_tools.claim_found_item_by_id,
}

# The model to use for chat
MODEL_NAME = "gemini-2.5-flash"

# Initialize the Router
router = Router(auth=GlobalAuth())

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

# Schema for the chat input
class ChatIn(Schema):
    message: str
    
# Schema for the chat output
class ChatOut(Schema):
    response: str

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
    # request.user is guaranteed to be a RegUser instance if logged in, otherwise None (handled by null=True)
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
    return 201, found_item

# 2. Endpoint to register a new lost claim
@router.post("/lost_claims", response={201: LostClaimOut})
def create_lost_claim(request, payload: LostClaimIn):
    # AUTH IS NOW HANDLED BY THE ROUTER: request.user is guaranteed to be a RegUser instance
    
    lost_claim = LostClaim.objects.create(
        item_name=payload.item_name,
        description=payload.description,
        approx_location_lost=payload.location_lost,
        contact_email=payload.contact_email,
        is_matched=False,
        date_lost=datetime.date.today(),
        owner=request.user # CRITICAL: Correctly links the user
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

# 5. Endpoint to handle the claiming of a found item
@router.post("/claim_item/{found_item_id}", response={200: FoundItemOut})
def claim_item(request, found_item_id: uuid.UUID):
    """
    Sets the status of a FoundItem to 'CLAIMED'.
    This assumes ownership has been manually verified or matched via AI.
    """
    
    # --- Authentication Check (Crucial for a real system) ---
    # For a production system, you'd check if the request.user is authorized
    # to perform this action (e.g., a staff admin or the verified owner).
    if not request.user.is_authenticated:
        # In a production setting, you'd raise a 401 Unauthorized exception
        # For simplicity now, we'll allow it if the user is not authenticated,
        # but in a real app, this should only be done by authorized personnel.
        pass

    # 1. Retrieve the Found Item or raise 404
    # We use get_object_or_404, which requires the get_object_or_404 import
    # which is already in your file.
    item_to_claim = get_object_or_404(FoundItem, item_id=found_item_id)

    # 2. Update the status
    if item_to_claim.status == 'PENDING':
        item_to_claim.status = 'CLAIMED'
        item_to_claim.save()
        return 200, item_to_claim
    elif item_to_claim.status in ['CLAIMED', 'RETURNED']:
        # Return the item status but perhaps a different message or status code
        # We can return a specific HTTP status code like 409 Conflict if Django Ninja supports it
        # For simplicity, we just return the item with a message in the description
        raise Exception(f"Item is already marked as {item_to_claim.status}")
    else:
        # Default case for other statuses like DISPOSED
        raise Exception(f"Cannot claim item with current status: {item_to_claim.status}")



# core/api.py

# ... existing code ...

@router.post("/chat", response=ChatOut)
def chat_with_llm(request, payload: ChatIn):
    """
    Handles conversational requests, leveraging Gemini's Function Calling
    to interact with the database using defined tools.
    """
    if not client:
        return {"response": "System maintenance: AI client is currently unavailable."}
        
    try:
        # 1. Start the conversation history with the user's message
        # CORRECTED: Use Part constructor with explicit 'text' keyword argument
        chat_history = [
            genai.types.Content(
                role="user", 
                parts=[genai.types.Part(text=payload.message)] # <<< FIX 1
            )
        ]
        
        # 2. Configure the model call with the available tools
        config = genai.types.GenerateContentConfig(
            tools=list(AVAILABLE_TOOLS.values())
        )

        # 3. Call the model and manage the multi-step process
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=chat_history,
            config=config,
        )

        # 4. Check if the model decided to call a function/tool
        if response.function_calls:
            function_call = response.function_calls[0]
            function_name = function_call.name
            tool_function = AVAILABLE_TOOLS.get(function_name)
            
            if tool_function:
                # 5. Execute the actual Python function (database tool)
                kwargs = dict(function_call.args)
                tool_output = tool_function(**kwargs)
                
                # 6. Send the tool output back to the model for a conversational response
                chat_history.append(response.candidates[0].content)
                # CORRECTED: Use Part constructor with explicit 'text' keyword argument
                chat_history.append(
                    genai.types.Content(
                        role="tool",
                        parts=[genai.types.Part(text=tool_output)], # <<< FIX 2
                    )
                )

                # 7. Final call to get the conversational response
                final_response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=chat_history,
                )
                return {"response": final_response.text}
            
            else:
                return {"response": f"AI requested an unknown tool: {function_name}"}

        # 8. If no function call, return the model's direct response
        return {"response": response.text}

    except Exception as e:
        return {"response": f"An unexpected error occurred during the AI process. Error: {e}"}