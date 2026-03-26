"""
Tests: Token verification, user authentication, expired tokens
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from main.middleware import JWTAuthenticationMiddleware

User = get_user_model()


class JWTAuthenticationMiddlewareTestCase(TestCase):
    """Test JWT Authentication Middleware"""
    
    def setUp(self):
        """Create test user and middleware"""
        self.factory = RequestFactory()
        self.middleware = JWTAuthenticationMiddleware(lambda r: None)
        
        self.user = User.objects.create_user(
            username='testuser',
            password='password123',
            role='member'
        )
        
        # Generate valid token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.refresh_token = str(refresh)
    
    def test_middleware_authenticates_valid_token(self):
        """✅ Test: Middleware authenticates user with valid token"""
        request = self.factory.get('/')
        request.COOKIES['access_token'] = self.access_token
        
        self.middleware.process_request(request)
        
        self.assertTrue(request.user.is_authenticated)
        self.assertEqual(request.user.username, 'testuser')
    
    def test_middleware_sets_anonymous_without_token(self):
        """✅ Test: Middleware sets anonymous user without token"""
        request = self.factory.get('/')
        # No token in cookies
        
        self.middleware.process_request(request)
        
        self.assertFalse(request.user.is_authenticated)
    
    def test_middleware_rejects_invalid_token(self):
        """❌ Test: Middleware rejects invalid token"""
        request = self.factory.get('/')
        request.COOKIES['access_token'] = 'invalid.token.here'
        
        self.middleware.process_request(request)
        
        # Should not authenticate invalid token
        self.assertFalse(request.user.is_authenticated)
    
    def test_middleware_injects_authorization_header(self):
        """✅ Test: Middleware injects Authorization header for API views"""
        request = self.factory.get('/api/user/')
        request.COOKIES['access_token'] = self.access_token
        
        self.middleware.process_request(request)
        
        # Should inject Authorization header for DRF
        self.assertIn('HTTP_AUTHORIZATION', request.META)
        self.assertTrue(
            request.META['HTTP_AUTHORIZATION'].startswith('Bearer ')
        )
    
    def test_middleware_preserves_user_data(self):
        """✅ Test: Middleware preserves user data correctly"""
        request = self.factory.get('/')
        request.COOKIES['access_token'] = self.access_token
        
        self.middleware.process_request(request)
        
        self.assertEqual(request.user.username, 'testuser')
        self.assertEqual(request.user.role, 'member')
        self.assertEqual(request.user.id, self.user.id)
    
    def test_middleware_works_for_different_roles(self):
        """✅ Test: Middleware works for both admin and member roles"""
        admin_user = User.objects.create_user(
            username='admin',
            password='password123',
            role='temple_admin',
            is_staff=True
        )
        
        refresh = RefreshToken.for_user(admin_user)
        admin_token = str(refresh.access_token)
        
        request = self.factory.get('/')
        request.COOKIES['access_token'] = admin_token
        
        self.middleware.process_request(request)
        
        self.assertEqual(request.user.username, 'admin')
        self.assertEqual(request.user.role, 'temple_admin')
        self.assertTrue(request.user.is_staff)


class TokenSecurityTestCase(TestCase):
    """Test JWT Token Security"""
    
    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            password='password123'
        )
    
    def test_token_cannot_be_modified(self):
        """❌ Test: Token cannot be modified without breaking"""
        refresh = RefreshToken.for_user(self.user)
        token = str(refresh.access_token)
        
        # Modify token
        modified_token = token[:-5] + 'xxxxx'
        
        # Should fail verification
        with self.assertRaises(TokenError):
            from rest_framework_simplejwt.tokens import AccessToken
            AccessToken(modified_token)
    
    def test_token_contains_user_id(self):
        """✅ Test: Token contains user ID"""
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        self.assertEqual(int(access_token['user_id']), self.user.id)
    
    def test_token_has_expiry(self):
        """✅ Test: Token has expiry time"""
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        self.assertIn('exp', access_token)
        self.assertIsNotNone(access_token['exp'])
    
    def test_refresh_token_rotation(self):
        """✅ Test: Refresh token can generate new access token"""
        refresh = RefreshToken.for_user(self.user)
        first_access_token = str(refresh.access_token)
        
        # Refresh should generate new access token
        refresh_token = RefreshToken(str(refresh))
        new_access_token = str(refresh_token.access_token)
        
        # Tokens should be different
        self.assertNotEqual(first_access_token, new_access_token)