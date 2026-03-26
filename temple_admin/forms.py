#forms.py
from django import forms
from .models import TempleAdmin
from django.core.exceptions import ValidationError
import re

class AddMemberForm(forms.Form):
    username = forms.CharField(
        label="Username",
        min_length=3,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-200 text-gray-800 focus:border-orange-500 focus:ring-2 focus:ring-orange-200 outline-none transition-all',
            'placeholder': 'e.g. member1',
            'id': 'id_username'
        })
    )
    
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-200 text-gray-800 focus:border-orange-500 focus:ring-2 focus:ring-orange-200 outline-none transition-all',
            'placeholder': 'e.g. member1@temple.com',
            'id': 'id_email'
        })
    )
    
    password = forms.CharField(
        label="Password",
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-200 text-gray-800 focus:border-orange-500 focus:ring-2 focus:ring-orange-200 outline-none transition-all',
            'placeholder': 'Enter password',
            'id': 'id_password'
        })
    )
    
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg bg-gray-50 border border-gray-200 text-gray-800 focus:border-orange-500 focus:ring-2 focus:ring-orange-200 outline-none transition-all',
            'placeholder': 'Confirm password',
            'id': 'id_confirm_password'
        })
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        
        # Check length
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long.")
        
        # Check if username contains only numbers
        if username.isdigit():
            raise ValidationError("Username cannot contain only numbers. Please include letters or special characters.")
        
        # Check if username already exists
        if TempleAdmin.objects.filter(username=username).exists():
            raise ValidationError("A member with this username already exists.")
        
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        
        # Basic email format validation using regex
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_regex, email):
            raise ValidationError("Please enter a valid email address. Example: user@example.com")
            
        # Extract domain part
        domain = email.split('@')[1]
        
        # List of allowed email domains
        ALLOWED_DOMAINS = [
            'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'protonmail.com',
            'aol.com', 'icloud.com', 'mail.com', 'zoho.com', 'gmx.com', 'yandex.com',
            'temple.com', 'temple.org', 'temple.edu'  # Add your organization's domains
        ]
        
        # Check if domain is in allowed list
        if domain not in ALLOWED_DOMAINS:
            raise ValidationError(
                "Please use a valid email provider. Common providers include: "
                "Gmail, Yahoo, Outlook, etc."
            )
            
        # Check if email already exists
        if TempleAdmin.objects.filter(email=email).exists():
            raise ValidationError("A member with this email already exists.")
        
        return email
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        
        # Check length
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        
        # Check for alphabet (both upper and lower case)
        if not re.search(r'[a-zA-Z]', password):
            raise ValidationError("Password must contain at least one letter.")
        
        # Check for numbers
        if not re.search(r'\d', password):
            raise ValidationError("Password must contain at least one number.")
        
        # Check for special characters
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError("Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>).")
        
        return password
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")
        
        return cleaned_data