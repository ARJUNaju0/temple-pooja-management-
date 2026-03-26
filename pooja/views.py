# D:\Django Internship\tprmsystem\pooja\views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, date, timedelta
from django.http import JsonResponse

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


from main.decorators import member_required, admin_required, admin_or_member_required 
from .models import Pooja
import re


# ==============================
#  MALAYALAM CALENDAR API
# ==============================
def api_ml_calendar(request, year, month):
    year = int(year)
    month = int(month)
    from kollavarsham import Kollavarsham
    # Kollavarsham settings
    kv = Kollavarsham(
        latitude=8.5241,     # Trivandrum
        longitude=76.9366,
        system="SuryaSiddhanta"
    )

    start = timezone.make_aware(datetime(year, month, 1))

    # Next month
    if month == 12:
        end = timezone.make_aware(datetime(year + 1, 1, 1))
    else:
        end = timezone.make_aware(datetime(year, month + 1, 1))

    days = []
    d = start

    while d < end:
        ml = kv.from_gregorian_date(d)

        days.append({
            "gregorian": d.date().isoformat(),
            "day": d.day,

            # Malayalam values
            "ml_day": ml.date,
            "ml_month": ml.ml_masa_name,
            "ml_year": ml.year,
            "ml_naksatra": ml.ml_naksatra_name,
        })

        d = d + timedelta(days=1)
        d = timezone.make_aware(d.replace(tzinfo=None))

    return JsonResponse({"days": days})


# ==============================
#  POOJA LIST API (USER)
# ==============================
#  1. UPDATED API ENDPOINT FOR BETTER FILTERING
# ==============================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_pooja_list(request):
    # Start with all active poojas
    poojas = Pooja.objects.filter(is_active=True)

    # --- Filter 1: Search by Name ---
    name_param = request.query_params.get('name', None)
    if name_param:
    # This excludes "Maha Ganapathi" if you search "Gan"
        poojas = poojas.filter(name__istartswith=name_param)

    # --- Filter 2: Date ---
    date_param = request.query_params.get('date', None)
    if date_param:
        try:
            filter_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            # Ensure the requested date is not in the past (optional strict check)
            if filter_date >= date.today():
                poojas = poojas.filter(pooja_date=filter_date)
            else:
                # If user tries to hack URL for past date, return empty or handle gracefully
                poojas = poojas.none() 
        except ValueError:
            pass

    # --- Filter 3: Type (Special vs Regular) ---
    category_param = request.query_params.get('category', None)
    if category_param:
        if category_param.lower() == 'special':
            poojas = poojas.filter(is_special_pooja=True)
        elif category_param.lower() == 'regular':
            poojas = poojas.filter(is_special_pooja=False)

    # Serialize Data
    data = [{
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "amount": float(p.amount),
        "pooja_date": p.pooja_date,
        "is_special_pooja": p.is_special_pooja,
        "available_slots": p.available_slots,
        "max_slots": p.max_slots,
    } for p in poojas]

    return Response({"poojas": data})



# ==============================
#  SINGLE POOJA DETAIL
# ==============================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_pooja_detail(request, pooja_id):
    p = get_object_or_404(Pooja, id=pooja_id)

    return Response({
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "amount": float(p.amount),
        "pooja_date": p.pooja_date,
        "is_special_pooja": p.is_special_pooja,
        "available_slots": p.available_slots,
        "max_slots": p.max_slots,
    })


# ==============================
#  FRONTEND PAGES
# ==============================
@admin_or_member_required
def pooja_services(request):
    poojas = Pooja.objects.filter(is_active=True).order_by('pooja_date', 'name')
    return render(request, 'pooja/pooja_service.html', {"poojas": poojas})


@admin_or_member_required
def calendar_view(request):    
    if not request.user.is_authenticated:
        return redirect('/login/')
    return render(request, 'pooja/calendar.html')


# ==============================
#  ADMIN — MANAGE POOJAS
# ==============================
@admin_required
def admin_manage_poojas(request):
    poojas = Pooja.objects.all().order_by('-created_at')
    return render(request, 'pooja/admin_manage.html', {"poojas": poojas})


# ==============================
#  ADMIN — ADD POOJA
# ==============================
@admin_required
def admin_add_pooja(request):
    context = {}
    
    if request.method == "POST":
        name = request.POST.get('name', '')
        description = request.POST.get('description', '')
        amount = request.POST.get('amount', 0)
        pooja_date_str = request.POST.get('pooja_date', None)
        is_special = "is_special" in request.POST
        allow_multiple_bookings = "allow_multiple_bookings" in request.POST

        # Prepare context with form data
        context.update({
            'name': name,
            'description': description,
            'amount': amount,
            'pooja_date': pooja_date_str,
            'is_special': is_special,
            'allow_multiple_bookings': allow_multiple_bookings,
        })

        # Slots handling
        enable_slots = 'enable_slots' in request.POST
        context['enable_slots'] = enable_slots
        
        if enable_slots:
            try:
                available_slots = int(request.POST.get('available_slots', 1))
                max_slots = int(request.POST.get('max_slots', 1))
                context.update({
                    'available_slots': available_slots,
                    'max_slots': max_slots
                })
            except (ValueError, TypeError):
                messages.error(request, "Invalid slot values. Please enter valid numbers.")
                return render(request, "pooja/admin_add.html", context)
        else:
            # When slots are disabled, set both to 5000
            available_slots = 5000
            max_slots = 5000
            context.update({
                'available_slots': available_slots,
                'max_slots': max_slots
            })

        # Amount validation
        try:
            amount = float(amount)
            if amount < 0:
                messages.error(request, "Amount cannot be negative.")
                return render(request, "pooja/admin_add.html", context)
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount format. Please enter a valid number.")
            return render(request, "pooja/admin_add.html", context)

        # Slot validation
        if available_slots > max_slots:
            messages.error(request, "Available slots cannot exceed maximum slots.")
            return render(request, "pooja/admin_add.html", context)

        # Name validation
        if not re.match(r'^[a-zA-Z\s\-\'.]{3,200}$', name):
            messages.error(request, 'Pooja name can only contain letters, spaces, hyphens (-), apostrophes (\'), and periods (.). Minimum 3 characters.')
            return render(request, "pooja/admin_add.html", context)
            
        # Duplicate name check for same date (case-insensitive)
        if pooja_date_str:
            if Pooja.objects.filter(name__iexact=name, pooja_date=pooja_date_str).exists():
                messages.error(request, f"A pooja with name '{name}' already exists on the selected date.")
                return render(request, "pooja/admin_add.html", context)

        # Date validation
        if pooja_date_str:
            try:
                pooja_date = datetime.strptime(pooja_date_str, '%Y-%m-%d').date()
                if pooja_date < date.today():
                    messages.error(request, "Pooja date must be today or in the future.")
                    return render(request, "pooja/admin_add.html", {
                        'name': name,
                        'description': description,
                        'amount': amount,
                        'pooja_date': pooja_date_str,
                        'is_special': is_special,
                        'available_slots': available_slots,
                        'max_slots': max_slots,
                        'today': date.today().isoformat()
                    })
            except ValueError:
                messages.error(request, "Invalid date format. Please use YYYY-MM-DD format.")
                return render(request, "pooja/admin_add.html", {
                    'name': name,
                    'description': description,
                    'amount': amount,
                    'pooja_date': pooja_date_str,
                    'is_special': is_special,
                    'available_slots': available_slots,
                    'max_slots': max_slots,
                    'today': date.today().isoformat()
                })

        # SAVE
        pooja = Pooja(
            name=name,
            description=description,
            amount=amount,
            is_special_pooja=is_special,
            created_by=request.user,
            updated_by=request.user,
            available_slots=available_slots,
            max_slots=max_slots,
            allow_multiple_bookings=allow_multiple_bookings,
        )

        if pooja_date_str:
            pooja.pooja_date = pooja_date_str

        pooja.save()
        messages.success(request, f"Pooja '{name}' added successfully.")
        return redirect("/poojas")

    # Default values for new pooja form
    return render(request, "pooja/admin_add.html", {
        "today": date.today().isoformat(),
        "max_slots": 1,
        "available_slots": 1,
        "enable_slots": True,
        "allow_multiple_bookings": False
    })


# ==============================
#  ADMIN — EDIT POOJA
# ==============================
@admin_required
def admin_edit_pooja(request, pooja_id):
    pooja = get_object_or_404(Pooja, id=pooja_id)

    if request.method == "POST":
        name = request.POST['name']

        # Duplicate check
        if Pooja.objects.filter(name__iexact=name).exclude(id=pooja_id).exists():
            messages.error(request, f"A pooja with name '{name}' already exists.")
            return render(request, "pooja/admin_edit.html", {"pooja": pooja})

        pooja.name = name
        pooja.description = request.POST.get('description', '')
        pooja.amount = float(request.POST.get('amount', 0))
        pooja.is_special_pooja = "is_special" in request.POST
        pooja.allow_multiple_bookings = "allow_multiple_bookings" in request.POST
        pooja.pooja_date = request.POST.get("pooja_date") or None
        pooja.updated_by = request.user

        pooja.available_slots = int(request.POST.get('available_slots', 1))
        pooja.max_slots = int(request.POST.get('max_slots', 1))

        if pooja.available_slots > pooja.max_slots:
            messages.error(request, "Available slots cannot exceed maximum slots.")
            return render(request, "pooja/admin_edit.html", {"pooja": pooja})

        pooja.save()
        messages.success(request, f"Pooja '{name}' updated successfully.")
        return redirect("/poojas")

    return render(request, "pooja/admin_edit.html", {"pooja": pooja})


# ==============================
#  ADMIN — DELETE POOJA
# ==============================
@admin_required
def admin_delete_pooja(request, pooja_id):
    pooja = get_object_or_404(Pooja, id=pooja_id)
    pooja_name = pooja.name
    pooja.delete()
    messages.success(request, f"Pooja '{pooja_name}' deleted successfully.")
    return redirect("/poojas")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_pooja_calendar_events(request):
    """
    Returns all pooja events grouped by date with color coding:
    - green  → available slots > 50%
    - yellow → available slots <= 50% but not zero
    - red    → no available slots
    """
    poojas = Pooja.objects.filter(is_active=True).order_by("pooja_date")

    events = {}

    for p in poojas:
        if not p.pooja_date:
            continue  # skip poojas without a date

        date_str = p.pooja_date.isoformat()

        # Safety conversion
        available = int(p.available_slots)
        max_slots = int(p.max_slots)

        # Determine color
        if max_slots == 0:
            color = "red"
        else:
            ratio = available / max_slots

            if available == 0:
                color = "red"
            elif ratio <= 0.5:
                color = "yellow"
            else:
                color = "green"

        if date_str not in events:
            events[date_str] = []

        events[date_str].append({
            "id": p.id,
            "name": p.name,
            "type": "special" if p.is_special_pooja else "normal",
            "available_slots": available,
            "max_slots": max_slots,
            "amount": float(p.amount),
            "color": color,   # <-- ADDED COLOR HERE
        })

    return Response({"events": events})

#  MEMBER POOJA PAGE 
# ==============================
def member_pooja_services(request):
    if not request.user.is_authenticated:
        return redirect('login')

    role = request.user.role
    poojas = Pooja.objects.filter(is_active=True).order_by('pooja_date', 'name')

    if role == 'temple_admin' or request.user.is_staff:
        # Admin allowed only admin page
        return render(request, 'pooja/pooja_service.html', {"poojas": poojas})

    elif role == 'member':
        # Member allowed only member page
        return render(request, 'pooja/service.html')

    # Anything else → unauthorized
    return render(request, 'main/unauthorized.html', status=403)



def search_pooja(request):
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"results": []})

    poojas = Pooja.objects.filter(name__icontains=q).values("id", "name", "amount")
    return JsonResponse({"results": list(poojas)})

