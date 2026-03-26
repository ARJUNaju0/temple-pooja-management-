# ========================================
# FILE 1: booking/utils/email_service.py
# Enhanced with logging, retry, and Celery support
# ========================================

import logging
from django.core.mail import EmailMultiAlternatives, BadHeaderError
from django.template.loader import render_to_string, TemplateDoesNotExist
from django.conf import settings
from datetime import datetime

logger = logging.getLogger(__name__)


def send_booking_email(template_name, subject, to_email, context, max_retries=3):
    """
    Send booking email with detailed logging and retry logic
    
    Args:
        template_name: Name of the email template (e.g., 'payment_cash.html')
        subject: Email subject line
        to_email: Recipient email address
        context: Template context dictionary
        max_retries: Number of retry attempts (default: 3)
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    attempt = 0
    last_error = None
    
    while attempt < max_retries:
        attempt += 1
        try:
            # Add year to context
            context["year"] = datetime.now().year
            template_path = f"emails/{template_name}"
            
            logger.info(
                f"[Attempt {attempt}/{max_retries}] Preparing email to {to_email} "
                f"using template '{template_path}' with subject '{subject}'"
            )
            
            # Validate email address
            if not to_email or '@' not in to_email:
                logger.error(f"Invalid email address: {to_email}")
                return False
            
            # Render HTML content
            try:
                html_content = render_to_string(template_path, context)
            except TemplateDoesNotExist:
                logger.error(f"Template not found: {template_path}")
                return False
            
            # Plain text fallback
            text_content = "Please view this email in HTML format."
            
            # Create email message
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to_email],
            )
            
            email.attach_alternative(html_content, "text/html")
            
            # Send email
            email.send(fail_silently=False)
            
            # Log success
            logger.info(
                f"✅ Email sent successfully to {to_email} "
                f"(Subject: '{subject}', Attempt: {attempt})"
            )
            
            # Record success in database (optional)
            _log_email_to_db(to_email, subject, 'sent', attempt)
            
            return True
            
        except BadHeaderError as e:
            last_error = f"Bad header error: {str(e)}"
            logger.error(f"❌ {last_error}")
            return False  # Don't retry on bad header
            
        except TemplateDoesNotExist as e:
            last_error = f"Template not found: {str(e)}"
            logger.error(f"❌ {last_error}")
            return False  # Don't retry on missing template
            
        except Exception as e:
            last_error = str(e)
            logger.warning(
                f"⚠️ Email send attempt {attempt}/{max_retries} failed: {last_error}"
            )
            
            if attempt >= max_retries:
                logger.error(
                    f"❌ Failed to send email to {to_email} after {max_retries} attempts. "
                    f"Last error: {last_error}"
                )
                
                # Record failure in database (optional)
                _log_email_to_db(to_email, subject, 'failed', attempt, last_error)
                
                return False
            
            # Wait before retry (exponential backoff)
            import time
            wait_time = 2 ** attempt  # 2, 4, 8 seconds
            logger.info(f"Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    return False


def _log_email_to_db(to_email, subject, status, attempts, error_message=None):
    """
    Optional: Log email status to database for audit trail
    """
    try:
        from booking.models import EmailLog
        
        EmailLog.objects.create(
            recipient=to_email,
            subject=subject,
            status=status,
            attempts=attempts,
            error_message=error_message
        )
    except Exception as e:
        logger.warning(f"Failed to log email to database: {str(e)}")








