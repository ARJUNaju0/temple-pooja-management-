# D:\Django Internship\tprmsystem\temple_admin\models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# --- 1. Core User Model ---
class TempleAdmin(AbstractUser):
    """
    Custom user model for the application.
    Roles: 'temple_admin' (Staff/Superuser) vs 'member' (Devotee).
    """
    ROLE_CHOICES = [
        ('temple_admin', 'Temple Admin'),
        ('member', 'Member'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    
    # Permission flags
    is_temple_admin = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'temple_users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def save(self, *args, **kwargs):
        """
        Auto-syncs 'is_staff' permissions based on the Role or Superuser status.
        """
        # 1. If Superuser (terminal created), force Admin role
        if self.is_superuser:
            self.role = 'temple_admin'
            self.is_temple_admin = True
            self.is_staff = True
            
        # 2. If explicitly set as Temple Admin
        elif self.role == 'temple_admin':
            self.is_temple_admin = True
            self.is_staff = True 
            
        # 3. Normal Members
        else:
            self.is_temple_admin = False
            self.is_staff = False
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


# --- 2. Activity Logging Model ---
class AdminActivityLog(models.Model):
    """
    Logs security events (Logins, Updates) for auditing.
    """
    admin = models.ForeignKey(TempleAdmin, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=255) # e.g., "Login", "Added Member"
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True) # Browser info
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'admin_activity_logs'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.admin.username} - {self.action} at {self.timestamp}"

class MemberProfile(models.Model):
    temple_admin = models.OneToOneField(
        TempleAdmin,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    nakshatram = models.CharField(max_length=100)
    gender = models.CharField(max_length=20)

    # Self-referential relationship for referrals / lineage
    referrer = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referred_members"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class SiteSettings(models.Model):
    allow_multiple_bookings = models.BooleanField(
        default=False,
        help_text="Allow members to book the same pooja multiple times"
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name_plural = "Site Settings"
        constraints = [
            models.UniqueConstraint(
                fields=['id'],
                name='single_site_settings'
            )
        ]
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and SiteSettings.objects.exists():
            raise ValidationError("Only one instance of SiteSettings is allowed")
        return super().save(*args, **kwargs)
    def __str__(self):
        return "Site Settings"
