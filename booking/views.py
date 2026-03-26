import json
import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from booking.utils.email_service import send_booking_email
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator
from rest_framework.permissions import IsAuthenticated
from main.decorators import member_required, admin_required
from booking.models import PoojaBooking, PaymentHistory
from pooja.models import Pooja
from rest_framework.decorators import api_view, permission_classes
from booking.serializers import PaymentStatusUpdateSerializer
from booking.permissions import IsAdminOrOperator
from booking.utils.email_service import send_booking_email
from booking.utils.email_service import send_booking_email
from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count, Case, When, DecimalField, Max
from django.http import HttpResponse
import csv
from temple_admin.models import SiteSettings
User = get_user_model()


logger = logging.getLogger(__name__)



# SECTION 1: EXISTING ONLINE PAYMENT VIEWS (Updated for Pending Workflow)


@member_required
@require_http_methods(["GET", "POST"])
def book_pooja(request, pooja_id):
    """
    Create Razorpay order for online payment
    Updated: Creates booking in 'pending' state (awaiting admin approval)
    """
    member = request.user
    pooja = get_object_or_404(Pooja, id=pooja_id)
    
    # Role check
    if request.user.role != "member":
        messages.error(request, "Only members can book poojas.")
        return redirect("pooja:services")

    # Duplicate booking check - only if multiple bookings are not allowed for this pooja
    if not pooja.allow_multiple_bookings:
        if PoojaBooking.objects.filter(
            user=member, 
            pooja=pooja,
            status__in=['pending', 'approved', 'completed']
        ).exists():
            messages.error(request, "You have already booked this pooja.")
            return redirect("pooja:services")

    # Slot availability check
    if pooja.available_slots <= 0:
        messages.error(request, "Sorry, no available slots for this pooja.")
        return redirect("pooja:services")

    # Amount validation
    if pooja.amount <= 0:
        messages.error(request, "Invalid pooja amount. Contact admin.")
        logger.error(f"Invalid pooja amount: {pooja.id} = {pooja.amount}")
        return redirect("pooja:services")

    try:
        # Create Razorpay order
        amount_paise = int(Decimal(str(pooja.amount)) * 100)
        
        order_data = {
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': f'pooja_{pooja.id}_{member.id}_{int(timezone.now().timestamp())}',
            'notes': {
                'pooja_id': str(pooja.id),
                'pooja_name': pooja.name,
                'user_id': str(member.id),
                'user_email': member.email,
            },
            'payment_capture': 1
        }

        # Initialize Razorpay client
        import razorpay
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        order = client.order.create(data=order_data)
        logger.info(f"Order created: {order['id']} for user {member.id}, pooja {pooja.id}")

    except Exception as e:
        messages.error(request, "Error initiating payment. Please try again.")
        logger.error(f"Order creation failed: {str(e)}", exc_info=True)
        return redirect("pooja:services")

    context = {
        'pooja': pooja,
        'member': member,
        'order': order,
        'RAZORPAY_KEY_ID': settings.RAZORPAY_KEY_ID,
        'amount': amount_paise,
        'currency': 'INR'
    }
    
    return render(request, "booking/book_pooja.html", context)


@csrf_exempt
@require_http_methods(["POST"])
def paymenthandler(request):
    """
    Handle Razorpay payment callback
    Updated: Creates booking in 'pending' state (not 'booked')
    Does NOT decrement slots (happens on admin approval)
    """
    try:
        # Extract form data
        payment_id = request.POST.get('razorpay_payment_id', '').strip()
        razorpay_order_id = request.POST.get('razorpay_order_id', '').strip()
        signature = request.POST.get('razorpay_signature', '').strip()
        pooja_id = request.POST.get('pooja_id', '').strip()
        devotee_name = request.POST.get('devotee_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        nakshatra = request.POST.get('nakshatra', '').strip()

        # Validate required fields
        if not all([payment_id, razorpay_order_id, signature, pooja_id]):
            logger.warning("Missing payment parameters")
            messages.error(request, "Invalid payment request.")
            return redirect('pooja:services')

        # Authenticate user
        if not request.user.is_authenticated:
            logger.warning(f"Unauthenticated payment attempt")
            messages.error(request, "You must be logged in.")
            return redirect('login')

        user = request.user
        pooja = get_object_or_404(Pooja, id=pooja_id)

        # Idempotency check
        existing_booking = PoojaBooking.objects.filter(
            payment_id=payment_id
        ).first()
        
        if existing_booking:
            logger.warning(f"Duplicate payment: {payment_id}")
            return redirect('booking_success', booking_id=existing_booking.id)

        # Verify signature
        try:
            import razorpay
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
        except Exception as e:
            logger.error(f"Signature verification failed: {str(e)}")
            messages.error(request, "Payment verification failed.")
            return redirect('pooja:services')

        # Fetch order from Razorpay API
        try:
            razorpay_order = client.order.fetch(razorpay_order_id)
            order_amount = razorpay_order['amount']
        except Exception as e:
            logger.error(f"Error fetching order: {str(e)}")
            messages.error(request, "Error verifying payment.")
            return redirect('pooja:services')

        # Verify amount
        expected_amount = int(Decimal(str(pooja.amount)) * 100)
        if order_amount != expected_amount:
            logger.error(f"Amount mismatch: {order_amount} vs {expected_amount}")
            messages.error(request, "Payment amount mismatch.")
            return redirect('pooja:services')

        # ATOMIC TRANSACTION - Create pending booking
        try:
            with transaction.atomic():
                locked_pooja = Pooja.objects.select_for_update().get(id=pooja.id)

                # Check for existing booking if multiple bookings are not allowed for this pooja
                if not locked_pooja.allow_multiple_bookings:
                    if PoojaBooking.objects.filter(
                        user=user, 
                        pooja=locked_pooja,
                        status__in=['pending', 'approved', 'completed']
                    ).exists():
                        messages.error(request, "You have already booked this pooja.")
                        return redirect('pooja:services')

                if locked_pooja.available_slots <= 0:
                    messages.error(request, "No slots available.")
                    return redirect('pooja:services')

                # CREATE BOOKING IN PENDING STATE
                booking = PoojaBooking.objects.create(
                    user=user,
                    pooja=locked_pooja,
                    payment_id=payment_id,
                    order_id=razorpay_order_id,
                    amount=Decimal(str(order_amount / 100)),
                    payment_status='paid_online',
                    status='pending',  # Awaiting admin approval
                    payment_method='upi',
                    payment_completed_at=timezone.now(),
                    payment_verified_at=timezone.now(),
                    devotee_name=devotee_name,
                    phone_number=phone,
                    nakshatra=nakshatra,
                )
                
                # Record payment in history
                PaymentHistory.objects.create(
                    booking=booking,
                    amount=booking.amount,
                    payment_mode='upi_online',
                    status='paid',
                    confirmed_by=None,
                    confirmed_at=timezone.now()
                )

                logger.info(f"Pending booking created: {booking.id} for user {user.id}")

        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            messages.error(request, "Booking creation failed.")
            return redirect('pooja:services')

        # For UPI payments, auto-approve and decrement slots
        if booking.payment_method == 'upi':
            try:
                with transaction.atomic():
                    # Lock pooja for update
                    pooja = Pooja.objects.select_for_update().get(id=booking.pooja_id)
                    
                    # Decrement slot count
                    if pooja.available_slots > 0:
                        pooja.available_slots -= 1
                        pooja.save(update_fields=['available_slots'])
                        
                        # Update booking status to approved
                        booking.status = 'approved'
                        booking.approved_at = timezone.now()
                        booking.save()
                        
                        # Record payment in history
                        PaymentHistory.objects.create(
                            booking=booking,
                            amount=booking.amount,
                            payment_mode='upi_online',
                            status='paid',
                            confirmed_by=user if user.is_staff else None,
                            confirmed_at=timezone.now()
                        )
                        # Send email synchronously with retry
                        email_sent = send_booking_email(
                            subject="Payment Received Successfully",
                            template_name="payment_online.html",
                            to_email=booking.user.email,
                            context={
                                "name": booking.devotee_name or booking.user.username,
                                "booking_id": booking.id,
                                "amount": booking.amount,
                                "status": "Paid Online",
                                "date": booking.payment_completed_at.strftime("%d %B %Y"),
                            },
                            max_retries=3
                        )
                        
                        if not email_sent:
                            logger.warning(f"Failed to send payment email for booking {booking.id}")
                            # Don't fail the payment - just log the issue
                        logger.info(f"UPI payment booking {booking.id} auto-approved for user {user.id}")
                        messages.success(request, "Booking confirmed! Your payment was successful.")
                    else:
                        # No slots available, mark as failed
                        booking.status = 'cancelled'
                        booking.cancelled_at = timezone.now()
                        booking.save()
                        
                        # Update payment status to failed
                        booking.payment_status = 'failed'
                        booking.save()
                        
                        # Record failed payment in history
                        PaymentHistory.objects.create(
                            booking=booking,
                            amount=booking.amount,
                            payment_mode='upi_online',
                            status='failed',
                            notes='No available slots at time of payment',
                            confirmed_at=timezone.now()
                        )
                        
                        logger.warning(f"UPI payment failed - no slots available for booking {booking.id}")
                        messages.error(request, "Booking failed. No slots available.")
                        return redirect('pooja:services')
                        
            except Exception as e:
                logger.error(f"Error processing UPI payment: {str(e)}")
                # If anything fails, keep as pending for admin review
                booking.status = 'pending'
                booking.save()
                
                PaymentHistory.objects.create(
                    booking=booking,
                    amount=booking.amount,
                    payment_mode='upi_online',
                    status='paid',  # Payment was successful, but approval pending
                    notes=f'Automatic approval failed: {str(e)}',
                    confirmed_at=timezone.now()
                )
                
                messages.warning(request, "Payment received. Your booking is pending admin approval.")
        else:
            # For non-UPI payments, keep as pending
            PaymentHistory.objects.create(
                booking=booking,
                amount=booking.amount,
                payment_mode='upi_online',
                status='paid',
                confirmed_by=None,
                confirmed_at=timezone.now()
            )
            logger.info(f"Pending booking created: {booking.id} for user {user.id}")
            messages.success(request, "Booking submitted! Awaiting admin approval.")

        return redirect('booking_success', booking_id=booking.id)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        messages.error(request, "An error occurred.")
        return redirect('pooja:services')



@member_required
def booking_success(request, booking_id):
    """Display booking confirmation page"""
    try:
        logger.info(f"Attempting to display booking success for booking ID: {booking_id}, user: {request.user.id}")
        
        booking = get_object_or_404(
            PoojaBooking.objects.select_related('pooja'),
            id=booking_id,
            user=request.user
        )
        
        logger.info(f"Found booking: {booking.id}, status: {booking.status}, payment_status: {booking.payment_status}")
        
        if booking.payment_status not in ['paid_online', 'pending']:
            msg = f"Invalid payment status: {booking.payment_status}"
            logger.warning(msg)
            messages.error(request, "This booking is not confirmed yet.")
            return redirect('pooja:services')
        
        context = {
            'booking': booking,
            'is_pending': booking.status == 'pending',
        }
        
        logger.info("Rendering booking success template")
        return render(request, 'booking/booking_success.html', context)
    
    except Exception as e:
        logger.exception(f"Error in booking_success view: {str(e)}")
        messages.error(request, f"Error loading booking details: {str(e)}")
        return redirect('pooja:services')



# SECTION 2: MEMBER BOOKING HISTORY & CANCELLATION


@member_required
def member_booking_history(request):
    """
    Display member's booking history with filters
    """
    member = request.user
    
    # Get filters from query params
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Start with member's bookings
    bookings = PoojaBooking.objects.filter(user=member).select_related('pooja')
    
    # Apply filters
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    
    if date_from:
        try:
            from datetime import datetime
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            bookings = bookings.filter(booked_at__date__gte=from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            from datetime import datetime
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            bookings = bookings.filter(booked_at__date__lte=to_date)
        except ValueError:
            pass
    
    # Order by newest first
    bookings = bookings.order_by('-booked_at')
    
    # Pagination
    paginator = Paginator(bookings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    total_bookings = PoojaBooking.objects.filter(user=member).count()
    completed_bookings = PoojaBooking.objects.filter(user=member, status='completed').count()
    approved_bookings = PoojaBooking.objects.filter(user=member, status='approved').count()
    pending_bookings = PoojaBooking.objects.filter(user=member, status='pending').count()
    cancelled_bookings = PoojaBooking.objects.filter(user=member, status='cancelled').count()
    
    # Get today's date for cancel button logic
    from django.utils import timezone
    
    context = {
        'page_obj': page_obj,
        'bookings': page_obj.object_list,
        'total_bookings': total_bookings,
        'completed_bookings': completed_bookings,
        'approved_bookings': approved_bookings,
        'pending_bookings': pending_bookings,
        'cancelled_bookings': cancelled_bookings,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'today': timezone.now().date(),
    }
    
    return render(request, 'booking/member_history.html', context)


@member_required
@require_POST
def cancel_booking(request, booking_id):
    """
    Cancel a booking (only pending or approved)
    Handles refund for paid bookings
    """
    try:
        with transaction.atomic():
            booking = get_object_or_404(
                PoojaBooking.objects.select_for_update(),
                id=booking_id,
                user=request.user
            )
            
            # Can only cancel pending or approved bookings
            if booking.status not in ['pending', 'approved']:
                messages.error(request, f"Cannot cancel {booking.status} booking.")
                return redirect('member_booking_history')
            
            # Process refund if payment was completed
            refund_id, refund_message = process_razorpay_refund(booking, request.user)
            
            # If approved, restore slot
            if booking.status == 'approved':
                booking.pooja.available_slots += 1
                booking.pooja.save()
            
            # Update booking status
            booking.status = 'cancelled'
            booking.cancelled_at = timezone.now()
            booking.payment_status = 'refunded' if refund_id else booking.payment_status
            booking.save()
            
            # Record cancellation in payment history
            PaymentHistory.objects.create(
                booking=booking,
                amount=-booking.amount if refund_id else 0,
                payment_mode='refund' if refund_id else 'cancellation',
                status='refunded' if refund_id else 'cancelled',
                reference_id=refund_id,
                notes=f'Cancelled by user. {refund_message}',
                confirmed_by=request.user,
                confirmed_at=timezone.now()
            )
            
            if refund_id:
                messages.success(request, f"Booking cancelled. {refund_message}")
            else:
                messages.warning(request, f"Booking cancelled but refund failed: {refund_message}")
            
            logger.info(f"Booking {booking_id} cancelled by user {request.user.id}")
            
    except Exception as e:
        logger.error(f"Error cancelling booking: {str(e)}", exc_info=True)
        messages.error(request, f"Error cancelling booking: {str(e)}")
    
    return redirect('member_booking_history')


def process_razorpay_refund(booking, user):
    """Helper function to process Razorpay refund"""
    if not all([booking.payment_status == 'completed', 
                booking.payment_method == 'upi', 
                booking.payment_id]):
        return None, "Refund not applicable for this booking"
    
    try:
        import razorpay
        from razorpay.errors import BadRequestError, ServerError
        from requests.exceptions import RequestException
        
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        
        # First verify the payment exists
        try:
            payment = client.payment.fetch(booking.payment_id)
            logger.info(f"Found payment for booking {booking.id}: {payment.get('id')}, status: {payment.get('status')}")
            
            # Check if already refunded
            if payment.get('refund_status') == 'partial' or payment.get('refund_status') == 'full':
                refunds = payment.get('refunds', [])
                if refunds:
                    refund = refunds[0]  # Get the most recent refund
                    logger.warning(f"Payment already has refunds. Most recent refund ID: {refund.get('id')}")
                    return refund.get('id'), "Refund already processed"
                
        except RequestException as e:
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
                error_msg = f"Payment {booking.payment_id} not found in Razorpay for booking {booking.id}"
                logger.error(error_msg)
                return None, error_msg
        except Exception as e:
            logger.warning(f"Error checking payment {booking.payment_id} for booking {booking.id}: {str(e)}")
            # Continue with refund attempt as the payment might still exist
        
        # Create new refund with detailed logging
        try:
            refund_data = {
                'amount': int(booking.amount * 100),  # Convert to paise
                'speed': 'normal',
                'receipt': f"REFUND_{booking.id}",
                'notes': {
                    'booking_id': str(booking.id),
                    'reason': 'user_cancellation',
                    'initiated_by': f'user_{user.id}'
                }
            }
            
            logger.info(f"Attempting refund for booking {booking.id}, payment {booking.payment_id}")
            # Process the refund
            refund = client.payment.refund(booking.payment_id, refund_data)
            
            if not refund or 'id' not in refund:
                logger.error(f"Invalid refund response: {refund}")
                return None, "Invalid response from payment processor"
                
            refund_id = refund['id']
            logger.info(f"Refund initiated for booking {booking.id}. Refund ID: {refund_id}")
            
            # Add a small delay to allow Razorpay to process the refund
            import time
            time.sleep(2)  # 2 second delay
            
            try:
                # Try to get the latest payment status with refunds
                payment = client.payment.fetch(booking.payment_id, {'expand[]': 'refunds'})
                refunds = payment.get('refunds', {}).get('items', [])
                
                # Try to find our refund in the list
                matching_refund = next((r for r in refunds if r.get('id') == refund_id), None)
                
                if matching_refund:
                    status = matching_refund.get('status', 'unknown')
                    logger.info(f"Refund {refund_id} status: {status}")
                    
                    if status == 'processed':
                        return refund_id, "Refund processed successfully"
                    elif status in ['pending', 'queued']:
                        logger.info(f"Refund {refund_id} is {status}, waiting for processing...")
                        return refund_id, f"Refund {status}. Please check Razorpay dashboard for details."
                    else:
                        return refund_id, f"Refund {status}. Please check Razorpay dashboard for details."
                
                # If we get here, refund not found in the list
                logger.warning(f"Refund {refund_id} not found in payment {booking.payment_id}")
                return refund_id, "Refund initiated but could not verify status. Please check Razorpay dashboard."
                    
            except Exception as e:
                logger.warning(f"Error verifying refund status: {str(e)}")
                return refund_id, "Refund initiated but could not verify status. Please check Razorpay dashboard."
                        
        except BadRequestError as e:
            error_msg = f"Bad request for refund: {str(e)}"
            if hasattr(e, 'error') and isinstance(e.error, dict):
                error_msg = e.error.get('description', error_msg)
            logger.error(f"Refund failed for booking {booking.id}: {error_msg}")
            return None, f"Refund failed: {error_msg}"
            
    except BadRequestError as e:
        error_msg = f"Invalid refund request for booking {booking.id}: {str(e)}"
        logger.error(error_msg)
        return None, error_msg
    except ServerError as e:
        error_msg = f"Razorpay server error for booking {booking.id}: {str(e)}"
        logger.error(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Error processing refund for booking {booking.id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return None, error_msg


@admin_required
@require_POST
def admin_refund_booking(request, booking_id):
    """
    Admin-only endpoint to process refund for a booking
    Can be used when auto-refund fails or for manual refunds
    """
    try:
        with transaction.atomic():
            booking = get_object_or_404(
                PoojaBooking.objects.select_for_update(),
                id=booking_id
            )
            
            # Only process refund for completed payments that aren't already refunded
            if booking.payment_status != 'completed':
                messages.error(request, f"Cannot refund a {booking.payment_status} payment.")
                return redirect('admin_booking_detail', booking_id=booking_id)
            
            # Process refund
            refund_id, refund_message = process_razorpay_refund(booking, request.user)
            
            if refund_id:
                booking.payment_status = 'refunded'
                booking.save()
                
                # Record refund in payment history
                PaymentHistory.objects.create(
                    booking=booking,
                    amount=-booking.amount,
                    payment_mode='refund',
                    status='refunded',
                    reference_id=refund_id,
                    notes=f'Refund processed by admin. {refund_message}',
                    confirmed_by=request.user,
                    confirmed_at=timezone.now()
                )
                
                messages.success(request, f"Refund successful. {refund_message}")
                logger.info(f"Admin {request.user.id} processed refund for booking {booking_id}. Refund ID: {refund_id}")
            else:
                messages.error(request, f"Refund failed: {refund_message}")
                
    except Exception as e:
        logger.error(f"Error processing refund for booking {booking_id}: {str(e)}", exc_info=True)
        messages.error(request, f"Error processing refund: {str(e)}")
    
    return redirect('admin_booking_detail', booking_id=booking_id)



# SECTION 3: OFFLINE PAYMENT FLOW


@member_required
@require_http_methods(["GET", "POST"])
def offline_book_pooja(request, pooja_id):
    """
    Offline booking (UPI QR or Cash)
    Creates booking in PENDING state
    No payment verification needed - admin approves later
    """
    member = request.user
    pooja = get_object_or_404(Pooja, id=pooja_id)

    if request.method == "POST":
        # Form submission
        payment_method = request.POST.get('payment_method', 'cash').strip()
        devotee_name = request.POST.get('devotee_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        nakshatra = request.POST.get('nakshatra', '').strip()

        # Validations
        if request.user.role != "member":
            messages.error(request, "Only members can book.")
            return redirect("pooja:services")

        # Check for existing booking if multiple bookings are not allowed for this pooja
        if not pooja.allow_multiple_bookings:
            if PoojaBooking.objects.filter(
                user=member,
                pooja=pooja,
                status__in=['pending', 'approved', 'completed']
            ).exists():
                messages.error(request, "You have already booked this pooja.")
                return redirect("pooja:services")

        if pooja.available_slots <= 0:
            messages.error(request, "No available slots.")
            return redirect("pooja:services")

        if payment_method not in ['upi_qr', 'cash']:
            messages.error(request, "Invalid payment method.")
            return redirect("pooja:services")

        # Create pending booking
        try:
            with transaction.atomic():
                locked_pooja = Pooja.objects.select_for_update().get(id=pooja_id)

                if locked_pooja.available_slots <= 0:
                    messages.error(request, "No slots available.")
                    return redirect("pooja:services")

                # Create PENDING booking with offline method
                booking = PoojaBooking.objects.create(
                    user=member,
                    pooja=locked_pooja,
                    amount=locked_pooja.amount,
                    payment_method=payment_method,
                    payment_status='pending_cash' if payment_method == 'cash' else 'pending',
                    status='pending',
                    devotee_name=devotee_name,
                    phone_number=phone,
                    nakshatra=nakshatra,
                    booked_at=timezone.now(),
                )

                # Record payment history as pending
                PaymentHistory.objects.create(
                    booking=booking,
                    amount=booking.amount,
                    payment_mode='upi_qr' if payment_method == 'upi_qr' else 'cash',
                    status='pending',
                    confirmed_by=None,
                )

                logger.info(f"Offline booking created: {booking.id}, method: {payment_method}")
                messages.success(request, "Booking submitted for admin approval!")
                return redirect('offline_booking_success', booking_id=booking.id)

        except Exception as e:
            logger.error(f"Offline booking creation failed: {str(e)}")
            messages.error(request, "Booking creation failed.")
            return redirect("pooja:services")

    else:
        # GET: Display offline booking form
        if request.user.role != "member":
            messages.error(request, "Only members can book.")
            return redirect("pooja:services")

        # Get site settings
        from temple_admin.models import SiteSettings
        site_settings = SiteSettings.objects.first()
        if site_settings is None:
            site_settings = SiteSettings.objects.create()

        # Check for existing booking if multiple bookings are not allowed
        if not site_settings.allow_multiple_bookings:
            if PoojaBooking.objects.filter(
                user=member,
                pooja=pooja,
                status__in=['pending', 'approved', 'completed']
            ).exists():
                messages.error(request, "You have already booked this pooja.")
                return redirect("pooja:services")

        if pooja.available_slots <= 0:
            messages.error(request, "No available slots.")
            return redirect("pooja:services")

        context = {
            'pooja': pooja,
            'member': member,
            'is_offline': True,
        }

        return render(request, "booking/offline_book_pooja.html", context)


@member_required
def offline_booking_success(request, booking_id):
    """
    Success page for offline booking
    Shows pending approval message
    """
    try:
        booking = get_object_or_404(
            PoojaBooking,
            id=booking_id,
            user=request.user,
            status='pending'
        )
        
        context = {
            'booking': booking,
            'is_offline': True,
            'payment_method_display': dict(booking.PAYMENT_METHOD_CHOICES)[booking.payment_method],
        }
        
        return render(request, 'booking/offline_booking_success.html', context)
    
    except Exception as e:
        logger.error(f"Error displaying offline success: {str(e)}")
        messages.error(request, "Error loading booking details.")
        return redirect('pooja:services')



# SECTION 4: ADMIN APPROVAL APIs


@require_POST
@admin_required
def api_approve_booking(request):
    """
    Admin approves a pending booking
    Transitions: pending → approved
    Decrements slot count
    """
    try:
        data = json.loads(request.body)
        booking_id = data.get('booking_id')

        if not booking_id:
            return JsonResponse({'success': False, 'message': 'Missing booking_id'}, status=400)

        booking = get_object_or_404(PoojaBooking, id=booking_id)

        # Validate: booking must be pending
        if booking.status != 'pending':
            return JsonResponse({
                'success': False,
                'message': f'Booking is in {booking.status} state, cannot approve'
            }, status=400)

        try:
            with transaction.atomic():
                # Lock pooja
                locked_pooja = Pooja.objects.select_for_update().get(id=booking.pooja_id)

                # Final check: slots still available
                if locked_pooja.available_slots <= 0:
                    return JsonResponse({
                        'success': False,
                        'message': 'No slots available anymore'
                    }, status=400)

                # Approve booking using the model method which handles email sending
                booking.approve(request.user)

                # Decrement slot (NOW, not during booking)
                locked_pooja.available_slots -= 1
                locked_pooja.save(update_fields=['available_slots'])

                # Mark payment as paid (if offline payment pending)
                if booking.payment_status == 'pending':
                    booking.payment_status = 'completed'
                    booking.payment_completed_at = timezone.now()
                    booking.save()

                    # Update payment history
                    payment_record = PaymentHistory.objects.filter(
                        booking=booking,
                        status='pending'
                    ).first()
                    if payment_record:
                        payment_record.status = 'paid'
                        payment_record.confirmed_by = request.user
                        payment_record.confirmed_at = timezone.now()
                        payment_record.save()

                logger.info(f"Booking {booking_id} approved by {request.user.id}")

                return JsonResponse({
                    'success': True,
                    'message': 'Booking approved successfully',
                    'booking': {
                        'id': booking.id,
                        'status': booking.status,
                        'approved_at': booking.approved_at.isoformat(),
                    }
                })

        except Exception as e:
            logger.error(f"Error approving booking: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Error approving booking'
            }, status=500)

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'success': False, 'message': 'Server error'}, status=500)


@require_POST
@admin_required
def api_cancel_booking(request):
    """
    Admin cancels a pending or approved booking
    Transitions: pending/approved → cancelled
    Restores slot if approved
    """
    try:
        data = json.loads(request.body)
        booking_id = data.get('booking_id')
        reason = data.get('reason', 'No reason provided')

        if not booking_id:
            return JsonResponse({'success': False, 'message': 'Missing booking_id'}, status=400)

        booking = get_object_or_404(PoojaBooking, id=booking_id)

        # Validate: booking must be pending or approved
        if booking.status not in ['pending', 'approved']:
            return JsonResponse({
                'success': False,
                'message': f'Cannot cancel {booking.status} booking'
            }, status=400)

        try:
            with transaction.atomic():
                was_approved = booking.status == 'approved'

                # Cancel booking
                booking.status = 'cancelled'
                booking.cancelled_at = timezone.now()
                booking.updated_by = request.user
                booking.save()

                # Restore slot if it was approved
                if was_approved:
                    booking.pooja.available_slots += 1
                    booking.pooja.save(update_fields=['available_slots'])

                # Record cancellation in payment history
                PaymentHistory.objects.create(
                    booking=booking,
                    amount=booking.amount,
                    payment_mode=booking.payment_method,
                    status='failed',
                    confirmed_by=request.user,
                    notes=f'Cancelled: {reason}'
                )

                logger.info(f"Booking {booking_id} cancelled by {request.user.id}. Reason: {reason}")

                return JsonResponse({
                    'success': True,
                    'message': 'Booking cancelled successfully',
                    'booking': {
                        'id': booking.id,
                        'status': booking.status,
                        'cancelled_at': booking.cancelled_at.isoformat(),
                    }
                })

        except Exception as e:
            logger.error(f"Error cancelling booking: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Error cancelling booking'
            }, status=500)

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'success': False, 'message': 'Server error'}, status=500)



# SECTION 5: ADMIN DASHBOARD VIEWS

@admin_required
def admin_all_bookings(request):
    """
    Admin view for all bookings with filters
    """
    # Get filters from query params
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    pooja_filter = request.GET.get('pooja', '')
    payment_method_filter = request.GET.get('payment_method', '')

    # Get all bookings
    bookings = PoojaBooking.objects.all().select_related('user', 'pooja', 'updated_by')

    # Apply filters
    if status_filter:
        bookings = bookings.filter(status=status_filter)

    if payment_method_filter:
        bookings = bookings.filter(payment_method=payment_method_filter)

    if pooja_filter:
        bookings = bookings.filter(pooja_id=pooja_filter)

    if date_from:
        try:
            from datetime import datetime
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            bookings = bookings.filter(booked_at__date__gte=from_date)
        except ValueError:
            pass

    if date_to:
        try:
            from datetime import datetime
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            bookings = bookings.filter(booked_at__date__lte=to_date)
        except ValueError:
            pass

    # Order by newest first
    bookings = bookings.order_by('-booked_at')

    # Pagination
    paginator = Paginator(bookings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Stats
    total_pending = PoojaBooking.objects.filter(status='pending').count()
    total_approved = PoojaBooking.objects.filter(status='approved').count()
    total_cancelled = PoojaBooking.objects.filter(status='cancelled').count()

    # Get all poojas for filter
    poojas = Pooja.objects.all()

    context = {
        'page_obj': page_obj,
        'bookings': page_obj.object_list,
        'poojas': poojas,
        'total_pending': total_pending,
        'total_approved': total_approved,
        'total_cancelled': total_cancelled,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'pooja_filter': pooja_filter,
        'payment_method_filter': payment_method_filter,
    }

    return render(request, 'booking/admin_all_bookings.html', context)


@admin_required
def admin_member_bookings(request, user_id):
    """
    Admin view for specific member's bookings
    """
    member = get_object_or_404(get_user_model(), id=user_id)
    bookings = PoojaBooking.objects.filter(user=member).select_related('pooja')
    total_bookings = PoojaBooking.objects.filter(user=member).count()
    completed_bookings = PoojaBooking.objects.filter(user=member, status='cancelled').count()
    pending_bookings = PoojaBooking.objects.filter(user=member, status='pending').count()
    cancelled_bookings = PoojaBooking.objects.filter(user=member, status='cancelled').count()
    # Pagination
    paginator = Paginator(bookings, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'member': member,
        'page_obj': page_obj,
        'bookings': page_obj.object_list,
        'total_bookings': total_bookings,
        'completed_bookings': completed_bookings,
        'pending_bookings': pending_bookings,
        'cancelled_bookings': cancelled_bookings,
    }

    return render(request, 'booking/admin_member_bookings.html', context)


@admin_required
def admin_payment_history(request):
    """
    Admin view for payment history
    """
    # Get filters from query params
    payment_mode_filter = request.GET.get('payment_mode', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('search', '')

    # Start with all payment history
    history = PaymentHistory.objects.all().select_related('booking', 'booking__user', 'confirmed_by')

    # Apply filters
    if payment_mode_filter:
        history = history.filter(payment_mode=payment_mode_filter)

    if date_from:
        try:
            from datetime import datetime
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            history = history.filter(confirmed_at__date__gte=from_date)
        except ValueError:
            pass

    if date_to:
        try:
            from datetime import datetime
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            history = history.filter(confirmed_at__date__lte=to_date)
        except ValueError:
            pass

    if search_query:
        history = history.filter(
            Q(booking__id__icontains=search_query) |
            Q(booking__user__username__icontains=search_query)
        )

    # Order and paginate
    history = history.order_by('-confirmed_at')

    paginator = Paginator(history, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'payment_history': page_obj.object_list,
        'payment_mode_filter': payment_mode_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
    }

    return render(request, 'booking/admin_payment_history.html', context)



@admin_required
def api_admin_bookings_list(request):
    """
    Return paginated list of bookings for admin
    """
    try:
        # Get filters from query params
        status_filter = request.GET.get('status', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        pooja_filter = request.GET.get('pooja', '')
        payment_method_filter = request.GET.get('payment_method', '')
        page = request.GET.get('page', 1)

        # Start with all bookings
        bookings = PoojaBooking.objects.all().select_related('user', 'pooja')

        # Apply filters
        if status_filter:
            bookings = bookings.filter(status=status_filter)

        if payment_method_filter:
            bookings = bookings.filter(payment_method=payment_method_filter)

        if pooja_filter:
            bookings = bookings.filter(pooja_id=pooja_filter)

        if date_from:
            try:
                from datetime import datetime
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                bookings = bookings.filter(booked_at__date__gte=from_date)
            except ValueError:
                pass

        if date_to:
            try:
                from datetime import datetime
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                bookings = bookings.filter(booked_at__date__lte=to_date)
            except ValueError:
                pass

        # Order by newest first
        bookings = bookings.order_by('-booked_at')

        # Pagination
        paginator = Paginator(bookings, 20)
        page_obj = paginator.get_page(page)

        # Build response
        data = {
            'success': True,
            'bookings': [
                {
                    'id': b.id,
                    'user': b.user.username,
                    'user_email': b.user.email,
                    'pooja': b.pooja.name,
                    'amount': str(b.amount),
                    'status': b.status,
                    'payment_method': b.payment_method,
                    'payment_status': b.payment_status,
                    'booked_at': b.booked_at.isoformat(),
                    'approved_at': b.approved_at.isoformat() if b.approved_at else None,
                }
                for b in page_obj.object_list
            ],
            'pagination': {
                'page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }

        return JsonResponse(data)

    except Exception as e:
        logger.error(f"Error fetching bookings: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Error fetching bookings'
        }, status=500)


@admin_required
def api_payments_history(request):
    """
    API endpoint to fetch payment history
    """
    try:
        # Get filters
        payment_mode_filter = request.GET.get('payment_mode', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        booking_id_filter = request.GET.get('booking_id', '')
        page = request.GET.get('page', 1)

        # Get history
        history = PaymentHistory.objects.all().select_related('booking', 'booking__user', 'confirmed_by')

        # Apply filters
        if payment_mode_filter:
            history = history.filter(payment_mode=payment_mode_filter)

        if booking_id_filter:
            history = history.filter(booking_id=booking_id_filter)

        if date_from:
            try:
                from datetime import datetime
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                history = history.filter(confirmed_at__date__gte=from_date)
            except ValueError:
                pass

        if date_to:
            try:
                from datetime import datetime
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                history = history.filter(confirmed_at__date__lte=to_date)
            except ValueError:
                pass

        # Order and paginate
        history = history.order_by('-confirmed_at')

        paginator = Paginator(history, 20)
        page_obj = paginator.get_page(page)

        # Build response
        data = {
            'success': True,
            'payment_history': [
                {
                    'id': h.id,
                    'booking_id': h.booking_id,
                    'pooja': h.booking.pooja.name,
                    'user': h.booking.user.username,
                    'amount': str(h.amount),
                    'payment_mode': h.payment_mode,
                    'status': h.status,
                    'confirmed_by': h.confirmed_by.username if h.confirmed_by else None,
                    'confirmed_at': h.confirmed_at.isoformat(),
                }
                for h in page_obj.object_list
            ],
            'pagination': {
                'page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
            }
        }

        return JsonResponse(data)

    except Exception as e:
        logger.error(f"Error fetching payment history: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Error fetching history'
        }, status=500)

@require_POST
@admin_required
def api_mark_as_paid(request):

    try:
        data = json.loads(request.body)
        booking_id = data.get('booking_id')
        
        if not booking_id:
            return JsonResponse({'success': False, 'message': 'Missing booking_id'}, status=400)
        
        booking = get_object_or_404(PoojaBooking, id=booking_id)
        
        # Validate: only offline bookings
        if booking.payment_method not in ['upi_qr', 'cash']:
            return JsonResponse({
                'success': False,
                'message': f'Only offline bookings can be marked as paid'
            }, status=400)
        
        # Validate: payment must be pending
        if booking.payment_status != 'pending':
            return JsonResponse({
                'success': False,
                'message': f'Payment is already {booking.payment_status}'
            }, status=400)
        
        try:
            with transaction.atomic():
                # Mark payment as completed
                booking.payment_status = 'completed'
                booking.payment_completed_at = timezone.now()
                booking.updated_by = request.user
                booking.save()
                
                # Update payment history
                payment_record = PaymentHistory.objects.filter(
                    booking=booking,
                    status='pending'
                ).first()
                
                if payment_record:
                    payment_record.status = 'paid'
                    payment_record.confirmed_by = request.user
                    payment_record.confirmed_at = timezone.now()
                    payment_record.save()
                
                logger.info(f"Payment marked as paid for booking {booking_id} by {request.user.id}")
                try:
                    # ✅ SEND EMAIL INSIDE TRANSACTION (before return)
                    send_booking_email(
                        subject="Payment Confirmed",
                        template_name="payment_cash.html",
                        to_email=booking.user.email,
                        context={
                            "name": booking.devotee_name or booking.user.username,
                            "booking_id": booking.id,
                            "amount": booking.amount,
                            "status": "Paid",
                            "date": booking.payment_completed_at.strftime("%d %B %Y"),
                        }
                    )  
                    logger.info("Payment confirmation email sent successfully")
                except Exception as email_error:
                    logger.error(f"Failed to send payment email: {str(email_error)}")
                return JsonResponse({
                    'success': True,
                    'message': 'Payment marked as completed',
                    'booking': {
                        'id': booking.id,
                        'payment_status': booking.payment_status,
                        'payment_completed_at': booking.payment_completed_at.isoformat(),
                    }
                })
        
        except Exception as e:
            logger.error(f"Error marking as paid: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Error marking as paid'
            }, status=500)
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'success': False, 'message': 'Server error'}, status=500)



# DRF
# approve booking 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def drf_approve_booking(request):
    serializer = BookingStatusSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    booking = get_object_or_404(
        PoojaBooking,
        id=serializer.validated_data['booking_id']
    )

    if booking.status != 'pending':
        return Response(
            {'error': f'Booking is {booking.status}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():
        pooja = Pooja.objects.select_for_update().get(id=booking.pooja_id)

        if pooja.available_slots <= 0:
            return Response(
                {'error': 'No slots available'},
                status=status.HTTP_400_BAD_REQUEST
            )

        booking.status = 'approved'
        booking.approved_at = timezone.now()
        booking.updated_by = request.user
        booking.save()

        pooja.available_slots -= 1
        pooja.save()

        if booking.payment_status == 'pending':
            booking.payment_status = 'completed'
            booking.payment_completed_at = timezone.now()
            booking.save()

    return Response({
    'success': True,
    'booking': {
        'id': booking.id,
        'status': booking.status,
        'payment_status': booking.payment_status,
        'approved_at': booking.approved_at,
    }
})


# cancel booking 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def drf_cancel_booking(request):
    serializer = BookingStatusSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    booking = get_object_or_404(
        PoojaBooking,
        id=serializer.validated_data['booking_id']
    )

    if booking.status not in ['pending', 'approved']:
        return Response(
            {'error': f'Cannot cancel {booking.status}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():
        was_approved = booking.status == 'approved'
        booking.status = 'cancelled'
        booking.cancelled_at = timezone.now()
        booking.updated_by = request.user
        booking.save()

        if was_approved:
            booking.pooja.available_slots += 1
            booking.pooja.save()

        PaymentHistory.objects.create(
            booking=booking,
            amount=booking.amount,
            payment_mode=booking.payment_method,
            status='failed',
            confirmed_by=request.user,
            notes=serializer.validated_data.get('reason', '')
        )

    return Response({
    'success': True,
    'booking': {
        'id': booking.id,
        'status': booking.status,
        'payment_status': booking.payment_status,
        'approved_at': booking.approved_at,
    }
})


# make offline payment as paid 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def drf_mark_as_paid(request):
    serializer = BookingStatusSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    booking = get_object_or_404(
        PoojaBooking,
        id=serializer.validated_data['booking_id']
    )

    if booking.payment_method not in ['upi_qr', 'cash']:
        return Response({'error': 'Not offline booking'}, status=400)

    if booking.payment_status != 'pending':
        return Response({'error': 'Already paid'}, status=400)

    with transaction.atomic():
        # Debug log 1: Starting transaction
        logger.info(f"Starting payment confirmation for booking {booking.id}")
        
        # Update booking status
        booking.payment_status = 'completed'
        booking.payment_completed_at = timezone.now()
        booking.updated_by = request.user
        booking.save()
        logger.info(f"Updated booking {booking.id} status to 'completed'")

        # Update payment history
        updated = PaymentHistory.objects.filter(
            booking=booking,
            status='pending'
        ).update(
            status='paid',
            confirmed_by=request.user,
            confirmed_at=timezone.now()
        )
        logger.info(f"Updated {updated} payment history records")
        
        # Prepare email context
        email_context = {
            'name': booking.devotee_name or booking.user.username,
            'booking_id': booking.id,
            'amount': booking.amount,
            'status': 'Paid',
            'payment_method': booking.get_payment_method_display(),
            'date': timezone.now().strftime('%d %B %Y')
        }
        
        logger.info(f"Preparing to send email to: {booking.user.email}")
        logger.info(f"Email context: {email_context}")
        
        # Send payment confirmation email
        try:
            logger.info("Attempting to send email...")
            send_booking_email(
                template_name='payment_cash.html',
                subject='Payment Confirmed',
                to_email=booking.user.email,
                context=email_context
            )
            logger.info("Email sent successfully")
        except Exception as e:
            logger.error(f"Failed to send payment confirmation email: {str(e)}", exc_info=True)

    return Response({
    'success': True,
    'booking': {
        'id': booking.id,
        'status': booking.status,
        'payment_status': booking.payment_status,
        'approved_at': booking.approved_at,
    }
})


# admin booking list
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def drf_admin_bookings_list(request):
    bookings = PoojaBooking.objects.select_related('user', 'pooja').order_by('-booked_at')

    paginator = Paginator(bookings, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    serializer = BookingListSerializer(page_obj.object_list, many=True)

    return Response({
        'results': serializer.data,
        'page': page_obj.number,
        'total_pages': paginator.num_pages
    })

# payment history 
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def drf_payment_history(request):
    history = PaymentHistory.objects.select_related(
        'booking', 'booking__user'
    ).order_by('-confirmed_at')

    paginator = Paginator(history, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    serializer = PaymentHistorySerializer(page_obj.object_list, many=True)

    return Response({
        'results': serializer.data,
        'page': page_obj.number,
        'total_pages': paginator.num_pages
    })

# drf view update-status
@api_view(['POST'])
@permission_classes([IsAdminOrOperator])
def drf_payment_update_status(request):
    """
    Manual payment confirmation API
    """

    serializer = PaymentStatusUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    booking = get_object_or_404(
        PoojaBooking,
        id=serializer.validated_data['booking_id']
    )

    with transaction.atomic():
        booking.payment_status = serializer.validated_data['status']
        booking.payment_method = serializer.validated_data['payment_method']
        booking.payment_completed_at = (
            timezone.now()
            if serializer.validated_data['status'] == 'completed'
            else None
        )
        booking.updated_by = request.user
        booking.save()

        # Update or create payment history
        PaymentHistory.objects.create(
            booking=booking,
            amount=booking.amount,
            payment_mode=serializer.validated_data['payment_method'],
            status='paid' if serializer.validated_data['status'] == 'completed' else 'failed',
            confirmed_by=request.user,
            confirmed_at=timezone.now()
        )

    return Response(
        {
            'success': True,
            'booking_id': booking.id,
            'payment_status': booking.payment_status,
            'payment_method': booking.payment_method
        },
        status=status.HTTP_200_OK
    )

@require_POST
@admin_required
def api_mark_cash_paid(request):
    data = json.loads(request.body)
    booking_id = data.get('booking_id')

    booking = get_object_or_404(PoojaBooking, id=booking_id)

    if booking.payment_status not in ['pending_cash', 'pending']:
        return JsonResponse({'success': False, 'message': 'Not a pending cash/QR payment'}, status=400)

    booking.payment_status = 'paid_cash' if booking.payment_status == 'pending_cash' else 'paid_qr'
    booking.payment_completed_at = timezone.now()
    booking.updated_by = request.user
    booking.save()

    PaymentHistory.objects.create(
        booking=booking,
        amount=booking.amount,
        payment_mode='cash',
        status='paid',
        confirmed_by=request.user,
        confirmed_at=timezone.now()
    )
    # ✅ SEND EMAIL BEFORE RETURN
    send_booking_email(
        subject="Cash Payment Confirmed",
        template_name="payment_cash.html",
        to_email=booking.user.email,
        context={
            "name": booking.devotee_name or booking.user.username,
            "booking_id": booking.id,
            "amount": booking.amount,
            "status": "Paid (Cash)",
            "date": booking.payment_completed_at.strftime("%d %B %Y"),
        }
    )

    return JsonResponse({'success': True})


# ADMIN REPORT view
@admin_required
def admin_daily_report_page(request):
    return render(request, "booking/admin_daily_report.html")



PAID_STATUSES = ["paid_online", "paid_cash"]


@api_view(["GET"])
@permission_classes([IsAdminOrOperator])
def admin_booking_report_api(request):

    # 1️⃣ READ QUERY PARAMS
    search = request.GET.get("search")
    payment_method = request.GET.get("payment_method")
    booking_status = request.GET.get("booking_status")
    payment_status = request.GET.get("payment_status")
    single_date = request.GET.get("date")
    from_date = request.GET.get("from")
    to_date = request.GET.get("to")
    export = request.GET.get("export")  # csv

    # 2️⃣ BASE QUERYSET
    bookings = (
        PoojaBooking.objects
        .select_related("pooja", "user")
        .all()
    )

    # 3️⃣ DATE FILTER
    if single_date:
        parsed_date = parse_date(single_date)
        if not parsed_date:
            return Response(
                {"error": "Invalid date format (YYYY-MM-DD)"},
                status=status.HTTP_400_BAD_REQUEST
            )
        bookings = bookings.filter(pooja__pooja_date=parsed_date)

    elif from_date and to_date:
        start = parse_date(from_date)
        end = parse_date(to_date)

        if not start or not end:
            return Response(
                {"error": "Invalid date range"},
                status=status.HTTP_400_BAD_REQUEST
            )

        bookings = bookings.filter(pooja__pooja_date__range=(start, end))

    # 4️⃣ BOOKING STATUS
    if booking_status:
        bookings = bookings.filter(status=booking_status)

    # 5️⃣ PAYMENT STATUS
    if payment_status == "paid":
        bookings = bookings.filter(payment_status__in=PAID_STATUSES)
    elif payment_status == "unpaid":
        bookings = bookings.filter(payment_status__in=["pending", "pending_cash"])

    # 6️⃣ PAYMENT METHOD
    if payment_method:
        bookings = bookings.filter(payment_method=payment_method)

    # 7️⃣ SEARCH (DEVOTEE NAME)
    if search:
        bookings = bookings.filter(devotee_name__icontains=search)

    # 8️⃣ ORDERING
    bookings = bookings.order_by("-booked_at")

    # 9️⃣ CSV EXPORT (IF REQUESTED)
    if export == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="booking_report.csv"'
        response["X-Frame-Options"] = 'SAMEORIGIN'  # For iframe compatibility
        
        # Create CSV writer
        writer = csv.writer(response)
        
        # Write headers
        writer.writerow([
            "Booking ID",
            "Pooja",
            "Devotee",
            "Pooja Date",
            "Booking Date",
            "Amount",
            "Payment Status",
            "Payment Method",
            "Booking Status",
        ])

        # Write data rows
        for b in bookings:
            writer.writerow([
                b.id,
                b.pooja.name,
                b.devotee_name,
                b.pooja.pooja_date.strftime('%Y-%m-%d') if b.pooja.pooja_date else '',
                b.booked_at.strftime('%Y-%m-%d %H:%M:%S') if b.booked_at else '',
                str(b.amount or b.pooja.amount or '0.00'),
                b.payment_status or '',
                b.payment_method or '',
                b.status or '',
            ])

        return response

    # 🔟 SUMMARY DATA (EXCLUDE CANCELLED)
    report_bookings = bookings.exclude(status="cancelled")

    total_bookings = report_bookings.count()

    total_revenue = (
        report_bookings
        .filter(payment_status__in=PAID_STATUSES)
        .aggregate(
            total=Sum(
                Case(
                    When(amount__isnull=False, then="amount"),
                    default=0,
                    output_field=DecimalField()
                )
            )
        )["total"] or 0
    )

    # 1️⃣1️⃣ GROUP BY POOJA
    pooja_summary = list(
        report_bookings
        .filter(payment_status__in=PAID_STATUSES)
        .values("pooja__name")
        .annotate(
            booking_count=Count("id"),
            total_amount=Sum("amount")
        )
        .order_by("-total_amount")
    )

    # 1️⃣2️⃣ GROUP BY PAYMENT METHOD
    payment_summary = list(
        report_bookings
        .filter(payment_status__in=PAID_STATUSES)
        .values("payment_method")
        .annotate(
            booking_count=Count("id"),
            total_amount=Sum("amount")
        )
    )

    # 1️⃣3️⃣ TABLE DATA
    booking_list = []
    for b in bookings:
        booking_list.append({
            "booking_id": b.id,
            "pooja_name": b.pooja.name,
            "devotee_name": b.devotee_name,
            "pooja_date": b.pooja.pooja_date,
            "booking_date": b.booked_at,
            "amount": float(b.amount or b.pooja.amount),
            "payment_status": b.payment_status,
            "payment_method": b.payment_method,
            "booking_status": b.status,
        })

    # 1️⃣4️⃣ FINAL RESPONSE
    return Response({
        "summary": {
            "total_bookings": total_bookings,
            "total_revenue": float(total_revenue),
        },
        "grouped_by_pooja": pooja_summary,
        "grouped_by_payment_method": payment_summary,
        "bookings": booking_list,
    })

CASH_METHODS = ["cash"]
UPI_METHODS = ["upi", "upi_qr"]

@api_view(["GET"])
@permission_classes([IsAdminOrOperator])
def admin_payment_report_api(request):

    from_date = request.GET.get("from")
    to_date = request.GET.get("to")

    bookings = PoojaBooking.objects.filter(
        payment_status__in=PAID_STATUSES
    )

    if from_date and to_date:
        start = parse_date(from_date)
        end = parse_date(to_date)
        bookings = bookings.filter(
            pooja__pooja_date__range=(start, end)
        )

    cash_total = bookings.filter(
        payment_method__in=CASH_METHODS
    ).aggregate(
        amount=Sum("amount"),
        count=Count("id")
    )

    upi_total = bookings.filter(
        payment_method__in=UPI_METHODS
    ).aggregate(
        amount=Sum("amount"),
        count=Count("id")
    )

    cash_amount = cash_total["amount"] or 0
    upi_amount = upi_total["amount"] or 0

    response = {
        "summary": {
            "cash_total": float(cash_amount),
            "upi_total": float(upi_amount),
            "grand_total": float(cash_amount + upi_amount)
        },
        "breakdown": [
            {
                "payment_method": "cash",
                "booking_count": cash_total["count"],
                "total_amount": float(cash_amount)
            },
            {
                "payment_method": "upi",
                "booking_count": upi_total["count"],
                "total_amount": float(upi_amount)
            }
        ]
    }

    return Response(response, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAdminOrOperator])
def admin_payment_report_csv(request):

    from_date = request.GET.get("from")
    to_date = request.GET.get("to")

    bookings = PoojaBooking.objects.filter(
        payment_status__in=PAID_STATUSES
    )

    if from_date and to_date:
        start = parse_date(from_date)
        end = parse_date(to_date)
        bookings = bookings.filter(
            pooja__pooja_date__range=(start, end)
        )

    cash_data = bookings.filter(
        payment_method__in=CASH_METHODS
    ).aggregate(
        count=Count("id"),
        amount=Sum("amount")
    )

    upi_data = bookings.filter(
        payment_method__in=UPI_METHODS
    ).aggregate(
        count=Count("id"),
        amount=Sum("amount")
    )

    cash_amount = cash_data["amount"] or 0
    upi_amount = upi_data["amount"] or 0
    grand_total = cash_amount + upi_amount

    # ---- CREATE CSV RESPONSE ----
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="payment_report.csv"'
    )

    writer = csv.writer(response)

    # Header row
    writer.writerow([
        "Payment Method",
        "Number of Bookings",
        "Total Amount",
        "Percentage Share"
    ])

    # Helper for percentage
    def pct(amount):
        return round((amount / grand_total) * 100, 2) if grand_total else 0

    # Cash row
    writer.writerow([
        "Cash",
        cash_data["count"],
        cash_amount,
        pct(cash_amount)
    ])

    # UPI row
    writer.writerow([
        "UPI",
        upi_data["count"],
        upi_amount,
        pct(upi_amount)
    ])

    return response

@admin_required
def admin_payment_report_page(request):
    return render(request, "booking/admin_payment_report.html")

@api_view(["GET"])
@permission_classes([IsAdminOrOperator])
def admin_member_booking_history_api(request, member_id):

    # -------- VALIDATION --------
    try:
        member = User.objects.get(id=member_id)
    except User.DoesNotExist:
        return Response(
            {"error": "Member not found"},
            status=404
        )

    # -------- FILTER PARAMS --------
    status_filter = request.GET.get("status")
    from_date = request.GET.get("from")
    to_date = request.GET.get("to")
    page = int(request.GET.get("page", 1))
    page_size = 10

    # -------- BASE QUERY --------
    bookings = (
        PoojaBooking.objects
        .select_related("pooja")
        .filter(user=member, is_deleted=False)
        .order_by("-booked_at")
    )

    # -------- DATE FILTER --------
    if from_date and to_date:
        bookings = bookings.filter(
            booked_at__date__range=(from_date, to_date)
        )

    # -------- STATUS FILTER --------
    if status_filter:
        bookings = bookings.filter(status=status_filter)

    # -------- PAGINATION --------
    paginator = Paginator(bookings, page_size)
    page_obj = paginator.get_page(page)

    # -------- RESPONSE DATA --------
    booking_list = []
    total_paid = 0

    for b in page_obj:
        if b.payment_status in ["paid_online", "paid_cash"]:
            total_paid += b.amount or 0

        booking_list.append({
            "id": b.id,
            "pooja_name": b.pooja.name,
            "pooja_date": b.pooja.pooja_date,
            "booking_date": b.booked_at,
            "payment_mode": b.payment_method,
            "amount": float(b.amount or 0),
            "booking_status": b.status,
            "payment_status": b.payment_status,
        })

    return Response({
        "member": {
            "id": member.id,
            "name": member.get_full_name(),
            "email": member.email,
            "phone":  u.phone_number or "",
        },
        "summary": {
            "total_bookings": bookings.count(),
            "total_paid": float(total_paid)
        },
        "bookings": booking_list,
        "pagination": {
            "current_page": page,
            "total_pages": paginator.num_pages
        }
    })

@admin_required
def admin_member_list_page(request):
    return render(request, "booking/admin_members.html")

@api_view(["GET"])
@permission_classes([IsAdminOrOperator])
def admin_member_list_api(request):
    search = request.GET.get("search", "")
    page = int(request.GET.get("page", 1))

    qs = User.objects.filter(is_staff=False)

    if search:
        qs = qs.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search)
        )

    qs = qs.order_by("first_name")

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(page)

    data = []
    for u in page_obj:
        data.append({
            "id": u.id,
            "name": f"{u.first_name} {u.last_name}".strip() or u.username,
            "username": u.username,
            "email": u.email,
            "phone":  u.phone_number or "",
            "date_joined": u.date_joined.date(),
            "is_active": u.is_active,
        })

    return Response({
        "results": data,
        "page": page,
        "total_pages": paginator.num_pages,
        "total_members": paginator.count,
    })

@api_view(['GET'])
@permission_classes([IsAdminOrOperator])
def admin_member_bookings_api(request, member_id):

    member = User.objects.filter(id=member_id, is_staff=False).first()
    if not member:
        return Response({"error": "Member not found"}, status=404)

    status_filter = request.GET.get("status")
    from_date = request.GET.get("from")
    to_date = request.GET.get("to")
    page = int(request.GET.get("page", 1))

    qs = (
        PoojaBooking.objects
        .select_related("pooja")
        .filter(user=member)
        .exclude(status="deleted")
        .order_by("-booked_at")
    )

    if status_filter:
        qs = qs.filter(status=status_filter)

    if from_date and to_date:
        qs = qs.filter(pooja__pooja_date__range=[from_date, to_date])

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(page)

    bookings = []
    for b in page_obj:
        bookings.append({
            "id": b.id,
            "pooja": b.pooja.name,
            "pooja_date": b.pooja.pooja_date,
            "booking_date": b.booked_at.date(),
            "payment_mode": b.payment_method,
            "amount": float(b.amount or b.pooja.amount),
            "booking_status": b.status,
            "payment_status": b.payment_status,
        })

    return Response({
        "member": {
            "id": member.id,
            "name": member.get_full_name() or member.username,
            "email": member.email,
            "phone": getattr(member, "phone", ""),
        },
        "results": bookings,
        "page": page,
        "total_pages": paginator.num_pages,
        "total_bookings": qs.count(),
    })

@admin_required
def admin_member_bookings_page(request, member_id):
    """
    Admin page: show all bookings of a single member
    """
    member = get_object_or_404(User, id=member_id, is_staff=False)

    bookings = (
        PoojaBooking.objects
        .select_related("pooja")
        .filter(user=member)
        .order_by("-booked_at")
    )

    # Calculate summary statistics
    total_bookings = bookings.count()
    total_amount = sum(b.amount or 0 for b in bookings if b.payment_status in ['paid_online', 'paid_cash'])
    
    # Count bookings by status
    status_counts = {}
    for status in ['pending', 'approved', 'completed', 'cancelled']:
        status_counts[status] = bookings.filter(status=status).count()
    
    return render(
        request,
        "booking/admin_main_member_bookings.html",
        {
            "member": member,
            "bookings": bookings,
            "total_bookings": total_bookings,
            "total_amount": total_amount,
            "status_counts": status_counts
        }
    )
