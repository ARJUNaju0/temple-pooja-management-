# D:\Django Internship\tprmsystem\main\middleware.py

from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    Unified JWT Authentication Middleware
    Handles admin + member using a single cookie: access_token
    """

    def process_request(self, request):
        
            
        access_token = request.COOKIES.get(settings.AUTH_COOKIE_ACCESS)

        if not access_token:
            request.user = AnonymousUser()
            return None

        # Inject Authorization header for DRF API routes
        if request.path.startswith('/api/'):
            request.META['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'

        user = self._authenticate_token(access_token)

        if user:
            request.user = user
        else:
            request.user = AnonymousUser()

        return None

    def _authenticate_token(self, token):
        try:
            access_token_obj = AccessToken(token)
            user_id = access_token_obj.payload.get('user_id')

            if not user_id:
                return None

            user = User.objects.get(id=user_id, is_active=True)
            return user

        except (TokenError, InvalidToken):
            return None
        except User.DoesNotExist:
            return None
        except Exception:
            return None

    def process_response(self, request, response):
        if hasattr(request, 'user') and request.user.is_authenticated:
            response['X-Authenticated-User'] = request.user.username
            response['X-User-Role'] = getattr(request.user, 'role', '')
        else:
            response['X-Authenticated-User'] = 'anonymous'

        return response
