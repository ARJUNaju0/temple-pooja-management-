from django import forms
from .models import FamilyMember

class FamilyMemberForm(forms.ModelForm):
    class Meta:
        model = FamilyMember
        fields = ['name', 'gender', 'parent', 'spouse', 'date_of_birth', 'photo', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'spouse': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Notes', 'rows': 3}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        family_id = kwargs.pop('family_id', None)
        super().__init__(*args, **kwargs)
        
        self.fields['parent'].empty_label = "No Parent (Root/Ancestor)"
        self.fields['spouse'].empty_label = "No Spouse"

        # Optionally filter parent/spouse dropdowns to only the same family
        if family_id:
            members = FamilyMember.objects.filter(family_group_id=family_id)
            self.fields['parent'].queryset = members
            self.fields['spouse'].queryset = members