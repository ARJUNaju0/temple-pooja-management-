from django.test import TestCase
from temple_admin.forms import AddMemberForm
from temple_admin.models import TempleAdmin

class AddMemberFormTest(TestCase):

    def setUp(self):
        # Create a user to test duplicate detection
        TempleAdmin.objects.create_user(
            username="existing_user", 
            email="exist@temple.com", 
            role='member'
        )

    def test_valid_form(self):
        """Test the form with perfect data"""
        data = {
            'username': 'new_user',
            'email': 'new@temple.com',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!'
        }
        form = AddMemberForm(data=data)
        self.assertTrue(form.is_valid())

    def test_password_mismatch(self):
        """Test that passwords must match"""
        data = {
            'username': 'user2',
            'email': 'user2@temple.com',
            'password': 'StrongPassword123!',
            'confirm_password': 'WrongPassword123!'
        }
        form = AddMemberForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("Passwords do not match.", form.errors['__all__'])

    def test_weak_password_validation(self):
        """Test regex validators (No number, no special char)"""
        # Case: No Number
        form = AddMemberForm(data={
            'username': 'u', 'email': 'u@t.com', 
            'password': 'Password!', 'confirm_password': 'Password!'
        })
        self.assertFalse(form.is_valid())
        self.assertIn("Password must contain at least one number.", form.errors['password'])

        # Case: No Special Char
        form = AddMemberForm(data={
            'username': 'u', 'email': 'u@t.com', 
            'password': 'Password123', 'confirm_password': 'Password123'
        })
        self.assertFalse(form.is_valid())
        self.assertIn("Password must contain at least one special character", form.errors['password'][0])

    def test_duplicate_username_and_email(self):
        """Test uniqueness validation"""
        data = {
            'username': 'existing_user', # Already in DB
            'email': 'exist@temple.com', # Already in DB
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!'
        }
        form = AddMemberForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("A member with this username already exists.", form.errors['username'])
        self.assertIn("A member with this email already exists.", form.errors['email'])