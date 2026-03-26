from functools import wraps
import logging
from django.shortcuts import redirect, render

logger = logging.getLogger(__name__)

def admin_or_member_required(view_func):
    # Allow both Admins and Members to access the view.
    # Block any other type of user.

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        # Not logged in → redirect to login
        if not request.user.is_authenticated:
            return redirect('/login/')

        # If user is admin
        if request.user.is_staff or request.user.role == 'temple_admin':
            return view_func(request, *args, **kwargs)

        # If user is member
        if request.user.role == 'member':
            return view_func(request, *args, **kwargs)

        # Any other role → unauthorized
        return render(request, 'main/unauthorized.html', status=403)

    return wrapper


# ACCESS CONTROL DECORATORS 
def member_required(view_func):
    """
    Decorator to ensure only members (not admins) can access the view
    Shows unauthorized page if admin tries to access
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        # Show unauthorized page if admin tries to access member pages
        if request.user.is_staff or request.user.role == 'temple_admin':
            return render(request, 'main/unauthorized.html', status=403)
        
        # Ensure user is a member
        if request.user.role != 'member':
            return render(request, 'main/unauthorized.html', status=403)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

def admin_required(view_func):
    """
    Decorator to ensure only admins can access the view
    Shows unauthorized page if member tries to access
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        logger.debug(f"[admin_required] Checking access for user: {request.user}")
        logger.debug(f"[admin_required] is_authenticated: {request.user.is_authenticated}")
        logger.debug(f"[admin_required] User role: {getattr(request.user, 'role', 'no-role')}")
        logger.debug(f"[admin_required] is_staff: {getattr(request.user, 'is_staff', False)}")
        
        if not request.user.is_authenticated:
            logger.warning("[admin_required] User not authenticated, redirecting to login")
            return redirect('/login/')
        
        # Show unauthorized page if member tries to access admin pages
        if request.user.role == 'member' and not request.user.is_staff:
            logger.warning(f"[admin_required] Unauthorized access attempt by member: {request.user}")
            return render(request, 'main/unauthorized.html', status=403)
        
        # Ensure user is admin
        is_admin = request.user.is_staff or request.user.role == 'temple_admin'
        logger.debug(f"[admin_required] is_admin check: {is_admin} (is_staff={request.user.is_staff}, role={request.user.role})")
        
        if not is_admin:
            logger.warning(f"[admin_required] Access denied - User is not admin: {request.user}")
            return render(request, 'main/unauthorized.html', status=403)
        
        logger.debug(f"[admin_required] Access granted to admin: {request.user}")
        return view_func(request, *args, **kwargs)
    
    return wrapper


