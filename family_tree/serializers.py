from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from .models import FamilyMember

def resolve_blood_parent(parent):
        """
        If selected parent is a spouse, redirect to the blood parent.
        """
        if not parent:
            return None

        # If parent has children, they are blood parent
        if parent.children.exists():
            return parent

        # If parent has spouse and spouse has children, spouse is blood parent
        if parent.spouse and parent.spouse.children.exists():
            return parent.spouse

        return parent

class FamilyMemberSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    spouse_id = serializers.IntegerField(source='spouse.id', read_only=True)
    spouse_name = serializers.CharField(source='spouse.name', read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = FamilyMember
        fields = '__all__'
        read_only_fields = ('created_at',)

    def get_photo_url(self, obj):
        if obj.photo:
            return obj.photo.url
        return None

    def validate(self, data):
        # ... (Keep your existing validation logic here) ...
        # Copy-paste your existing validate() method here
        instance = FamilyMember(**data)
        if self.instance:
            instance.id = self.instance.id
            if 'parent' not in data: instance.parent = self.instance.parent
            if 'spouse' not in data: instance.spouse = self.instance.spouse

        try:
            instance.clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else list(e.messages))
        
        return data

    # =========================================================
    # 1. HANDLE CREATION (Adding Mother)
    # =========================================================
    @transaction.atomic
    def create(self, validated_data):
        parent = validated_data.get('parent')
        spouse = validated_data.get('spouse')

        # 🔑 FIX: normalize parent
        if parent:
            validated_data['parent'] = resolve_blood_parent(parent)

        instance = super().create(validated_data)

        # Sync spouse (your existing logic)
        if spouse:
            spouse.spouse = instance
            spouse.save()

        return instance

    # =========================================================
    # 2. HANDLE UPDATES (Editing links later)
    # =========================================================
    @transaction.atomic
    def update(self, instance, validated_data):
        if 'parent' in validated_data:
            validated_data['parent'] = resolve_blood_parent(
                validated_data.get('parent')
            )

        return super().update(instance, validated_data)

    
   