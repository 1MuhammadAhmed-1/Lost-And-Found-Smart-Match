from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid 

# 1. USER MODEL 
class RegUser(AbstractUser):
    """Extends the default Django User for custom authentication and roles."""
    
    student_id = models.CharField(max_length=10, unique=True, null=True, blank=True)
    is_staff_admin = models.BooleanField(default=False)
    
    # Required for custom user models to avoid field name clashes in Django's internal system
    groups = models.ManyToManyField(
        'auth.Group', related_name='reguser_groups', blank=True,
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission', related_name='reguser_permissions', blank=True,
    )
    
    def __str__(self):
        return self.username


# 2. FOUND ITEM MODEL (Data for AI matching)
class FoundItem(models.Model):
    """Represents an item that has been found and reported."""
    
    item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # CRUCIAL FOR AI MATCHING
    item_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, help_text="Detailed description of the item, color, condition, etc.")
    
    location_found = models.CharField(max_length=100)
    date_found = models.DateField()
    contact_email = models.EmailField(max_length=100, null=True, blank=True)

    # In core/models.py — add this line inside FoundItem class
    claimed_by = models.ForeignKey(
        RegUser, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='claimed_items'
    )

    status_choices = [
        ('PENDING', 'Pending Claim'),
        ('CLAIMED', 'Claimed'),
        ('RETURNED', 'Returned'),
        ('DISPOSED', 'Disposed')
    ]
    status = models.CharField(max_length=20, choices=status_choices, default='PENDING')
    image = models.ImageField(upload_to='found_items/', null=True, blank=True)  # ← ADD THIS
    reported_by = models.ForeignKey(RegUser, on_delete=models.SET_NULL, null=True, related_name='reported_found_items')

    # Field to store the text vector for AI
    text_vector = models.JSONField(null=True, blank=True) 

    def __str__(self):
        return f"{self.item_name} found at {self.location_found}"


# 3. LOST CLAIM MODEL (Data for AI matching)
class LostClaim(models.Model):
    """Represents a request/report for a lost item."""
    
    claim_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # CRUCIAL FOR AI MATCHING
    item_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, help_text="Detailed description of the lost item.")
    
    approx_location_lost = models.CharField(max_length=100, null=True, blank=True)
    date_lost = models.DateField()
    contact_email = models.EmailField(max_length=100, null=True, blank=True)
    
    owner = models.ForeignKey(RegUser, on_delete=models.CASCADE, related_name='submitted_lost_claims')
    image = models.ImageField(upload_to='lost_items/', null=True, blank=True)   # ← ADD THIS
    is_matched = models.BooleanField(default=False)
    
    # Field to store the text vector for AI
    text_vector = models.JSONField(null=True, blank=True) 
    
    def __str__(self):
        return f"Lost: {self.item_name} by {self.owner.username}"
    
    # 4. CLAIM REQUEST (The bridge between Finder and Claimant)
class ClaimRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    found_item = models.ForeignKey(FoundItem, on_delete=models.CASCADE, related_name='claims')
    claimant = models.ForeignKey(RegUser, on_delete=models.CASCADE, related_name='my_requests')
    
    # Verification Fields
    proof_description = models.TextField(help_text="Claimant's description of unique details.")
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected')
    ], default='PENDING')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Claim for {self.found_item.item_name} by {self.claimant.username}"

# 5. ANONYMOUS CHAT SYSTEM
class ChatMessage(models.Model):
    claim_request = models.ForeignKey(ClaimRequest, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(RegUser, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']