from django.urls import path
from . import views

urlpatterns = [
    # ========================================
    # ORIGINAL URLS (UNCHANGED)
    # ========================================
    
    # Your original online booking URL structure
    path("pooja/<int:pooja_id>/book/", views.book_pooja, name="book_pooja"),
    path("payment-handler/", views.paymenthandler, name="payment_handler"),
    path('book/success/<int:booking_id>/', views.booking_success, name='booking_success'),
    
    # Your original member URLs
    path('history/', views.member_booking_history, name='member_booking_history'),
    path('cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    
    # Your original admin URLs
    path('admin/all-bookings/', views.admin_all_bookings, name='admin_all_bookings'),
    path('admin/bookings-by-member/<int:user_id>/', views.admin_member_bookings, name='admin_member_bookings'),
    
    # ========================================
    # NEW: OFFLINE PAYMENT URLS (ADDED)
    # ========================================
    
    # Offline booking (UPI QR or Cash)
    path("offline/<int:pooja_id>/", views.offline_book_pooja, name="offline_book_pooja"),
    path('offline/success/<int:booking_id>/', views.offline_booking_success, name='offline_booking_success'),
    
    # Payment history (NEW)
    path('admin/payment-history/', views.admin_payment_history, name='admin_payment_history'),
    
    # ========================================
    # NEW: ADMIN API ENDPOINTS (ADDED)
    # ========================================
    
    path('api/booking/approve/', views.api_approve_booking, name='api_approve_booking'),
    path('api/booking/cancel/', views.api_cancel_booking, name='api_cancel_booking'),
    path('api/bookings/admin/list/', views.api_admin_bookings_list, name='api_admin_bookings_list'),
    path('api/payments/history/', views.api_payments_history, name='api_payments_history'),
    path('api/booking/mark-as-paid/', views.api_mark_as_paid, name='api_mark_as_paid'),
    path('api/payment/update-status/', views.drf_payment_update_status, name='api_payment_update_status'),
    path('api/payment/mark-cash-paid/', views.api_mark_cash_paid, name='api_mark_cash_paid'),

    # Admin refund endpoint
    path('admin/refund-booking/<int:booking_id>/', views.admin_refund_booking, name='admin_refund_booking'),
    
    #admin reports
    path("api/admin/reports/bookings/",views.admin_booking_report_api,name="admin_booking_report_api"),
    path("admin/reports/bookings/",views.admin_daily_report_page,name="admin_daily_report_page"),
    path("api/admin/payment-report/", views.admin_payment_report_api,name="admin_payment_report_api"),
    path("api/admin/payment-report/csv/",views.admin_payment_report_csv,name="admin_payment_report_csv"),
    path("admin/payment-report/",views.admin_payment_report_page,name="admin_payment_report_page"),
    path("admin/members/",views.admin_member_list_page,name="admin_member_list_page"),
    path("api/admin/members/", views.admin_member_list_api,name="admin_member_list_api"),
    path("api/admin/members/<int:member_id>/bookings/", views.admin_member_bookings_api,name='admin_member_bookings_api'),
    path("admin/members/<int:member_id>/",views.admin_member_bookings_page,name="admin_member_bookings_page"),
    ]

    
