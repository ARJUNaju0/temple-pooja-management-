# main/tests/test_models.py
"""
✅ TEST SUITE FOR MODELS
Tests: User model, Activity logging
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from main.models import ActivityLog

User = get_user_model()


class TempleAdminModelTestCase(TestCase):
    """Test TempleAdmin User Model"""
    
    def test_create_member_user(self):
        """✅ Test: Create member user"""
        user = User.objects.create_user(
            username='member1',
            email='member1@temple.com',
            password='password123',
            role='member'
        )
        
        self.assertEqual(user.username, 'member1')
        self.assertEqual(user.role, 'member')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_temple_admin)
    
    def test_create_admin_user(self):
        """✅ Test: Create admin user"""
        user = User.objects.create_user(
            username='admin',
            email='admin@temple.com',
            password='password123',
            role='temple_admin',
            is_staff=True
        )
        
        self.assertEqual(user.username, 'admin')
        self.assertEqual(user.role, 'temple_admin')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_temple_admin)
    
    def test_auto_sync_permissions(self):
        """✅ Test: Auto-sync permissions on save"""
        user = User.objects.create_user(
            username='testuser',
            password='password123',
            role='temple_admin'
        )
        
        # Should auto-sync
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_temple_admin)
    
    def test_password_hashing(self):
        """✅ Test: Password is hashed, not stored in plain text"""
        user = User.objects.create_user(
            username='testuser',
            password='mypassword123'
        )
        
        # Password should be hashed
        self.assertNotEqual(user.password, 'mypassword123')
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))
    
    def test_password_verification(self):
        """✅ Test: Password verification works"""
        user = User.objects.create_user(
            username='testuser',
            password='mypassword123'
        )
        
        # Correct password
        self.assertTrue(user.check_password('mypassword123'))
        
        # Wrong password
        self.assertFalse(user.check_password('wrongpassword'))
    
    def test_user_string_representation(self):
        """✅ Test: User string representation"""
        user = User.objects.create_user(
            username='testuser',
            role='member'
        )
        
        expected = "testuser (Member)"
        self.assertEqual(str(user), expected)
    
    def test_inactive_user_cannot_login(self):
        """❌ Test: Inactive user cannot login"""
        user = User.objects.create_user(
            username='testuser',
            password='password123'
        )
        user.is_active = False
        user.save()
        
        from django.contrib.auth import authenticate
        
        result = authenticate(username='testuser', password='password123')
        self.assertIsNone(result)
    
    def test_user_with_phone_number(self):
        """✅ Test: User can have phone number"""
        user = User.objects.create_user(
            username='testuser',
            password='password123',
            phone_number='+91-9876543210'
        )
        
        self.assertEqual(user.phone_number, '+91-9876543210')
    
    def test_duplicate_username_not_allowed(self):
        """❌ Test: Duplicate usernames not allowed"""
        User.objects.create_user(
            username='testuser',
            password='password123'
        )
        
        from django.db import IntegrityError
        
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username='testuser',
                password='password123'
            )


class ActivityLogModelTestCase(TestCase):
    """Test ActivityLog Model"""
    
    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            password='password123'
        )
    
    def test_create_activity_log(self):
        """✅ Test: Create activity log"""
        log = ActivityLog.objects.create(
            user=self.user,
            action='login',
            ip_address='127.0.0.1',
            user_agent='Mozilla/5.0'
        )
        
        self.assertEqual(log.action, 'login')
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.ip_address, '127.0.0.1')
    
    def test_activity_log_timestamp(self):
        """✅ Test: Activity log has timestamp"""
        log = ActivityLog.objects.create(
            user=self.user,
            action='login'
        )
        
        self.assertIsNotNone(log.timestamp)
    
    def test_multiple_logs_for_user(self):
        """✅ Test: User can have multiple activity logs"""
        ActivityLog.objects.create(user=self.user, action='login')
        ActivityLog.objects.create(user=self.user, action='logout')
        ActivityLog.objects.create(user=self.user, action='view_profile')
        
        logs = ActivityLog.objects.filter(user=self.user)
        self.assertEqual(logs.count(), 3)
    
    def test_activity_log_ordering(self):
        """✅ Test: Activity logs ordered by timestamp (newest first)"""
        log1 = ActivityLog.objects.create(user=self.user, action='login')
        log2 = ActivityLog.objects.create(user=self.user, action='logout')
        
        logs = ActivityLog.objects.all()
        
        # log2 should be first (newest)
        self.assertEqual(logs[0].id, log2.id)
        self.assertEqual(logs[1].id, log1.id)
    
    def test_activity_log_with_details(self):
        """✅ Test: Activity log can store details"""
        log = ActivityLog.objects.create(
            user=self.user,
            action='login_success',
            details={'role': 'member', 'is_staff': False}
        )
        
        self.assertEqual(log.details['role'], 'member')
        self.assertFalse(log.details['is_staff'])
    
    def test_activity_log_string_representation(self):
        """✅ Test: Activity log string representation"""
        log = ActivityLog.objects.create(
            user=self.user,
            action='login'
        )
        
        expected = f"testuser - login at {log.timestamp}"
        self.assertEqual(str(log), expected)
    
    def test_cascade_delete_user_logs(self):
        """✅ Test: Deleting user deletes their logs"""
        self.user.save()

        ActivityLog.objects.create(user=self.user, action='login')
        ActivityLog.objects.create(user=self.user, action='logout')
        
        self.assertEqual(ActivityLog.objects.filter(user=self.user).count(), 2)
        
        # Delete user
        self.user.delete()
        
        # Logs should also be deleted
        self.assertEqual(ActivityLog.objects.count(), 0)
