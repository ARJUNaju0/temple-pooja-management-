# D:\Django Internship\tprmsystem\main\views.py

from .models import Gallery
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from .models import ActivityLog
from main.decorators import member_required
import json
from cloudinary.uploader import upload
from cloudinary.uploader import upload, destroy  
import cloudinary
from .models import PasswordResetToken
from django.core.mail import send_mail
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError



User = get_user_model()


def home(request):
    """Home page"""
    images = Gallery.objects.filter(is_approved=True).order_by("-uploaded_at")[:8]
    return render(request, 'main/home.html', {'images': images})


def login_page(request):
    """
    Unified login page for BOTH admin and members
    Redirects if already logged in
    """
    if request.user.is_authenticated:
        # Redirect based on role
        if request.user.is_staff or request.user.role == 'temple_admin':
            return redirect('/temple_admin/dashboard/')
        else:
            return redirect('/services')
    
    return render(request, 'registration/login.html')


# HELPER FUNCTIONS

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_activity(user, action, request, details=None):
    """Log user activity for audit trail"""
    try:
        ActivityLog.objects.create(
            user=user,
            action=action,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            is_admin=(user.is_staff if user else False),
            details=details or {}
        )
    except Exception as e:
        print(f"❌ Logging error: {e}")


# JWT AUTHENTICATION ENDPOINTS

@csrf_exempt
@require_http_methods(["POST"])
def jwt_login(request):
    """
    JWT Login endpoint for BOTH Admin and Member
    Returns tokens in HttpOnly cookies with configurable expiration based on remember_me
    """
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        remember_me = data.get('remember_me', False)
        
        # Validate input
        if not username or not password:
            log_activity(
                user=None,
                action='login_failed',
                request=request,
                details={'reason': 'missing_credentials', 'username': username}
            )
            return JsonResponse({
                'success': False,
                'error': 'Please provide both username and password'
            }, status=400)
        
        # Authenticate user (works for both admin and members)
        user = authenticate(username=username, password=password)
        
        if user is not None:
            # Check if user is active
            if not user.is_active:
                log_activity(
                    user=user,
                    action='login_failed',
                    request=request,
                    details={'reason': 'inactive_account'}
                )
                return JsonResponse({
                    'success': False,
                    'error': 'Account is inactive. Please contact administrator.'
                }, status=403)
            
            # Set token expiration based on remember_me
            if remember_me:
                # Longer expiration for "Remember me"
                access_token_lifetime = timedelta(days=30)  # 30 days
                refresh_token_lifetime = timedelta(days=60)  # 60 days
            else:
                # Default session-based expiration
                access_token_lifetime = timedelta(hours=1)  # 1 hour
                refresh_token_lifetime = timedelta(days=7)   # 7 days
            
            # Generate JWT tokens with custom expiration
            refresh = RefreshToken.for_user(user)
            refresh.set_exp(lifetime=refresh_token_lifetime)
            
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # Log successful login
            log_activity(
                user=user,
                action='login_success',
                request=request,
                details={
                    'role': user.role,
                    'is_staff': user.is_staff,
                    'is_temple_admin': user.is_temple_admin,
                    'remember_me': remember_me,
                    'access_token_expires_in': str(access_token_lifetime),
                    'refresh_token_expires_in': str(refresh_token_lifetime)
                }
            )
            
            # Create response with user info
            response = JsonResponse({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                    'is_temple_admin': user.is_temple_admin,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'message': 'Login successful',
                'remember_me': remember_me
            }, status=200)
            
            # Set tokens in HttpOnly cookies with appropriate max_age
            response.set_cookie(
                key=settings.AUTH_COOKIE_ACCESS,  
                value=access_token,
                httponly=settings.AUTH_COOKIE_HTTPONLY,
                secure=settings.AUTH_COOKIE_SECURE,
                samesite=settings.AUTH_COOKIE_SAMESITE,
                path=settings.AUTH_COOKIE_PATH,
                max_age=access_token_lifetime.total_seconds() if remember_me else None  # Session cookie if not remember_me
            )
            
            response.set_cookie(
                key=settings.AUTH_COOKIE_REFRESH,  
                value=refresh_token,
                httponly=settings.AUTH_COOKIE_HTTPONLY,
                secure=settings.AUTH_COOKIE_SECURE,
                samesite=settings.AUTH_COOKIE_SAMESITE,
                path=settings.AUTH_COOKIE_PATH,
                max_age=refresh_token_lifetime.total_seconds() if remember_me else None  # Session cookie if not remember_me
            )
            
            return response
        else:
            # Log failed attempt
            log_activity(
                user=None,
                action='login_failed',
                request=request,
                details={'reason': 'invalid_credentials', 'username': username}
            )
            return JsonResponse({
                'success': False,
                'error': 'Invalid credentials'
            }, status=401)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        print(f"Login error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def jwt_refresh(request):
    """
    Refresh JWT access token using refresh token from cookie
    """
    try:
        refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        
        if not refresh_token:
            return JsonResponse({
                'success': False,
                'error': 'Refresh token is required'
            }, status=400)
        
        # Generate new access token
        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)
        
        # Log token refresh
        try:
            user_id = refresh.payload.get('user_id')
            user = User.objects.get(id=user_id)
            log_activity(
                user=user,
                action='token_refresh',
                request=request,
                details={}
            )
        except:
            pass
        
        # Create response with new access token
        response = JsonResponse({
            'success': True,
            'message': 'Token refreshed successfully'
        }, status=200)
        
        response.set_cookie(
            key=settings.AUTH_COOKIE_ACCESS,
            value=access_token,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            path=settings.AUTH_COOKIE_PATH,
            max_age=3600,
        )
        
        return response
        
    except TokenError as e:
        return JsonResponse({
            'success': False,
            'error': 'Invalid or expired refresh token'
        }, status=401)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=401)


@csrf_exempt
@require_http_methods(["POST"])
def jwt_logout(request):
    """
    Logout by blacklisting the refresh token and clearing cookies
    """
    try:
        refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                # Log logout before blacklisting
                try:
                    user_id = token.payload.get('user_id')
                    user = User.objects.get(id=user_id)
                    log_activity(
                        user=user,
                        action='logout',
                        request=request,
                        details={}
                    )
                except:
                    pass
                # Blacklist the token
                token.blacklist()
            except:
                pass
        
        # Create response
        response = JsonResponse({
            'success': True,
            'message': 'Successfully logged out'
        }, status=200)
        
        # Clear cookies
        response.delete_cookie(settings.AUTH_COOKIE_ACCESS)
        response.delete_cookie(settings.AUTH_COOKIE_REFRESH)
        
        return response
        
    except Exception as e:
        response = JsonResponse({
            'success': True,
            'message': 'Logged out'
        }, status=200)
        response.delete_cookie(settings.AUTH_COOKIE_ACCESS)
        response.delete_cookie(settings.AUTH_COOKIE_REFRESH)
        return response


# USER INFO ENDPOINTS

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """
    Get current authenticated user information
    """
    user = request.user
    log_activity(
        user=user,
        action='view_profile',
        request=request,
        details={}
    )
    
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'is_temple_admin': user.is_temple_admin,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone_number': user.phone_number,
        'last_login': user.last_login,
        'date_joined': user.date_joined,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_view(request):
    """
    Example protected endpoint that requires JWT authentication
    """
    return Response({
        'message': f'Hello {request.user.username}!',
        'user_id': request.user.id,
        'role': request.user.role,
        'is_staff': request.user.is_staff
    })


#  ADMIN-ONLY ENDPOINTS

@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_member(request):
    """
    Admin-only endpoint to create new members
    """
    try:
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        phone_number = request.data.get('phone_number', '')
        
        if not all([username, email, password]):
            return Response({
                'error': 'Username, email, and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate password strength
        if len(password) < 8:
            return Response({
                'error': 'Password must be at least 8 characters long'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            return Response({
                'error': 'Username already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(email=email).exists():
            return Response({
                'error': 'Email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create new member user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            role='member',  
            is_staff=False,
            is_temple_admin=False,
        )
        
        # Log member creation
        log_activity(
            user=request.user,
            action='create_member',
            request=request,
            details={'created_user': username, 'created_user_id': user.id}
        )
        
        return Response({
            'success': True,
            'message': 'Member created successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# PASSWORD MANAGEMENT ENDPOINTS

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    try:
        user = request.user
        data = json.loads(request.body)
        
        # Check current password
        if not user.check_password(data.get('current_password')):
            return Response(
                {'error': 'Current password is incorrect'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check passwords match
        new_password1 = data.get('new_password1')
        new_password2 = data.get('new_password2')
        
        if new_password1 != new_password2:
            return Response(
                {'error': 'New passwords do not match'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check password length
        if len(new_password1) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters long'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update password
        user.set_password(new_password1)
        user.save()
        
        return Response(
            {'message': 'Password updated successfully'}, 
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# MEMBER DASHBOARD ENDPOINTS

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def member_dashboard(request):
    """
    Member dashboard - shows personalized information
    """
    user = request.user
    
    log_activity(
        user=user,
        action='view_dashboard',
        request=request,
        details={}
    )
    
    return Response({
        'welcome_message': f'Welcome back, {user.username}!',
        'user_info': {
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'member_since': user.date_joined,
            'last_login': user.last_login,
        },
        'quick_stats': {
            'total_bookings': 0, 
            'active_sevas': 0,
            'total_donations': 0,
        }
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def member_profile(request):
    """
    Member profile - view and update profile information
    """
    user = request.user
    
    if request.method == 'POST':
        # Update user profile
        data = request.data
        
        # Update basic fields
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        user.phone_number = data.get('phone_number', user.phone_number)
        
        # Save the changes
        user.save()
        
        log_activity(
            user=user,
            action='update_profile',
            request=request,
            details={
                'fields_updated': [
                    k for k in ['first_name', 'last_name', 'email', 'phone_number']
                    if k in data
                ]
            }
        )
        
        return Response({
            'success': True,
            'message': 'Profile updated successfully',
            'profile': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone_number': user.phone_number,
                'role': user.role,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined,
                'last_login': user.last_login,
            }
        })
    
    # GET request handling
    log_activity(
        user=user,
        action='view_profile',
        request=request,
        details={}
    )
    
    return Response({
        'profile': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'role': user.role,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'date_joined': user.date_joined,
            'last_login': user.last_login,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def member_activity_logs(request):
    """
    Member can view their own activity logs
    """
    user = request.user
    
    # Get user's recent activities
    logs = ActivityLog.objects.filter(user=user).order_by('-timestamp')[:50]
    
    activities = [{
        'action': log.action,
        'timestamp': log.timestamp,
        'ip_address': log.ip_address,
        'details': log.details
    } for log in logs]
    
    return Response({
        'activities': activities
    })



# PROTECTED PAGE VIEWS

@member_required
def member_profile_view(request):
    """Member profile page (HTML)"""
    if not request.user.is_authenticated:
        return redirect('/login/')
    return render(request, 'main/member_profile.html')


def unauthorized_view(request):
    """Unauthorized access page"""
    return render(request, 'main/unauthorized.html', status=403)


def devtools_config(request):
    """Devtools config (returns 404)"""
    return HttpResponse(status=404)


# gallery 
ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png"]
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_gallery_image(request):
    # Check if files are present
    if not request.FILES.getlist('image'):
        return Response(
            {"success": False, "error": "No files were uploaded"},
            status=status.HTTP_400_BAD_REQUEST
        )

    uploaded_files = request.FILES.getlist('image')
    response_data = {
        "success": True,
        "message": "Files processed successfully",
        "results": []
    }
    
    for image in uploaded_files:
        # Validate extension
        extension = image.name.split(".")[-1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            response_data["results"].append({
                "success": False,
                "filename": image.name,
                "error": "Invalid file type. Only JPG, JPEG, PNG files are allowed"
            })
            continue

        # Validate size
        if image.size > MAX_FILE_SIZE:
            response_data["results"].append({
                "success": False,
                "filename": image.name,
                "error": f"File size exceeds {MAX_FILE_SIZE // (1024 * 1024)}MB limit"
            })
            continue

        try:
            # Upload to Cloudinary
            result = upload(
                image,
                folder="gallery_images"
            )

            # Get title from request data, append index if multiple files
            title = request.POST.get('title', '').strip()
            
            # Save to DB with title
            gallery = Gallery.objects.create(
                image_url=result["secure_url"],
                title=title if title else None,
                cloudinary_public_id=result["public_id"],
                uploaded_by=request.user,
                is_approved=request.user.is_staff
            )

            response_data["results"].append({
                "success": True,
                "filename": image.name,
                "image_url": gallery.image_url,
                "id": gallery.id
            })

        except Exception as e:
            response_data["results"].append({
                "success": False,
                "filename": image.name,
                "error": str(e)
            })
            
    # Check if any files were processed successfully
    if not any(r["success"] for r in response_data["results"]):
        return Response(
            {
                "success": False,
                "error": "Failed to process any files. Please check file requirements.",
                "details": response_data["results"]
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response(
        response_data,
        status=status.HTTP_201_CREATED
    )

def upload_page(request):
    return render(request, "main/upload_image.html")


def gallery_view(request):
    images = Gallery.objects.filter(is_approved=True).order_by("-uploaded_at")
    return render(request, "main/gallery.html", {
        "images": images
    })

@api_view(['POST'])
@permission_classes([IsAdminUser])
def delete_gallery_image(request, image_id):
    """Delete gallery image from both Cloudinary and database"""
    try:
        image = get_object_or_404(Gallery, id=image_id)

        # Delete from Cloudinary first if public_id exists
        if image.cloudinary_public_id:
            try:
                # Use the destroy function we imported
                result = destroy(image.cloudinary_public_id)
                print(f"Cloudinary deletion result: {result}")
            except Exception as e:
                # Log the error but continue with DB deletion
                print(f"Error deleting from Cloudinary: {str(e)}")
        
        # Delete from database
        image.delete()

        # Log the activity
        log_activity(
            user=request.user,
            action='delete_gallery_image',
            request=request,
            details={'image_id': image_id, 'title': image.title}
        )

        return JsonResponse({
            "success": True,
            "message": "Image deleted successfully"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def approve_gallery_image(request, image_id):
    image = get_object_or_404(Gallery, id=image_id)

    image.is_approved = True
    image.approved_by = request.user
    image.approved_at = timezone.now()
    image.save()

    log_activity(
        user=request.user,
        action='approve_gallery_image',
        request=request,
        details={'image_id': image.id}
    )

    return Response({"success": True, "message": "Image approved"})

@api_view(['POST'])
@permission_classes([IsAdminUser])
def reject_gallery_image(request, image_id):
    image = get_object_or_404(Gallery, id=image_id)

    if image.cloudinary_public_id:
        destroy(image.cloudinary_public_id)

    image.delete()

    return Response({"success": True, "message": "Image rejected"})

@api_view(['GET'])
@permission_classes([IsAdminUser])
def pending_gallery_images(request):
    images = Gallery.objects.filter(is_approved=False).order_by("-uploaded_at")

    return Response([
        {
            "id": img.id,
            "image_url": img.image_url,
            "title": img.title,
            "uploaded_by": img.uploaded_by.username if img.uploaded_by else None,
            "uploaded_at": img.uploaded_at
        } for img in images
    ])

from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def admin_pending_gallery_view(request):
    images = Gallery.objects.filter(is_approved=False).order_by("-uploaded_at")
    return render(request, "main/admin_pending_gallery.html", {
        "images": images
    })

# forgot password 
@csrf_exempt
@require_http_methods(["POST"])
def forgot_password(request):
    data = json.loads(request.body)
    email = data.get("email")

    # Always return success (security best practice)
    if not email:
        return JsonResponse({"success": True})

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({"success": True})

    token = PasswordResetToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(minutes=30)
    )

    reset_link = f"{settings.FRONTEND_URL}/reset-password/{token.token}/"

    send_mail(
        subject="Reset your password",
        message=f"Click this link to reset your password:\n\n{reset_link}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

    return JsonResponse({
        "success": True,
        "message": "If the email exists, a reset link has been sent."
    })
# Reset Password API 
@csrf_exempt
@require_http_methods(["POST"])
def reset_password(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        token_value = data.get("token")
        password = data.get("password")

        if not token_value or not password:
            return JsonResponse({"error": "Invalid request"}, status=400)

        try:
            token_obj = PasswordResetToken.objects.get(token=token_value)
        except PasswordResetToken.DoesNotExist:
            return JsonResponse({"error": "Invalid or expired token"}, status=400)

        if not token_obj.is_valid():
            return JsonResponse({"error": "Token expired or already used"}, status=400)

        try:
            validate_password(password, token_obj.user)
        except ValidationError as e:
            return JsonResponse({"error": e.messages[0]}, status=400)

        user = token_obj.user
        user.set_password(password)
        user.save()

        token_obj.is_used = True
        token_obj.save()

        return JsonResponse({
            "success": True,
            "message": "Password reset successful"
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    except Exception as e:
        # CRITICAL: never return HTML on API errors
        return JsonResponse({"error": str(e)}, status=500)


def forgot_password_page(request):
    return render(request, 'registration/forgot_password.html')

def reset_password_page(request, token):
    return render(request, 'registration/reset_password.html', {
        'token': token
    })
