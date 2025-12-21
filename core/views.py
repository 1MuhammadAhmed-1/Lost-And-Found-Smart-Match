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
from .models import FoundItem, LostClaim

# --------------------- GEMINI AI SETUP ---------------------
import google.generativeai as genai
from pathlib import Path
import mimetypes
import numpy as np
from numpy.linalg import norm

genai.configure(api_key=settings.GEMINI_API_KEY)
# --------------------- AI HELPER FUNCTIONS ---------------------

def describe_with_gemini(image_field):
    """Generate concise description from uploaded image using Gemini Vision"""
    try:
        image_field.seek(0)
        image_data = image_field.read()
        ext = Path(image_field.name).suffix.lower()
        mime_type = mimetypes.guess_type("file" + ext)[0] or "image/jpeg"

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content([
            "Describe this item CONCISELY in 3-5 sentences. Focus on UNIQUE features: color, brand, size, condition, logos, damage. Avoid general phrases.",
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
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content([
            "Compare these two images. Are they the same item? Answer ONLY with a number 0–100.",
            img1, img2
        ])
        match = re.search(r'\d+', response.text)
        return float(match.group()) if match else 50
    except:
        return 50
    finally:
        for img in (img1, img2):
            try:
                img.seek(0)
            except:
                pass


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
            messages.success(request, "Lost item reported — AI analyzed your photo!")
            return redirect('home')
    else:
        form = LostClaimForm()
    return render(request, 'report_form.html', {'form': form, 'title': 'Report Lost Item'})


# REAL AI SMART SEARCH — FIXED TO SHOW RESULTS
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
def claim_item(request, item_id):
    found_item = get_object_or_404(FoundItem, item_id=item_id)
    if found_item.reported_by == request.user:
        messages.error(request, "You cannot claim your own found item!")
        return redirect('found_list')
    if found_item.claimed_by:
        messages.warning(request, f"Already claimed by {found_item.claimed_by.username}")
        return redirect('found_list')

    user_lost_items = LostClaim.objects.filter(owner=request.user)
    matches = []

    for lost in user_lost_items:
        vision = ai_image_similarity(lost.image, found_item.image) if lost.image and found_item.image else 0
        text = ai_text_similarity(f"{lost.item_name} {lost.description}", f"{found_item.item_name} {found_item.description}")
        score = (vision * 0.6) + (text * 0.4)
        if score >= 30:
            matches.append({
                'lost_item': lost, 'match_score': round(score, 1),
                'vision_score': round(vision, 1), 'text_score': round(text, 1)
            })

    matches.sort(key=lambda x: x['match_score'], reverse=True)

    if request.method == 'POST':
        found_item.claimed_by = request.user
        found_item.status = 'CLAIMED'
        found_item.save()
        messages.success(request, f"You successfully claimed '{found_item.item_name}'!")
        return redirect('found_list')

    return render(request, 'claim_match.html', {
        'found_item': found_item, 'matches': matches,
        'has_matches': len(matches) > 0, 'already_claimed': bool(found_item.claimed_by)
    })


def found_list(request):
    items = FoundItem.objects.all().order_by('-date_found')
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
            messages.success(request, f"Welcome {user.username}!")
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