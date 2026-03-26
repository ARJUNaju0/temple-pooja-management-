from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import FamilyMember
from .serializers import FamilyMemberSerializer

@login_required(login_url='/login/')
def family_tree_view(request):
    return render(request, 'family_tree/family_tree.html', {
        'is_admin': request.user.is_staff
    })

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_staff

class FamilyMemberViewSet(viewsets.ModelViewSet):
    queryset = FamilyMember.objects.all()
    serializer_class = FamilyMemberSerializer
    permission_classes = [IsAdminOrReadOnly]

    def perform_create(self, serializer):
        """Override create to handle spouse bidirectional relationship"""
        instance = serializer.save()
        self._sync_spouse_relationship(instance)

    def perform_update(self, serializer):
        """Override update to handle spouse bidirectional relationship"""
        old_spouse_id = self.get_object().spouse_id if self.get_object().spouse else None
        instance = serializer.save()
        
        # Clear old spouse relationship if changed
        if old_spouse_id and old_spouse_id != instance.spouse_id:
            try:
                old_spouse = FamilyMember.objects.get(id=old_spouse_id)
                if old_spouse.spouse == instance:
                    old_spouse.spouse = None
                    old_spouse.save(update_fields=['spouse'])
            except FamilyMember.DoesNotExist:
                pass
        
        self._sync_spouse_relationship(instance)

    def _sync_spouse_relationship(self, instance):
        """Ensure spouse relationship is bidirectional"""
        if instance.spouse and instance.spouse.spouse != instance:
            instance.spouse.spouse = instance
            instance.spouse.save(update_fields=['spouse'])
        elif not instance.spouse and hasattr(instance, '_old_spouse'):
            # Clear reverse relationship if spouse was removed
            pass

    @action(detail=False, methods=['get'])
    def tree_structure(self, request):
        members = FamilyMember.objects.select_related('spouse', 'parent').all()

        # Build a map of all members with references (not copies)
        node_map = {}
        for m in members:
            node_map[m.id] = {
                "id": m.id,
                "name": m.name,
                "gender": m.gender,
                "photo": m.photo.url if m.photo else None,
                "spouse_id": m.spouse.id if m.spouse else None,
                "parent_id": m.parent.id if m.parent else None,
                "children": []
            }

        # Build parent-child relationships
        roots = []
        for m in members:
            if m.parent_id and m.parent_id in node_map:
                # Add child to parent's children array
                node_map[m.parent_id]["children"].append(node_map[m.id])
            else:
                # No parent - this is a root node
                roots.append(node_map[m.id])

        return Response({
            "id": "root",
            "is_virtual_root": True,
            "children": roots
        })
    
    @action(detail=False, methods=['get'])
    def valid_parents(self, request):
        """
        Returns only valid parent options:
        - Root members (no parent) - they are the original blood line
        - Members who have a parent (blood relations only)
        
        EXCLUDES: Spouses who married into the family (they have no parent but are not roots)
        """
        members = FamilyMember.objects.select_related('spouse', 'parent').all()
        
        # Blood relations are:
        # 1. Root members (no parent, original ancestors)
        # 2. Anyone who HAS a parent (born into the family)
        
        blood_relation_ids = set()
        
        for member in members:
            if member.parent_id:
                # Has a parent = blood relation
                blood_relation_ids.add(member.id)
            elif not member.parent_id:
                # No parent - check if they're a true root or just a married-in spouse
                # A root member has no parent AND either:
                # - Has children (established lineage), OR
                # - Has no spouse (original ancestor), OR
                # - Their spouse also has no parent (both are roots)
                
                if member.children.exists():
                    # Has children, so this is an established blood line
                    blood_relation_ids.add(member.id)
                elif not member.spouse_id:
                    # No spouse, single root ancestor
                    blood_relation_ids.add(member.id)
                elif member.spouse and not member.spouse.parent_id:
                    # Both spouses have no parent - they're both roots
                    blood_relation_ids.add(member.id)
                # Otherwise, this person married into the family (has no parent, has a spouse who has children)
        
        # Return only blood relations
        valid_members = [m for m in members if m.id in blood_relation_ids]
        serializer = self.get_serializer(valid_members, many=True)
        return Response(serializer.data)