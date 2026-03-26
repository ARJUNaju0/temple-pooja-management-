#temple_admin views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from main.decorators import admin_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import AdminActivityLog
from .forms import AddMemberForm
from .models import TempleAdmin
from .models import SiteSettings
import json
from django.http import JsonResponse
from booking.models import PoojaBooking





def login_page(request):
    return redirect('/login/')


@admin_required
@login_required(login_url='/login/')
def dashboard_view(request):
    """
    Protected Admin Dashboard View
    Only accessible by Temple Admins
    """

    # Check if user is admin/staff
    if not (request.user.is_staff or request.user.role == 'temple_admin'):
        return redirect('/member/dashboard/')
    
    # Get or create site settings
    settings = SiteSettings.objects.first()
    if not settings:
        settings = SiteSettings.objects.create(allow_multiple_bookings=False)
    
    show_all = request.GET.get('show_all', '').lower() == 'true'
    members = TempleAdmin.objects.filter(role='member').order_by('-date_joined')
    total_members = members.count()
    members = members[:5]
    
    # Get booking statistics
    from django.db.models import Count
    from django.utils import timezone
    
    # Get all bookings count
    total_bookings = PoojaBooking.objects.count()
    
    # Get counts by status
    status_counts = PoojaBooking.objects.values('status').annotate(count=Count('status'))
    status_dict = {item['status']: item['count'] for item in status_counts}
    
    # Get recent bookings for activity feed (last 5)
    recent_bookings = PoojaBooking.objects.select_related('user', 'pooja').order_by('-booked_at')[:5]
    
    # Count active services (poojas)
    from pooja.models import Pooja
    active_services = Pooja.objects.filter(is_active=True).count()
    
    # Today's bookings
    today = timezone.now().date()
    today_bookings = PoojaBooking.objects.filter(booked_at__date=today).count()
    services = Pooja.objects.filter(is_active=True).select_related('category')
    # Get active poojas for the dashboard
    active_poojas = Pooja.objects.filter(is_active=True).order_by('name')[:6]  # Show first 6 active poojas
    
    context = {
        'total_members': total_members,
        'members': members,
        'show_all': show_all,
        'active_services': active_services,
        'bookings': today_bookings,
        'total_bookings': total_bookings,
        'approved_bookings': status_dict.get('approved', 0),
        'pending_bookings': status_dict.get('pending', 0),
        'cancelled_bookings': status_dict.get('cancelled', 0),
        'recent_bookings': recent_bookings,
        'user': request.user,
        'settings': settings,
        'poojas': active_poojas,
        'poojas_count': Pooja.objects.filter(is_active=True).count()
    }
    return render(request, 'temple_admin/dashboard.html', context)


#member creation view and setting tem pasword to members

# Decorator to check if user is a Temple Admin
def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.role == 'temple_admin')

@login_required(login_url='/login/') 
@user_passes_test(is_admin, login_url='/login/')
def add_member_view(request):
    if request.method == 'POST':
        form = AddMemberForm(request.POST)
        if form.is_valid():
            try:
                # Create member exactly like in shell
                new_member = TempleAdmin.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    role='member'
                )
                
                # Log Activity
                AdminActivityLog.objects.create(
                    admin=request.user,
                    action="Added Member",
                    description=f"Created member: {new_member.username} ({new_member.email})",
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                messages.success(request, f"Member '{new_member.username}' created successfully.")
                return redirect('temple_admin:dashboard')
            except Exception as e:
                messages.error(request, f"Error: {e}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AddMemberForm()

    return render(request, 'temple_admin/add_member.html', {'form': form})

@admin_required
@login_required
def update_settings(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        settings = SiteSettings.objects.first()
        
        if not settings:
            settings = SiteSettings(allow_multiple_bookings=False)
            
        if 'allow_multiple_bookings' in data:
            settings.allow_multiple_bookings = data['allow_multiple_bookings']
            settings.save()
            
        return JsonResponse({
            'status': 'success',
            'message': 'Settings updated successfully',
            'settings': {
                'allow_multiple_bookings': settings.allow_multiple_bookings
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)