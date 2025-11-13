from django.urls import path
from . import views

urlpatterns = [
    # --- Main Site & Event Viewing ---
    path('', views.home, name='home'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),

    # --- Authentication ---
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # --- Event Creation & Management (for Organizers) ---
    path('add_event/', views.add_event_view, name='add_event'),
    path('organizer/event/<int:event_id>/edit/', views.edit_event_view, name='edit_event'),
    path('organizer/event/<int:pk>/delete/', views.EventDeleteView.as_view(), name='delete_event'),

    # --- Registration & SIMULATED Payment Flow ---
    path('event/<int:event_id>/register/', views.register_event_view, name='register_event'),
    path('event/<int:event_id>/pay/', views.payment_view, name='payment_page'),
    path('event/<int:event_id>/process_payment/', views.payment_simulation_view, name='payment_simulation'),
    path('registration/<int:registration_id>/confirmation/', views.registration_confirmation_view, name='registration_confirmation'),
    
    # --- User & Role Dashboards ---
    path('my_registrations/', views.my_registrations_view, name='my_registrations'),
    path('hod/dashboard/', views.hod_dashboard_view, name='hod_dashboard'),
    path('organizer/dashboard/', views.organizer_dashboard_view, name='organizer_dashboard'),
    
    # --- HOD Actions ---
    path('hod/event/<int:event_id>/review/', views.review_event_view, name='review_event'),
    path('hod/event/<int:event_id>/approve/', views.approve_event_view, name='approve_event'),
    path('hod/event/<int:event_id>/reject/', views.reject_event_view, name='reject_event_confirm'),

    # --- Organizer Tools ---
    path('event/<int:event_id>/scanner/', views.scanner_view, name='scanner'),
    path('check_in/', views.check_in_view, name='check_in'),
    path('organizer/event/<int:event_id>/participants/', views.view_participants_view, name='view_participants'),
    path('organizer/event/<int:event_id>/analytics/', views.analytics_dashboard_view, name='analytics_dashboard'),

    # --- Feedback ---
    path('event/<int:event_id>/feedback/', views.leave_feedback_view, name='leave_feedback'),
]

