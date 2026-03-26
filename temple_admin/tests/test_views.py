from django.test import TestCase, Client, modify_settings # <-- Import modify_settings
from django.urls import reverse
from temple_admin.models import TempleAdmin, AdminActivityLog

@modify_settings(MIDDLEWARE={'remove': 'main.middleware.JWTAuthenticationMiddleware'}) 
class AdminViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        
        # Create users...
        self.admin_user = TempleAdmin.objects.create_user(
            username='admin', password='password123', role='temple_admin'
        )
        self.member_user = TempleAdmin.objects.create_user(
            username='member', password='password123', role='member'
        )
        self.dashboard_url = reverse('temple_admin:dashboard')
        self.add_member_url = reverse('temple_admin:add_member')

    def test_dashboard_access_admin(self):
        # Use force_login just to be safe
        self.client.force_login(self.admin_user)
        
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

    def test_add_member_logic_success(self):
        self.client.force_login(self.admin_user)
        
        data = {
            'username': 'new_devotee',
            'email': 'devotee@temple.com',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!'
        }
        
        response = self.client.post(self.add_member_url, data)
        self.assertRedirects(response, self.dashboard_url)
    def test_add_member_permission_denied(self):
        """Member tries to access add_member page -> Login redirect"""
        self.client.login(username='member', password='password123')
        response = self.client.get(self.add_member_url)
        # @user_passes_test usually redirects to login if failed
        self.assertEqual(response.status_code, 302)