# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import RegUser, FoundItem, LostClaim

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    student_id = forms.CharField(max_length=10, required=True)

    class Meta(UserCreationForm.Meta):
        model = RegUser
        fields = ("username", "email", "student_id")

class FoundItemForm(forms.ModelForm):
    class Meta:
        model = FoundItem
        fields = ['item_name', 'description', 'location_found', 'date_found', 'contact_email', 'image']
        widgets = {
            'date_found': forms.DateInput(attrs={'type': 'date', 'class': 'input input-bordered'}),
            'description': forms.Textarea(attrs={
                'rows': 4, 
                'class': 'textarea textarea-bordered shadow-inner',
                'placeholder': 'AI will generate this from your photo, or you can type here...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allows form to submit even if user hasn't typed anything yet
        self.fields['description'].required = False 

class LostClaimForm(forms.ModelForm):
    class Meta:
        model = LostClaim
        fields = ['item_name', 'description', 'approx_location_lost', 'date_lost', 'contact_email', 'image']
        widgets = {
            'date_lost': forms.DateInput(attrs={'type': 'date', 'class': 'input input-bordered'}),
            'description': forms.Textarea(attrs={
                'rows': 4, 
                'class': 'textarea textarea-bordered shadow-inner',
                'placeholder': 'AI will generate this from your photo, or you can type here...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allows form to submit even if user hasn't typed anything yet
        self.fields['description'].required = False