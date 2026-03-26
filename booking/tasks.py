#booking/tasks.py


from celery import shared_task
from booking.utils.email_service import send_booking_email
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_booking_email_async(self, template_name, subject, to_email, context):
    """
    Celery task to send booking email asynchronously with automatic retry
    
    Usage:
        send_booking_email_async.delay(
            template_name='payment_cash.html',
            subject='Payment Confirmed',
            to_email='user@example.com',
            context={'name': 'John', 'amount': 500}
        )
    """
    try:
        logger.info(f"[Celery Task] Sending email to {to_email} (Subject: {subject})")
        
        success = send_booking_email(
            template_name=template_name,
            subject=subject,
            to_email=to_email,
            context=context,
            max_retries=1  # Celery handles retries
        )
        
        if not success:
            logger.error(f"[Celery Task] Failed to send email to {to_email}")
            # Retry the task
            raise self.retry(exc=Exception("Email send failed"))
        
        logger.info(f"[Celery Task] ✅ Email sent successfully to {to_email}")
        return True
        
    except Exception as exc:
        logger.error(f"[Celery Task] Error sending email: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@shared_task
def send_bulk_booking_emails(email_list):
    """
    Send emails to multiple recipients (e.g., for notifications)
    
    Args:
        email_list: List of dicts with email details
        [{
            'template_name': 'booking_approved.html',
            'subject': 'Booking Approved',
            'to_email': 'user@example.com',
            'context': {...}
        }]
    """
    results = []
    
    for email_data in email_list:
        try:
            success = send_booking_email(
                template_name=email_data['template_name'],
                subject=email_data['subject'],
                to_email=email_data['to_email'],
                context=email_data['context']
            )
            results.append({
                'to': email_data['to_email'],
                'status': 'sent' if success else 'failed'
            })
        except Exception as e:
            logger.error(f"Error in bulk email to {email_data['to_email']}: {str(e)}")
            results.append({
                'to': email_data['to_email'],
                'status': 'error',
                'error': str(e)
            })
    
    logger.info(f"Bulk email results: {results}")
    return results
