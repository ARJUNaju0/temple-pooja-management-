from django.db import models
from django.conf import settings
from django.utils import timezone
from temple_admin.models import TempleAdmin
from booking.utils.email_service import send_booking_email



class PoojaBooking(models.Model):
    """Enhanced booking model with offline payment & admin approval"""
    
    # ============================================================================
    # STATUS & PAYMENT CHOICES
    # ============================================================================
    
    BOOKING_STATUS_CHOICES = [
        ("pending", "Pending"),           # ← NEW: Awaiting admin approval
        ("approved", "Approved"),         # ← NEW: Admin approved
        ("completed", "Completed"),       # Existing
        ("cancelled", "Cancelled"),       # Existing
    ]
    
    PAYMENT_STATUS_CHOICES = [
    ("pending", "Pending"),              # default (online before success)
    ("pending_cash", "Pending Cash"),    # cash not yet paid
    ("paid_online", "Paid Online"),       # Razorpay success
    ("paid_cash", "Paid Cash"),           # admin confirmed cash
    ("failed", "Failed"),
    ("refunded", "Refunded"),
]

    
    # ← NEW: Payment method to differentiate online/offline
    PAYMENT_METHOD_CHOICES = [
        ("upi", "UPI Online"),            # Razorpay online
        ("upi_qr", "UPI QR Code"),        # Offline UPI QR
        ("cash", "Cash"),                 # Cash at counter
    ]
    
    # ============================================================================
    # CORE FIELDS (EXISTING)
    # ============================================================================
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pooja_bookings"
    )
    pooja = models.ForeignKey(
        "pooja.Pooja",
        on_delete=models.CASCADE,
        related_name="bookings"
    )
    
    # ← UPDATED: Default is now 'pending' instead of 'booked'
    status = models.CharField(
        max_length=20,
        choices=BOOKING_STATUS_CHOICES,
        default="pending",  # ← CHANGED from "booked"
        db_index=True
    )
    
    # ============================================================================
    # PAYMENT TRACKING FIELDS (EXISTING)
    # ============================================================================
    
    payment_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Razorpay payment ID (online only)"
    )
    order_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        help_text="Razorpay order ID"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount paid in INR"
    )
    
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="pending",
        db_index=True
    )
    
    # ← NEW: Track which payment method was used
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="upi",
        db_index=True,
        help_text="Payment method: online UPI, offline QR, or cash"
    )
    
    # ============================================================================
    # TIMESTAMPS (EXISTING + NEW)
    # ============================================================================
    
    booked_at = models.DateTimeField(auto_now_add=True)
    
    payment_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When payment was actually completed"
    )
    
    # ← NEW: When admin approved the booking
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When admin approved this booking"
    )
    
    # ← NEW: When booking was cancelled
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When booking was cancelled"
    )
    
    payment_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment signature was verified"
    )
    
    # ============================================================================
    # ADMIN TRACKING (NEW)
    # ============================================================================
    
    # ← NEW: Which admin approved/cancelled the booking
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_bookings",
        help_text="Admin who approved/cancelled this booking"
    )
    
    # ============================================================================
    # DEVOTEE DETAILS (EXISTING)
    # ============================================================================
    
    devotee_name = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )
    phone_number = models.CharField(
        max_length=15,
        null=True,
        blank=True
    )
    nakshatra = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )
    
    # ============================================================================
    # META & STRING
    # ============================================================================
    
    class Meta:
        db_table = "pooja_bookings"
        ordering = ['-booked_at']
        indexes = [
            models.Index(fields=['payment_id']),
            models.Index(fields=['order_id']),
            models.Index(fields=['user', '-booked_at']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_method']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.pooja.name} ({self.status})"
    
    # ============================================================================
    # EXISTING METHODS
    # ============================================================================
    
    def is_payment_pending(self):
        """Check if payment is still pending"""
        return self.payment_status == "pending"
    
    def mark_payment_completed(self):
        """Mark payment as completed (call after verification)"""
        self.payment_status = "completed"
        self.payment_completed_at = timezone.now()
        self.save()
    
    # ============================================================================
    # NEW METHODS FOR APPROVAL WORKFLOW
    # ============================================================================
    
    def can_be_approved(self):
        """Check if booking can be approved"""
        return self.status == "pending"
    
    def can_be_cancelled(self):
        """Check if booking can be cancelled"""
        return self.status in ["pending", "approved"]
    
    def approve(self, admin_user):
        """
        Approve pending booking
        Sets: status='approved', approved_at=now, updated_by=admin
        """
        if not self.can_be_approved():
            raise ValueError(f"Cannot approve booking in {self.status} state")
        
        self.status = "approved"
        self.approved_at = timezone.now()
        self.updated_by = admin_user
        self.save()
         # AUTO EMAIL
        send_booking_email(
            subject="Your Booking Has Been Approved",
            template_name="booking_approved.html",
            to_email=self.user.email,
            context={
                "name": self.devotee_name or self.user.username,
                "booking_id": self.id,
                "status": "Approved",
                "date": self.approved_at.strftime("%d %B %Y"),
            }
        )
    
    def cancel(self, admin_user):
        """
        Cancel booking
        Sets: status='cancelled', cancelled_at=now, updated_by=admin
        """
        if not self.can_be_cancelled():
            raise ValueError(f"Cannot cancel booking in {self.status} state")
        
        self.status = "cancelled"
        self.cancelled_at = timezone.now()
        self.updated_by = admin_user
        self.save()


# ============================================================================
# NEW: PAYMENT HISTORY MODEL
# ============================================================================

class PaymentHistory(models.Model):
    """Track all payment events for audit trail and reconciliation"""
    
    PAYMENT_MODE_CHOICES = [
        ('upi_online', 'UPI Online'),
        ('upi_qr', 'UPI QR Code'),
        ('cash', 'Cash'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]
    
    # ← LINK TO BOOKING
    booking = models.ForeignKey(
        PoojaBooking,
        on_delete=models.CASCADE,
        related_name='payment_history',
        help_text="Associated booking"
    )
    
    # ← PAYMENT DETAILS
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount in INR"
    )
    payment_mode = models.CharField(
        max_length=20,
        choices=PAYMENT_MODE_CHOICES,
        help_text="Payment method used"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Payment status"
    )
    
    # ← OPTIONAL: UPI/GATEWAY REFERENCE
    reference_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="UPI transaction reference (for QR payments)"
    )
    transaction_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Payment gateway transaction ID (Razorpay)"
    )
    
    # ← ADMIN WHO CONFIRMED
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_payments',
        help_text="Admin who confirmed this payment"
    )
    
    # ← NOTES (for failures, etc.)
    notes = models.TextField(
        null=True,
        blank=True,
        help_text="Additional notes (reason for failure, etc.)"
    )
    
    # ← TIMESTAMPS
    confirmed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When payment was confirmed"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When record was last updated"
    )
    
    class Meta:
        db_table = "payment_history"
        ordering = ['-confirmed_at']
        indexes = [
            models.Index(fields=['booking', '-confirmed_at']),
            models.Index(fields=['payment_mode']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Payment for Booking #{self.booking.id} - {self.payment_mode}"



# Email logging model for audit trail

class EmailLog(models.Model):
    """Track all email sending attempts for audit and debugging"""
    
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]
    
    recipient = models.EmailField(
        help_text="Email recipient"
    )
    subject = models.CharField(
        max_length=200,
        help_text="Email subject line"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Email delivery status"
    )
    attempts = models.IntegerField(
        default=1,
        help_text="Number of send attempts"
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Error message if failed"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the email was first attempted"
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the email was successfully sent"
    )
    
    # Link to booking (optional)
    booking = models.ForeignKey(
        'PoojaBooking',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_logs',
        help_text="Associated booking"
    )
    
    class Meta:
        db_table = "email_logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['booking']),
        ]
    
    def __str__(self):
        return f"{self.recipient} - {self.subject} ({self.status})"
