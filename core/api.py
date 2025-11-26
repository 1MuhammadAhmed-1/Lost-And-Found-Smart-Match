import os
import time 
from ninja import Router, Schema, Field, NinjaAPI
from ninja.security.base import AuthBase 
from ninja.errors import HttpError, ConfigError
from typing import List, Optional
from django.shortcuts import get_object_or_404
from .models import FoundItem, LostClaim, RegUser 
from ninja.orm import ModelSchema
import uuid 
import datetime 
from core import ai_tools 
from google import genai
from ninja.orm import ModelSchema

# --- Authentication Class (Unchanged) ---
class GlobalAuth(AuthBase):
    openapi_type: str = "apiKey"
    param_name: str = "Authorization"
    
    def authenticate(self, request):
        from rest_framework.authtoken.models import Token
        
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        source = "META"
        
        if not auth_header:
            auth_header = request.headers.get(self.param_name) 
            source = "headers"
            
        if not auth_header:
            return None
        
        try:
            auth_header_normalized = auth_header.strip() 
            scheme, separator, token = auth_header_normalized.partition(' ')
            
            if not token:
                return None
            
            if scheme.lower() != 'token':
                return None
        except Exception:
            return None

        try:
            token_obj = Token.objects.get(key=token)
            return token_obj.user
        except Token.DoesNotExist:
            return None

    def __call__(self, request):
        return self.authenticate(request)

# --- Gemini Client Setup ---

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

try:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
        
    client = genai.Client(api_key=GEMINI_API_KEY)
    
except Exception as e:
    print(f"CRITICAL ERROR: Failed to initialize Gemini Client. {e}")
    client = None

AVAILABLE_TOOLS = {
    "report_found_item": ai_tools.report_found_item,
    "search_for_matches": ai_tools.search_for_matches,
    "claim_found_item_by_id": ai_tools.claim_found_item_by_id,
}

MODEL_NAME = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = (
    "You are a helpful Lost and Found assistant. "
    "Your goal is to help users report found items, search for lost items, or claim items. "
    "ALWAYS use the provided tools for database interactions, never guess. "
    "CRITICAL RULE 1: When presenting a found item to the user, you **MUST** explicitly state and display the **FULL 32-character Item ID** you received from the tool output. **DO NOT** shorten or truncate the Item ID in the conversation. "
    "CRITICAL RULE 2: When the user confirms an item, you **MUST** pass the **FULL 32-character Item ID** to the 'claim_found_item_by_id' tool. "
    "CRITICAL NEW RULE 3: If the user provides details for a lost item and you search but they reject the one and only match, **immediately pivot to offering to create a new Lost Claim** with the details they provided, rather than insisting on the rejected match."
)

router = Router(auth=GlobalAuth())

# -----------------
# Pydantic Schemas (Unchanged)
# -----------------

class RegUserIn(Schema):
    username: str
    password: str
    email: str = Field(..., example="john.doe@example.com") 
    
class RegUserOut(ModelSchema):
    class Meta:
        model = RegUser 
        fields = ('id', 'username', 'email', 'date_joined', 'last_login') 

class FoundItemIn(Schema):
    item_name: str
    description: str
    location_found: str
    contact_email: str 

class FoundItemOut(ModelSchema):
    class Meta:
        model = FoundItem
        fields = ('item_id', 'item_name', 'description', 'location_found', 'date_found', 'status', 'contact_email')
    
class LostClaimIn(Schema):
    item_name: str
    description: str
    location_lost: str = Field(alias='approx_location_lost') 
    contact_email: str

class LostClaimOut(ModelSchema):
    class Meta:
        model = LostClaim
        fields = ('claim_id', 'item_name', 'description', 'approx_location_lost', 'date_lost', 'is_matched', 'contact_email')

class HistoryElement(Schema):
    role: str 
    text: str

class ChatIn(Schema):
    message: str
    history: List[HistoryElement]
    
class ChatOut(Schema):
    response: str

# -----------------
# API Endpoints (Unchanged paths from last fix)
# -----------------

## 1. Endpoint to register a new found item
@router.post("/core/found_items", response={201: FoundItemOut,})
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
    return found_item 

## 2. Endpoint to register a new lost claim
@router.post("/core/lost_claims", response={201: LostClaimOut})
def create_lost_claim(request, payload: LostClaimIn):
    
    lost_claim = LostClaim.objects.create(
        item_name=payload.item_name,
        description=payload.description,
        approx_location_lost=payload.location_lost, 
        contact_email=payload.contact_email,
        is_matched=False,
        owner=request.user 
    )
    return lost_claim

## 3. Endpoint to retrieve all found items
@router.get("/core/found_items_list", response=List[FoundItemOut])
def list_found_items(request):
    """Retrieves a list of all reported found items."""
    items = FoundItem.objects.all()
    return items

## 4. Endpoint to retrieve all lost claims
@router.get("/core/lost_claims_list", response=List[LostClaimOut])
def list_lost_claims(request):
    """Retrieves a list of all reported lost claims."""
    claims = LostClaim.objects.all()
    return claims

## 5. Endpoint to handle the claiming of a found item
@router.post("/core/claim_item/{found_item_id}", response={200: FoundItemOut})
def claim_item(request, found_item_id: uuid.UUID):
    """Sets the status of a FoundItem to 'CLAIMED'."""
    item_to_claim = get_object_or_404(FoundItem, item_id=found_item_id)

    if item_to_claim.status == 'PENDING':
        item_to_claim.status = 'CLAIMED'
        item_to_claim.save()
        return item_to_claim 
    elif item_to_claim.status in ['CLAIMED', 'RETURNED']:
        raise HttpError(409, f"Item is already marked as {item_to_claim.status}")
    else:
        raise HttpError(400, f"Cannot claim item with current status: {item_to_claim.status}")

## 6. Endpoint to register a new user
@router.post("/core/register", response={201: RegUserOut, 400: Optional[dict]}, auth=None)
def register_user(request, payload: RegUserIn):
    """Creates a new RegUser and securely hashes the password."""
    try:
        if RegUser.objects.filter(username=payload.username).exists():
            return 400, {"message": "Username already taken."}
        if RegUser.objects.filter(email=payload.email).exists():
            return 400, {"message": "Email already registered."}

        user = RegUser.objects.create_user(
            username=payload.username,
            email=payload.email,
            password=payload.password 
        )
        return 201, user 
        
    except Exception as e:
        raise HttpError(500, f"Registration failed due to unexpected error: {e}")

# --- AI Call Helper Function with Retry Logic (Unchanged) ---
def call_gemini_with_retry(contents, config, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model=MODEL_NAME,
                contents=contents, 
                config=config,
            )
        except genai.errors.APIError as e:
            print(f"[GEMINI ERROR] Attempt {attempt + 1}: API call failed. {e}")
            if attempt < max_retries - 1:
                # Exponential backoff: 2s, 4s, 8s
                delay = 2 ** (attempt + 1)
                time.sleep(delay)
                continue
            else:
                raise 
        except Exception as e:
             raise e

## 7. AI Chat Endpoint
@router.post("/core/chat", response=ChatOut)
def chat_with_llm(request, payload: ChatIn):
    """Handles the user chat interaction using the Gemini model and its tools."""
    
    if not client:
        # Client not initialized (API Key missing)
        return {"response": "System maintenance: AI client is currently unavailable due to missing API key."}
        
    try:
        # Convert Pydantic history into Gemini Content objects
        chat_history = [
            genai.types.Content(
                role=item.role,
                parts=[genai.types.Part(text=item.text)]
            ) for item in payload.history
        ]

        # Append the new user message
        chat_history.append(
            genai.types.Content(
                role="user", 
                parts=[genai.types.Part(text=payload.message)] 
            )
        )
        
        config = genai.types.GenerateContentConfig(
            tools=list(AVAILABLE_TOOLS.values()),
            system_instruction=SYSTEM_INSTRUCTION 
        )

        # First AI Call
        response = call_gemini_with_retry(chat_history, config)

        if response.function_calls:
            function_call = response.function_calls[0]
            function_name = function_call.name
            tool_function = AVAILABLE_TOOLS.get(function_name)
            
            if tool_function:
                kwargs = dict(function_call.args)
                
                # Execute the tool function
                tool_output = tool_function(**kwargs) 
                
                # Append the AI's function call and the tool's output to the history
                chat_history.append(response.candidates[0].content)
                chat_history.append(
                    genai.types.Content(
                        role="tool",
                        parts=[genai.types.Part(text=tool_output)],
                    )
                )

                # Second AI Call to summarize tool output
                final_response = call_gemini_with_retry(chat_history, config)

                return {"response": final_response.text}
            
            else:
                return {"response": f"AI requested an unknown tool: {function_name}"}

        # If no function call, return the response directly
        return {"response": response.text}

    except HttpError as he:
        raise he
    except genai.errors.APIError as e:
        # Catch GenAI specific errors (e.g., failed after retries)
        print(f"Final Gemini API Error: {e}")
        # The user's requested error message
        return {"response": "Sorry, I ran into an error connecting to the AI service."}
    except Exception as e:
        # Catch all other internal errors (e.g., Python serialization, tool execution failure)
        print(f"Internal Chat Error: {e}")
        return {"response": "Sorry, I ran into an error connecting to the AI service."}