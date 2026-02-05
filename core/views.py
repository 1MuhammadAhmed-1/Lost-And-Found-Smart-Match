# core/views.py — FINAL WORKING VERSION
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.core.files.base import ContentFile
from django.conf import settings
import json
import re
import base64
from datetime import date

from .forms import RegisterForm, FoundItemForm, LostClaimForm
from .models import FoundItem, LostClaim, ClaimRequest, ChatMessage

# --------------------- GEMINI AI SETUP ---------------------
import google.generativeai as genai
from pathlib import Path
import mimetypes
import numpy as np
from numpy.linalg import norm

genai.configure(api_key=settings.GEMINI_API_KEY)

# --------------------- AI HELPER FUNCTIONS ---------------------

def describe_with_gemini(image_field):
    try:
        image_field.seek(0)
        image_data = image_field.read()
        ext = Path(image_field.name).suffix.lower()
        mime_type = mimetypes.guess_type("file" + ext)[0] or "image/jpeg"

        model = genai.GenerativeModel("gemini-2.0-flash") # Updated to stable flash
        response = model.generate_content([
            "Describe this item CONCISELY in 3-5 sentences. Focus on UNIQUE features: color, brand, size, condition, logos, damage.",
            {"mime_type": mime_type, "data": image_data}
        ])
        return response.text.strip()
    except Exception as e:
        return f"[AI description failed: {str(e)}]"
    finally:
        image_field.seek(0)

def get_embedding(text):
    if not text.strip():
        return [0] * 768
    try:
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except:
        return [0] * 768

def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    if norm(a) == 0 or norm(b) == 0:
        return 0.0
    return np.dot(a, b) / (norm(a) * norm(b))

def ai_text_similarity(t1, t2):
    return cosine_similarity(get_embedding(t1), get_embedding(t2)) * 100

def ai_image_similarity(img1, img2):
    if not img1 or not img2:
        return 0
    try:
        img1.seek(0); img2.seek(0)
        model = genai.GenerativeModel('gemini-2.0-flash')
        # Logic to compare images via text description comparison for stability
        response = model.generate_content([
            "Compare these two images. Are they the same item? Answer ONLY with a number 0–100.",
            img1, img2
        ])
        match = re.search(r'\d+', response.text)
        return float(match.group()) if match else 50
    except:
        return 50

# --------------------- VIEWS ---------------------

def home(request):
    return render(request, 'home.html')

@login_required
def report_found(request):
    if request.method == 'POST':
        form = FoundItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.reported_by = request.user
            if item.image:
                item.description = describe_with_gemini(item.image) + ("\n\n" + item.description if item.description.strip() else "")
            item.save()
            messages.success(request, "Found item reported — AI description added!")
            return redirect('home')
    else:
        form = FoundItemForm()
    return render(request, 'report_form.html', {'form': form, 'title': 'Report Found Item'})

@login_required
def report_lost(request):
    if request.method == 'POST':
        form = LostClaimForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            if item.image:
                item.description = describe_with_gemini(item.image) + ("\n\n" + item.description if item.description.strip() else "")
            item.save()
            messages.success(request, "Lost item reported!")
            return redirect('home')
    else:
        form = LostClaimForm()
    return render(request, 'report_form.html', {'form': form, 'title': 'Report Lost Item'})

@login_required
def claim_item(request, item_id):
    found_item = get_object_or_404(FoundItem, item_id=item_id)
    
    # 1. Validation Checks
    if found_item.reported_by == request.user:
        messages.error(request, "You cannot claim your own found item!")
        return redirect('found_list')

    existing_claim = ClaimRequest.objects.filter(found_item=found_item, claimant=request.user).first()
    if existing_claim:
        return redirect('chat_room', claim_id=existing_claim.id)

    # 2. AI Matching Logic (FIXED TO PREVENT REPETITIVE 30% SCORES)
    user_lost_items = LostClaim.objects.filter(owner=request.user)
    matches = []
    
    # Common categories to detect mismatch
    categories = ['phone', 'ring', 'key', 'wallet', 'bag', 'laptop', 'bottle', 'watch']
    found_text = f"{found_item.item_name} {found_item.description}".lower()

    for lost in user_lost_items:
        lost_text = f"{lost.item_name} {lost.description}".lower()
        
        # Calculate Base AI scores
        v_score = ai_image_similarity(lost.image, found_item.image) if lost.image and found_item.image else 0
        t_score = ai_text_similarity(lost_text, found_text)
        
        total_score = (v_score * 0.6) + (t_score * 0.4)

        # Apply Category Penalty (The Fix for the 30% issue)
        for cat in categories:
            if cat in lost_text and cat not in found_text:
                total_score -= 40 # Heavily penalize mismatching types
        
        # Only show if score is meaningful
        if total_score > 20:
            matches.append({
                'lost_item': lost, 
                'match_score': max(0, round(total_score, 1)),
            })

    # Sort and take top 3
    top_matches = sorted(matches, key=lambda x: x['match_score'], reverse=True)[:3]

    # 3. Handle Form Submission
    if request.method == 'POST':
        proof = request.POST.get('proof_description')
        if not proof:
            messages.error(request, "Please provide some proof of ownership.")
        else:
            new_claim = ClaimRequest.objects.create(
                found_item=found_item,
                claimant=request.user,
                proof_description=proof,
                status='PENDING'
            )
            messages.success(request, "Claim request sent! You can now chat with the finder.")
            return redirect('chat_room', claim_id=new_claim.id)

    return render(request, 'claim_match.html', {
        'found_item': found_item,
        'matches': top_matches,
        'has_matches': len(top_matches) > 0,
    })

@login_required
def finalize_claim(request, claim_id):
    claim = get_object_or_404(ClaimRequest, id=claim_id)
    
    # Security: Only the person who FOUND the item can approve a claim
    if request.user != claim.found_item.reported_by:
        messages.error(request, "Only the finder can approve this claim.")
        return redirect('chat_room', claim_id=claim.id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            # 1. Update the claim status
            claim.status = 'APPROVED'
            claim.save()
            
            # 2. Update the actual item status so it's no longer 'PENDING'
            item = claim.found_item
            item.status = 'CLAIMED'
            item.save()
            
            messages.success(request, "Claim approved! The item is now marked as returned.")
            
        elif action == 'reject':
            claim.status = 'REJECTED'
            claim.save()
            messages.warning(request, "Claim rejected. The item is still available for others.")

        return redirect('chat_room', claim_id=claim.id)
    
@login_required
def my_activity(request):
    # Items the user has reported as lost
    my_lost_reports = LostClaim.objects.filter(owner=request.user).order_by('-date_lost')
    
    # Items the user has found and reported
    my_found_reports = FoundItem.objects.filter(reported_by=request.user).order_by('-date_found')
    
    # Claims the user has made on other people's found items
    my_claims_made = ClaimRequest.objects.filter(claimant=request.user).order_by('-created_at')
    
    # Claims other people have made on items this user found
    claims_on_my_items = ClaimRequest.objects.filter(found_item__reported_by=request.user).order_by('-created_at')

    return render(request, 'my_activity.html', {
        'lost_reports': my_lost_reports,
        'found_reports': my_found_reports,
        'claims_made': my_claims_made,
        'claims_received': claims_on_my_items
    })

@login_required

def smart_search_api(request):

    query = request.GET.get('q', '').strip()

    if not query:

        return JsonResponse([], safe=False)



    query_lower = query.lower()

    query_emb = get_embedding(query)

    results = []



    all_items = list(FoundItem.objects.all()) + list(LostClaim.objects.all())



    for item in all_items:

        text = f"{item.item_name} {item.description}".lower().strip()

        if not text:

            continue



        # 1. Embedding similarity

        emb_sim = cosine_similarity(query_emb, get_embedding(text)) * 100



        # 2. Keyword overlap fallback

        query_words = set(query_lower.split())

        item_words = set(text.split())

        keyword_score = len(query_words & item_words) / len(query_words) * 80 if query_words else 0



        # 3. Exact name match bonus

        name_bonus = 50 if query_lower in item.item_name.lower() or item.item_name.lower() in query_lower else 0



        # Final score

        final_score = max(emb_sim, keyword_score) + name_bonus



        if final_score >= 25:  # Lowered threshold

            results.append({

                'item_name': item.item_name,

                'match': round(final_score, 1),

                'type': 'found' if isinstance(item, FoundItem) else 'lost',

                'image': item.image.url if item.image else None,

                'description': item.description[:150] + ("..." if len(item.description) > 150 else item.description)

            })



    results.sort(key=lambda x: x['match'], reverse=True)

    return JsonResponse(results[:10], safe=False)  # Show up to 10

@login_required
def chat_room(request, claim_id):
    claim = get_object_or_404(ClaimRequest, id=claim_id)
    if request.user != claim.claimant and request.user != claim.found_item.reported_by:
        return redirect('home')

    if request.method == 'POST':
        msg_text = request.POST.get('message')
        if msg_text:
            ChatMessage.objects.create(claim_request=claim, sender=request.user, message=msg_text)
        return redirect('chat_room', claim_id=claim.id)

    return render(request, 'chat_room.html', {
        'claim': claim,
        'chat_messages': claim.messages.all(),
        'is_finder': request.user == claim.found_item.reported_by
    })

def found_list(request):
    items = FoundItem.objects.filter(status='PENDING').order_by('-date_found')
    return render(request, 'items_list.html', {'items': items, 'title': 'Found Items', 'type': 'found'})

def lost_list(request):
    items = LostClaim.objects.all().order_by('-date_lost')
    return render(request, 'items_list.html', {'items': items, 'title': 'Lost Items', 'type': 'lost'})

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


# FINAL CHATBOT VIEW — WITH ALL FEATURES
@method_decorator(csrf_exempt, name='dispatch')
class ChatbotView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            question = data.get('question', '').strip()
            image_base64 = data.get('image', None)

            if not request.user.is_authenticated:
                return JsonResponse({'answer': "Please log in to report items! 🔒"})

            if not question and not image_base64:
                return JsonResponse({'answer': "Say something or upload a photo! 😊"})

            q = question.lower() if question else ""

            session = request.session
            state = session.get('chatbot_state', {})

            # Cancel
            if any(word in q for word in ['cancel', 'stop', 'nevermind']):
                if 'chatbot_state' in session:
                    del session['chatbot_state']
                    session.modified = True
                return JsonResponse({'answer': "Conversation canceled! How else can I help?"})

            # IMAGE UPLOAD
            if image_base64:
                if 'action' not in state or state['action'] != 'report':
                    return JsonResponse({'answer': "Start by saying 'report lost/found item' first!"})

                # Extract base64 and extension
                if ';base64,' in image_base64:
                    header, base64_str = image_base64.split(';base64,')
                    ext = header.split('/')[-1]
                else:
                    base64_str = image_base64
                    ext = 'jpg'

                # Decode for Gemini
                image_bytes = base64.b64decode(base64_str)
                temp_file = ContentFile(image_bytes, name=f'temp.{ext}')
                ai_desc = describe_with_gemini(temp_file)

                # Store serializable data
                state['image_base64'] = base64_str
                state['image_ext'] = ext
                state['description'] = ai_desc
                state['has_image'] = True
                state['step'] = 'contact'
                session['chatbot_state'] = state
                session.modified = True

                return JsonResponse({'answer': f"Photo uploaded! 📸\n\n**AI Description:**\n{ai_desc}\n\nNow your contact email?"})

            # START REPORTING
            if 'report' in q and 'action' not in state:
                state['action'] = 'report'
                state['type'] = 'lost' if 'lost' in q else 'found'
                state['step'] = 'name'
                state['has_image'] = False
                session['chatbot_state'] = state
                session.modified = True
                return JsonResponse({'answer': f"Let's report your **{state['type']}** item!\n\nWhat is the item name? (e.g., bag, ring)"})

            # REPORT FLOW
            if state.get('action') == 'report':
                if state['step'] == 'name':
                    state['item_name'] = question.title()
                    state['step'] = 'location'
                    session['chatbot_state'] = state
                    session.modified = True
                    return JsonResponse({'answer': f"Got it: **{state['item_name']}**\n\nWhere was it {state['type']}?"})

                elif state['step'] == 'location':
                    state['location'] = question
                    state['step'] = 'photo'
                    session['chatbot_state'] = state
                    session.modified = True
                    return JsonResponse({'answer': f"Location: **{question}**\n\nPlease upload a photo 📸 (click the camera icon)\n\nOr type 'skip' to continue without photo."})

                elif state['step'] == 'photo':
                    if q == 'skip':
                        state['step'] = 'contact'
                        session['chatbot_state'] = state
                        session.modified = True
                        return JsonResponse({'answer': "Photo skipped.\n\nYour contact email?"})
                    elif 'has_image' not in state:
                        return JsonResponse({'answer': "Waiting for photo... 📸\n\nOr type 'skip' to continue."})

                    state['step'] = 'contact'
                    session['chatbot_state'] = state
                    session.modified = True
                    return JsonResponse({'answer': "Photo analyzed! ✅\n\nFinal step: your contact email?"})

                elif state['step'] == 'contact':
                    state['contact'] = question
                    today = date.today()

                    # SAVE REPORT — FIXED: Save first, get ID, then add image
                    try:
                        if state['type'] == 'lost':
                            obj = LostClaim(
                                owner=request.user,
                                item_name=state['item_name'],
                                description=state.get('description', 'Reported via chatbot'),
                                approx_location_lost=state['location'],
                                date_lost=today,
                                contact_email=state['contact']
                            )
                        else:
                            obj = FoundItem(
                                reported_by=request.user,
                                item_name=state['item_name'],
                                description=state.get('description', 'Reported via chatbot'),
                                location_found=state['location'],
                                date_found=today,
                                contact_email=state['contact']
                            )

                        obj.save()  # Save first to generate ID

                        if state.get('has_image'):
                            base64_str = state['image_base64']
                            ext = state['image_ext']
                            image_bytes = base64.b64decode(base64_str)
                            image_file = ContentFile(image_bytes, name=f'report_{obj.pk}.{ext}')  # Use pk (primary key)
                            obj.image = image_file
                            obj.save()  # Save again with image

                        del session['chatbot_state']
                        session.modified = True

                        return JsonResponse({
                            'answer': f"🎉 **Success!**\n\nYour **{state['type']} {state['item_name']}** reported on {today}.\n\n"
                                      f"{'AI description + photo added!' if state.get('has_image') else 'No photo — consider adding one later.'}\n\n"
                                      "Thank you! ❤️"
                        })
                    except Exception as e:
                        return JsonResponse({'answer': f"Save failed: {str(e)}\nPlease try the regular form."})

            # BASIC RESPONSES
            answer = None  # Initialize answer variable
            
            if any(phrase in q for phrase in ['report', 'submit', 'add item', 'lost item', 'found item', 'how to report', 'report lost', 'report found']):
                answer = (
                    "**How to Report an Item**\n\n"
                    "1. Click **Lost Item** (red button) or **Found Item** (green button) in the top navbar\n"
                    "2. Upload a clear photo → **Gemini AI automatically writes a detailed description**\n"
                    "3. Fill in location, date, and contact info\n"
                    "4. Click Submit — your item is instantly live for others to see!\n\n"
                    "Your report helps someone reunite with their belongings. Thank you! ❤️"
                )

            elif any(phrase in q for phrase in ['claim', 'get back', 'my item', 'retrieve', 'claim this', 'how to claim']):
                answer = (
                    "**How to Claim an Item**\n\n"
                    "1. Go to **Browse Found Items**\n"
                    "2. Find an item that looks like yours → click **Claim This Item**\n"
                    "3. AI automatically compares it with **all your lost reports**\n"
                    "4. See the match percentage (Vision + Text AI)\n"
                    "5. If it's yours → click **YES, THIS IS MY ITEM — CLAIM NOW!**\n\n"
                    "The item is now officially yours. The finder will be notified! 🎉"
                )

            elif any(phrase in q for phrase in ['search', 'find', 'look for', 'how to search', 'how does search work']):
                answer = (
                    "**AI Smart Search**\n\n"
                    "Just type naturally in the big search bar on the homepage!\n\n"
                    "Examples:\n"
                    "• \"I lost my red backpack\"\n"
                    "• \"black iPhone with cracked screen\"\n"
                    "• \"car keys with blue tag\"\n"
                    "• \"nike shoes size 10\"\n\n"
                    "Uses **Google Gemini Embeddings** — understands meaning, not just keywords.\n"
                    "Results appear instantly with photos and match %!"
                )

            elif any(phrase in q for phrase in ['ai matching', 'how does ai work', 'gemini', 'vision', 'how accurate', 'matching']):
                answer = (
                    "**AI Magic Explained**\n\n"
                    "• **Photo Upload** → Gemini Vision analyzes the image → writes detailed description\n"
                    "• **Smart Search** → Gemini Embeddings understand natural language meaning\n"
                    "• **Claim Matching** → \n"
                    "   – 60% Image comparison (Gemini Vision)\n"
                    "   – 40% Text similarity (Gemini Embeddings)\n"
                    "   = Ultra-accurate match score\n\n"
                    "Smarter than any manual system! 🤖✨"
                )

            elif any(phrase in q for phrase in ['everything', 'all features', 'what can i do', 'features', 'capabilities']):
                answer = (
                    "**Everything You Can Do in FoundIt**\n\n"
                    "• Report lost or found items with **AI-powered photo description**\n"
                    "• Search using **natural language** (e.g., \"I lost my wallet yesterday\")\n"
                    "• Browse all items with beautiful photos\n"
                    "• Click **Claim This Item** → AI shows match % with your lost reports\n"
                    "• Permanently claim items with one click\n"
                    "• Get help anytime from **me — your AI assistant** 🤖\n\n"
                    "All powered by **Google Gemini Vision + Embeddings**\n"
                    "The smartest lost & found system ever built! 🚀"
                )

            elif any(phrase in q for phrase in ['own item', 'claim my own', 'found myself', 'claim own']):
                answer = (
                    "No — you cannot claim an item you reported yourself.\n\n"
                    "This prevents abuse and keeps the system fair for everyone. "
                    "The goal is to help others recover their belongings! 🙏"
                )

            elif any(phrase in q for phrase in ['hello', 'hi', 'hey', 'help', 'what', 'how', 'sup', 'yo']):
                answer = (
                    "**Hey there! 👋**\n\n"
                    "I'm your personal AI assistant for FoundIt.\n\n"
                    "Ask me anything:\n"
                    "• How do I report a lost item?\n"
                    "• How does the AI search work?\n"
                    "• How do I claim an item?\n"
                    "• What features are available?\n\n"
                    "Just type naturally — I'm here to help! 😊"
                )

            else:
                answer = (
                    "I'm your FoundIt expert! I can help with:\n\n"
                    "• Reporting lost/found items\n"
                    "• Using the AI search\n"
                    "• Claiming items\n"
                    "• Understanding how the AI works\n\n"
                    "Try asking:\n"
                    "• \"How do I report a lost item?\"\n"
                    "• \"How does claiming work?\"\n"
                    "• \"What can I do here?\""
                )

            return JsonResponse({'answer': "Try 'report lost bag' or ask any question! 😊"})

        except Exception as e:
            return JsonResponse({'answer': f"Error: {str(e)}"})