# D:\Django Internship\tprmsystem\main\models.py
from django.db import models
from django.conf import settings 
from django.utils import timezone
from django.contrib.auth import get_user_model  
import uuid


User = get_user_model()


class ActivityLog(models.Model):
    """
    Log all user activities for audit trail
    Tracks both admin and member actions
    """
    
    ACTION_CHOICES = [
        ('login_success', 'Login Success'),
        ('login_failed', 'Login Failed'),
        ('logout', 'Logout'),
        ('token_refresh', 'Token Refresh'),
        ('view_dashboard', 'View Dashboard'),
        ('view_profile', 'View Profile'),
        ('update_profile', 'Update Profile'),
        ('create_member', 'Create Member'),
        ('view_bookings', 'View Bookings'),
        ('create_booking', 'Create Booking'),
        ('other', 'Other Action'),
    ]
    
    # Changed: Use settings.AUTH_USER_MODEL instead of User
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # This points to 'temple_admin.TempleAdmin'
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='main_activity_logs',
        help_text="User who performed the action"
    )
    
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        help_text="Type of action performed"
    )
    
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When the action occurred"
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the user"
    )
    
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        help_text="Browser/device information"
    )
    
    is_admin = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether action was performed by admin"
    )
    
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional details about the action"
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
    
    def __str__(self):
        username = self.user.username if self.user else 'Anonymous'
        return f"{self.user.username} - {self.action} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    
class Gallery(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    image_url = models.URLField()
    cloudinary_public_id = models.CharField(max_length=255)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_gallery_images"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or self.image_url

class PasswordResetToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
