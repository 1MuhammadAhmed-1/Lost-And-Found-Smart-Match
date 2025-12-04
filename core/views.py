# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse

from .forms import RegisterForm, FoundItemForm, LostClaimForm
from .models import FoundItem, LostClaim

# --------------------- GEMINI AI SETUP ---------------------
import google.generativeai as genai
from pathlib import Path
import mimetypes
import numpy as np
from numpy.linalg import norm
import re

genai.configure(api_key="AIzaSyAaZduo5QrN1CIK8n-ZhYdkIhyHrRmuJGA")  # Change to env var later

# --------------------- AI HELPER FUNCTIONS ---------------------

def describe_with_gemini(image_field):
    try:
        image_field.seek(0)
        image_data = image_field.read()
        ext = Path(image_field.name).suffix.lower()
        mime_type = mimetypes.guess_type("file" + ext)[0] or "image/jpeg"

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([
            "You are an expert lost & found assistant. Describe this item in extreme detail: color, brand, material, size, condition, logos, damage, unique features. Write in full sentences.",
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
    """Safe and working image comparison with Gemini"""
    if not img1 or not img2:
        return 0

    try:
        img1.seek(0)
        img2.seek(0)

        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([
            "Compare these two images. Are they the same item? "
            "Answer with ONLY a number 0–100. No words, no explanation.",
            img1, img2
        ])

        import re
        match = re.search(r'\d+', response.text)
        return float(match.group()) if match else 50

    except Exception as e:
        print("Image comparison error:", e)
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


# REAL AI SMART SEARCH — USING GEMINI EMBEDDINGS
@login_required
def smart_search_api(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse([], safe=False)

    query_lower = query.lower()
    query_emb = get_embedding(query)

    results = []

    # Combine both found and lost items
    for item in list(FoundItem.objects.all()) + list(LostClaim.objects.all()):
        text = f"{item.item_name} {item.description}".lower()
        if not text:
            continue

        # 1. Embedding similarity (real AI understanding)
        emb_sim = cosine_similarity(query_emb, get_embedding(text)) * 100

        # 2. Keyword fallback (in case embedding is picky)
        keyword_score = 0
        query_words = set(query_lower.split())
        item_words = set(text.split())
        if query_words & item_words:
            keyword_score = len(query_words & item_words) / len(query_words) * 70

        # 3. Exact name match bonus
        name_bonus = 40 if query_lower in item.item_name.lower() or item.item_name.lower() in query_lower else 0

        # Final score
        final_score = max(emb_sim, keyword_score) + name_bonus

        if final_score >= 40:  # Lowered threshold + smarter logic
            results.append({
                'item_name': item.item_name,
                'match': round(min(final_score, 98), 1),
                'type': 'found' if isinstance(item, FoundItem) else 'lost',
                'image': item.image.url if item.image else None,
                'description': item.description[:130] + "..." if len(item.description) > 130 else item.description
            })

    # Sort by best match
    results.sort(key=lambda x: x['match'], reverse=True)
    return JsonResponse(results[:10], safe=False)


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