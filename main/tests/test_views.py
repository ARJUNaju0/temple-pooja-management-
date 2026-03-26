"""
Tests: Login, Logout, Token Refresh, Protected APIs
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import json

User = get_user_model()



class LoginViewTestCase(TestCase):
    """Test JWT Login endpoint"""
    
    def setUp(self):
        """Create test client and test user"""
        self.client = Client()
        
        # Create test users
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123',
            email='admin@temple.com',
            role='temple_admin',
            is_staff=True
        )
        
        self.member_user = User.objects.create_user(
            username='member1',
            password='member123',
            email='member1@temple.com',
            role='member',
            is_staff=False
        )
    
    # ============================================
    # Test: Valid Credentials
    # ============================================
    
    def test_member_login_success(self):
        """✅ Test: Member can login with valid credentials"""
        response = self.client.post(
            '/api/login/',
            data=json.dumps({
                'username': 'member1',
                'password': 'member123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['username'], 'member1')
        self.assertEqual(data['user']['role'], 'member')
        self.assertFalse(data['user']['is_staff'])
    
    def test_admin_login_success(self):
        """✅ Test: Admin can login with valid credentials"""
        response = self.client.post(
            '/api/login/',
            data=json.dumps({
                'username': 'admin',
                'password': 'admin123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['username'], 'admin')
        self.assertEqual(data['user']['role'], 'temple_admin')
        self.assertTrue(data['user']['is_staff'])
    
    # ============================================
    # Test: Invalid Credentials
    # ============================================
    
    def test_login_invalid_username(self):
        """❌ Test: Login fails with invalid username"""
        response = self.client.post(
            '/api/login/',
            data=json.dumps({
                'username': 'nonexistent',
                'password': 'member123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Invalid credentials', data['error'])
    
    def test_login_invalid_password(self):
        """❌ Test: Login fails with invalid password"""
        response = self.client.post(
            '/api/login/',
            data=json.dumps({
                'username': 'member1',
                'password': 'wrongpassword'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Invalid credentials', data['error'])
    
    # ============================================
    # Test: Missing Fields
    # ============================================
    
    def test_login_missing_username(self):
        """❌ Test: Login fails without username"""
        response = self.client.post(
            '/api/login/',
            data=json.dumps({
                'password': 'member123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_login_missing_password(self):
        """❌ Test: Login fails without password"""
        response = self.client.post(
            '/api/login/',
            data=json.dumps({
                'username': 'member1'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
    
    # ============================================
    # Test: Cookie Storage
    # ============================================
    
    def test_login_sets_cookies(self):
        """✅ Test: Login sets access_token and refresh_token cookies"""
        response = self.client.post(
            '/api/login/',
            data=json.dumps({
                'username': 'member1',
                'password': 'member123'
            }),
            content_type='application/json'
        )
        
        # Check cookies are set
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)
        
        # Check HttpOnly flag
        access_cookie = response.cookies['access_token']
        refresh_cookie = response.cookies['refresh_token']
        
        self.assertTrue(access_cookie['httponly'])
        self.assertTrue(refresh_cookie['httponly'])
    
    # ============================================
    # Test: Invalid JSON
    # ============================================
    
    def test_login_invalid_json(self):
        """❌ Test: Login fails with invalid JSON"""
        response = self.client.post(
            '/api/login/',
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])


class LogoutViewTestCase(TestCase):
    """Test JWT Logout endpoint"""
    
    def setUp(self):
        """Create test client and login"""
        self.client = Client()
        
        self.member_user = User.objects.create_user(
            username='member1',
            password='member123',
            role='member'
        )
    
    def test_logout_success(self):
        """✅ Test: User can logout"""
        # First login
        login_response = self.client.post(
            '/api/login/',
            data=json.dumps({
                'username': 'member1',
                'password': 'member123'
            }),
            content_type='application/json'
        )
        
        # Then logout
        logout_response = self.client.post('/api/logout/')
        
        self.assertEqual(logout_response.status_code, 200)
        data = logout_response.json()
        self.assertTrue(data['success'])
    
    def test_logout_clears_cookies(self):
        """✅ Test: Logout clears cookies"""
        # Login first
        self.client.post(
            '/api/login/',
            data=json.dumps({
                'username': 'member1',
                'password': 'member123'
            }),
            content_type='application/json'
        )
        
        # Logout
        logout_response = self.client.post('/api/logout/')
        
        # Check cookies are deleted
        self.assertIn('access_token', logout_response.cookies)
        # Cookie with max_age=0 means deleted
        self.assertEqual(logout_response.cookies['access_token']['max-age'], 0)


class ProtectedAPITestCase(TestCase):
    """Test Protected API endpoints"""
    
    def setUp(self):
        """Create test user and login"""
        self.client = Client()
        
        self.member_user = User.objects.create_user(
            username='member1',
            password='member123',
            role='member',
            is_staff=False
        )
        
        # Login to get token
        response = self.client.post(
            '/api/login/',
            data=json.dumps({
                'username': 'member1',
                'password': 'member123'
            }),
            content_type='application/json'
        )
        # Cookies are automatically set by client
    
    def test_get_current_user_authenticated(self):
        """✅ Test: Get current user when authenticated"""
        response = self.client.get('/api/user/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['username'], 'member1')
        self.assertEqual(data['role'], 'member')
    
    def test_get_current_user_unauthenticated(self):
        """❌ Test: Can't get current user when not authenticated"""
        # Create new client without login
        new_client = Client()
        response = new_client.get('/api/user/')
        
        self.assertEqual(response.status_code, 401)
    
    def test_member_dashboard_authenticated(self):
        """✅ Test: Member can access their dashboard API"""
        response = self.client.get('/api/member/dashboard/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('welcome_message', data)
        self.assertIn('member1', data['welcome_message'])
    
    def test_member_dashboard_unauthenticated(self):
        """❌ Test: Can't access dashboard without auth"""
        new_client = Client()
        response = new_client.get('/api/member/dashboard/')
        
        self.assertEqual(response.status_code, 401)
    
    def test_member_profile_api(self):
        """✅ Test: Member can access profile API"""
        response = self.client.get('/api/member/profile/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('profile', data)
        self.assertEqual(data['profile']['username'], 'member1')


class AdminOnlyAPITestCase(TestCase):
    """Test Admin-only endpoints"""
    
    def setUp(self):
        """Create test users"""
        self.client = Client()
        
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123',
            role='temple_admin',
            is_staff=True
        )
        
        self.member_user = User.objects.create_user(
            username='member1',
            password='member123',
            role='member',
            is_staff=False
        )
    
    def test_admin_can_create_member(self):
        """✅ Test: Admin can create new members"""
        # Login as admin
        self.client.post(
            '/api/login/',
            data=json.dumps({
                'username': 'admin',
                'password': 'admin123'
            }),
            content_type='application/json'
        )
        
        # Create member
        response = self.client.post(
            '/api/members/create/',
            data=json.dumps({
                'username': 'newmember',
                'email': 'newmember@temple.com',
                'password': 'member123',
                'first_name': 'New',
                'last_name': 'Member'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['username'], 'newmember')
    
    def test_member_cannot_create_member(self):
        """❌ Test: Member can't create new members"""
        # Login as member
        self.client.post(
            '/api/login/',
            data=json.dumps({
                'username': 'member1',
                'password': 'member123'
            }),
            content_type='application/json'
        )
        
        # Try to create member
        response = self.client.post(
            '/api/members/create/',
            data=json.dumps({
                'username': 'newmember',
                'email': 'newmember@temple.com',
                'password': 'member123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
    
    def test_unauthenticated_cannot_create_member(self):
        """❌ Test: Unauthenticated user can't create members"""
        response = self.client.post(
            '/api/members/create/',
            data=json.dumps({
                'username': 'newmember',
                'email': 'newmember@temple.com',
                'password': 'member123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)