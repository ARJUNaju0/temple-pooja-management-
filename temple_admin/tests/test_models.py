from django.test import TestCase
from temple_admin.models import TempleAdmin, AdminActivityLog # Replace 'your_app' with your actual app name

class TempleAdminModelTest(TestCase):
    
    def test_create_temple_admin_auto_staff(self):
        """Test that setting role='temple_admin' automatically sets is_staff=True"""
        user = TempleAdmin.objects.create_user(
            username='admin_user',
            password='password123',
            role='temple_admin'
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_temple_admin)

    def test_create_member_auto_not_staff(self):
        """Test that setting role='member' ensures is_staff=False"""
        user = TempleAdmin.objects.create_user(
            username='member_user',
            password='password123',
            role='member'
        )
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_temple_admin)

    def test_superuser_is_always_admin(self):
        """Test that a superuser is forced to be a temple_admin"""
        superuser = TempleAdmin.objects.create_superuser(
            username='super',
            password='password123'
        )
        self.assertEqual(superuser.role, 'temple_admin')
        self.assertTrue(superuser.is_temple_admin)

class ActivityLogModelTest(TestCase):
    
    def test_activity_log_creation(self):
        admin = TempleAdmin.objects.create_user(username='admin', role='temple_admin')
        log = AdminActivityLog.objects.create(
            admin=admin,
            action="Test Action",
            description="Testing log"
        )
        self.assertEqual(str(log), f"admin - Test Action at {log.timestamp}")