from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('add_event/', views.add_event_view, name='add_event'),
    path('event/<int:event_id>/register/', views.register_event_view, name='register_event'),
    path('registration/<int:registration_id>/confirmation/', views.registration_confirmation_view, name='registration_confirmation'),
    path('my_registrations/', views.my_registrations_view, name='my_registrations'),
    path('hod/dashboard/', views.hod_dashboard_view, name='hod_dashboard'),
    path('hod/event/<int:event_id>/approve/', views.approve_event_view, name='approve_event'),
    path('hod/event/<int:event_id>/reject/', views.reject_event_view, name='reject_event_confirm'),
    path('event/<int:event_id>/scanner/', views.scanner_view, name='scanner'),
    path('check_in/', views.check_in_view, name='check_in'),
    path('organizer/dashboard/', views.organizer_dashboard_view, name='organizer_dashboard'),
    path('organizer/event/<int:event_id>/participants/', views.view_participants_view, name='view_participants'),
    path('organizer/event/<int:event_id>/edit/', views.edit_event_view, name='edit_event'),
    path('organizer/event/<int:pk>/delete/', views.EventDeleteView.as_view(), name='delete_event'),
    path('event/<int:event_id>/feedback/', views.leave_feedback_view, name='leave_feedback'),
    path('organizer/event/<int:event_id>/analytics/', views.analytics_dashboard_view, name='analytics_dashboard'),
]