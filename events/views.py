from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.db import models
from django.db.models import Avg, Count, Q
from django.db.models.functions import Round
from django.utils import timezone
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic.edit import DeleteView
from django.core.paginator import Paginator
import logging

from .models import Event, Profile, Registration, Feedback
from .forms import (
    CustomUserCreationForm,
    EventForm,
    FeedbackForm,
    RejectionForm,
    EventApprovalForm
)
import re
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
import json
import os

# Imports for PDF Generation
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)

# --- Helper Functions ---

def link_callback(uri, rel):
    sUrl = settings.STATIC_URL
    sRoot = settings.STATIC_ROOT
    mUrl = settings.MEDIA_URL
    mRoot = settings.MEDIA_ROOT
    if uri.startswith(mUrl):
        path = os.path.join(mRoot, uri.replace(mUrl, ""))
    elif uri.startswith(sUrl):
        path = os.path.join(sRoot, uri.replace(sUrl, ""))
    else:
        return uri
    if not os.path.isfile(path):
        raise Exception('media URI must start with %s or %s' % (sUrl, mUrl))
    return path

def html_to_pdf(template_src, context_dict={}):
    html = render_to_string(template_src, context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, link_callback=link_callback)
    if not pdf.err:
        return result.getvalue()
    return None

def get_embed_url(url):
    if not url:
        return None
    youtube_regex = (
        r"(https?://)?(www\.)?"
        r"(youtube|youtu|youtube-nocookie)\.(com|be)/"
        r"(watch\?v=|embed/|v/|live/|.+\?v=)?([^&=%\?]{11})"
    )
    vimeo_regex = r"(https?://)?(www\.)?vimeo\.com/(\d+)"
    youtube_match = re.search(youtube_regex, url)
    if youtube_match:
        return f'https://www.youtube.com/embed/{youtube_match.group(6)}'
    vimeo_match = re.search(vimeo_regex, url)
    if vimeo_match:
        return f'https://player.vimeo.com/video/{vimeo_match.group(3)}'
    return None

# --- Main Views ---

def home(request):
    query = request.GET.get('q', '')
    event_filter = request.GET.get('filter', '')
    events_qs = Event.objects.filter(status='Approved').order_by('start_time')
    if query:
        events_qs = events_qs.filter(title__icontains=query)
    if event_filter == 'online':
        events_qs = events_qs.filter(Q(event_mode='Online') | Q(event_mode='Hybrid'))
    elif event_filter == 'in-person':
        events_qs = events_qs.filter(Q(event_mode='In-Person') | Q(event_mode='Hybrid'))
    elif event_filter == 'hybrid':
        events_qs = events_qs.filter(event_mode='Hybrid')
    paginator = Paginator(events_qs, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj, 'query': query, 'event_filter': event_filter}
    return render(request, 'events/home.html', context)

def event_detail(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    registration = None
    if request.user.is_authenticated:
        try:
            registration = Registration.objects.get(event=event, attendee=request.user)
        except Registration.DoesNotExist:
            registration = None
    embed_url = get_embed_url(event.stream_url)
    context = {'event': event, 'registration': registration, 'embed_url': embed_url}
    return render(request, 'events/event_detail.html', context)

# --- Authentication Views ---

def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(
                user=user,
                defaults={'role': form.cleaned_data.get('role')}
            )
            login(request, user)
            messages.success(request, f'Account created successfully! Welcome, {user.username}.')
            return redirect('home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'events/signup.html', {'signup_form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Login successful! Welcome back, {user.username}.")
            next_url = request.GET.get('next')
            return redirect(next_url) if next_url else redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'events/login.html', {'login_form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('home')

# --- Event Management Views ---

@login_required
def add_event_view(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'Organizer':
        messages.error(request, 'You do not have permission to create an event.')
        return redirect('home')
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.status = 'Pending Approval'
            event.save()
            messages.success(request, f'Event "{event.title}" has been submitted for approval.')
            return redirect('organizer_dashboard')
    else:
        form = EventForm()
    return render(request, 'events/add_event.html', {'form': form})

@login_required
def edit_event_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if event.organizer != request.user:
        messages.error(request, 'You do not have permission to edit this event.')
        return redirect('organizer_dashboard')
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save(commit=False)
            event.status = 'Pending Approval'
            event.save()
            messages.success(request, f'Event "{event.title}" has been updated and resubmitted for approval.')
            return redirect('organizer_dashboard')
    else:
        form = EventForm(instance=event)
    context = {'form': form, 'event': event}
    return render(request, 'events/edit_event.html', context)

class EventDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Event
    template_name = 'events/delete_event_confirm.html'
    success_url = reverse_lazy('organizer_dashboard')

    def test_func(self):
        event = self.get_object()
        return self.request.user == event.organizer

    def form_valid(self, form):
        messages.success(self.request, f'The event "{self.object.title}" has been successfully deleted.')
        return super().form_valid(form)

# --- Registration & Payment Views ---

@login_required
def register_event_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if event.is_full:
        messages.error(request, f'Sorry, "{event.title}" is already full.')
        return redirect('event_detail', event_id=event.id)

    if Registration.objects.filter(event=event, attendee=request.user).exists():
        messages.warning(request, f'You are already registered for "{event.title}".')
        return redirect('event_detail', event_id=event.id)

    if event.entry_fee == 'Paid':
        return redirect('payment_page', event_id=event.id)

    registration = Registration.objects.create(event=event, attendee=request.user)
    current_site = get_current_site(request)
    protocol = 'https' if request.is_secure() else 'http'
    event_path = reverse('event_detail', args=[event.id])
    event_url = f"{protocol}://{current_site.domain}{event_path}"
    mail_subject = f'Your Ticket for {event.title}'
    email_context = {'user': request.user, 'event': event, 'event_url': event_url}
    html_content = render_to_string('events/emails/registration_confirmation.html', email_context)
    text_content = render_to_string('events/emails/registration_confirmation.txt', email_context)
    email = EmailMultiAlternatives(mail_subject, text_content, settings.EMAIL_HOST_USER, [request.user.email])
    email.attach_alternative(html_content, "text/html")

    if event.event_mode != 'Online':
        qr_data = f'REG-{registration.id}-{event.id}-{request.user.username}'
        buffer = BytesIO()
        qrcode.make(qr_data).save(buffer, format='PNG')
        file_name = f'reg_{registration.id}.png'
        registration.qr_code_path.save(file_name, ContentFile(buffer.getvalue()))
        pdf_context = {'event': event, 'registration': registration, 'qr_code_path': registration.qr_code_path.path}
        pdf = html_to_pdf('events/emails/ticket_template.html', pdf_context)
        if pdf:
            email.attach(f'Ticket-{event.title}.pdf', pdf, 'application/pdf')
    email.send()
    messages.success(request, f'You have successfully registered for "{event.title}". A confirmation email has been sent.')
    return redirect('registration_confirmation', registration_id=registration.id)

@login_required
def payment_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    return render(request, 'events/payment_page.html', {'event': event})

@login_required
def process_payment_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if event.is_full or Registration.objects.filter(event=event, attendee=request.user).exists():
        messages.error(request, 'Registration failed. The event might be full or you are already registered.')
        return redirect('event_detail', event_id=event.id)

    registration = Registration.objects.create(event=event, attendee=request.user)
    current_site = get_current_site(request)
    protocol = 'https' if request.is_secure() else 'http'
    event_path = reverse('event_detail', args=[event.id])
    event_url = f"{protocol}://{current_site.domain}{event_path}"
    mail_subject = f'Your Ticket for {event.title}'
    email_context = {'user': request.user, 'event': event, 'event_url': event_url}
    html_content = render_to_string('events/emails/registration_confirmation.html', email_context)
    text_content = render_to_string('events/emails/registration_confirmation.txt', email_context)
    email = EmailMultiAlternatives(mail_subject, text_content, settings.EMAIL_HOST_USER, [request.user.email])
    email.attach_alternative(html_content, "text/html")

    if event.event_mode != 'Online':
        qr_data = f'REG-{registration.id}-{event.id}-{request.user.username}'
        buffer = BytesIO()
        qrcode.make(qr_data).save(buffer, format='PNG')
        file_name = f'reg_{registration.id}.png'
        registration.qr_code_path.save(file_name, ContentFile(buffer.getvalue()))
        pdf_context = {'event': event, 'registration': registration, 'qr_code_path': registration.qr_code_path.path}
        pdf = html_to_pdf('events/emails/ticket_template.html', pdf_context)
        if pdf:
            email.attach(f'Ticket-{event.title}.pdf', pdf, 'application/pdf')
    email.send()
    messages.success(request, f'Payment successful! You are now registered for "{event.title}". A confirmation email has been sent.')
    return redirect('registration_confirmation', registration_id=registration.id)

@login_required
def registration_confirmation_view(request, registration_id):
    registration = get_object_or_404(Registration, pk=registration_id, attendee=request.user)
    return render(request, 'events/registration_confirmation.html', {'registration': registration})

# --- Dashboard Views ---
@login_required
def my_registrations_view(request):
    now = timezone.now()
    all_registrations = Registration.objects.filter(attendee=request.user).select_related('event').order_by('event__start_time')
    upcoming_registrations = all_registrations.filter(event__end_time__gte=now)
    past_registrations = all_registrations.filter(event__end_time__lt=now).order_by('-event__start_time')
    context = {
        'upcoming_registrations': upcoming_registrations,
        'past_registrations': past_registrations,
    }
    return render(request, 'events/my_registrations.html', context)

@login_required
def organizer_dashboard_view(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'Organizer':
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('home')
    organized_events = Event.objects.filter(organizer=request.user).order_by('-start_time')
    total_events = organized_events.count()
    pending_events_count = organized_events.filter(status='Pending Approval').count()
    registrations_aggregates = Registration.objects.filter(event__in=organized_events).aggregate(
        total_registrations=Count('id'),
        total_checked_in=Count('id', filter=Q(attended=True))
    )
    total_registrations = registrations_aggregates.get('total_registrations', 0)
    total_checked_in = registrations_aggregates.get('total_checked_in', 0)
    for event in organized_events:
        registrations = Registration.objects.filter(event=event)
        event.checked_in_count = registrations.filter(attended=True).count()
        event.registrations_count = registrations.count()
    context = {
        'organized_events': organized_events,
        'total_events': total_events,
        'pending_events_count': pending_events_count,
        'total_registrations': total_registrations,
        'total_checked_in': total_checked_in,
    }
    return render(request, 'events/organizer_dashboard.html', context)

@login_required
def view_participants_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if event.organizer != request.user:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('organizer_dashboard')
    registrations = Registration.objects.filter(event=event).order_by('attendee__username')
    return render(request, 'events/view_participants.html', {'event': event, 'registrations': registrations})

# --- HOD Views ---
@staff_member_required
def hod_dashboard_view(request):
    pending_events = Event.objects.filter(status='Pending Approval').order_by('start_time')
    return render(request, 'events/hod_dashboard.html', {'pending_events': pending_events})

@staff_member_required
def review_event_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id, status='Pending Approval')
    return render(request, 'events/review_event.html', {'event': event})

@staff_member_required
def approve_event_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.method == 'POST':
        form = EventApprovalForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save(commit=False)
            event.status = 'Approved'
            event.save()
            messages.success(request, f'The event "{event.title}" has been approved and a location has been assigned.')
            current_site = get_current_site(request)
            mail_subject = f'Your Event "{event.title}" has been Approved'
            email_context = {
                'organizer': event.organizer, 'event': event, 'domain': current_site.domain
            }
            html_content = render_to_string('events/emails/event_status_notification.html', email_context)
            text_content = render_to_string('events/emails/event_status_notification.txt', email_context)
            email = EmailMultiAlternatives(mail_subject, text_content, settings.EMAIL_HOST_USER, [event.organizer.email])
            email.attach_alternative(html_content, "text/html")
            email.send()
            return redirect('hod_dashboard')
    else:
        form = EventApprovalForm(instance=event)
    return render(request, 'events/approve_event.html', {'event': event, 'form': form})

@staff_member_required
def reject_event_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.method == 'POST':
        form = RejectionForm(request.POST)
        if form.is_valid():
            event.status = 'Rejected'
            event.rejection_reason = form.cleaned_data['rejection_reason']
            event.save()
            messages.warning(request, f'The event "{event.title}" has been rejected.')
            current_site = get_current_site(request)
            mail_subject = f'Update on your Event: "{event.title}"'
            email_context = {
                'organizer': event.organizer, 'event': event, 'domain': current_site.domain
            }
            html_content = render_to_string('events/emails/event_status_notification.html', email_context)
            text_content = render_to_string('events/emails/event_status_notification.txt', email_context)
            email = EmailMultiAlternatives(mail_subject, text_content, settings.EMAIL_HOST_USER, [event.organizer.email])
            email.attach_alternative(html_content, "text/html")
            email.send()
            return redirect('hod_dashboard')
    else:
        form = RejectionForm()
    return render(request, 'events/reject_event_confirm.html', {'event': event, 'form': form})

# --- Scanner Views ---
@login_required
def scanner_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if event.organizer != request.user:
        messages.error(request, "You do not have permission to access the scanner for this event.")
        return redirect('organizer_dashboard')
    return render(request, 'events/scanner.html', {'event': event})

@csrf_exempt
@login_required
def check_in_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            qr_data = data.get('qr_data')
            current_event_id = data.get('current_event_id')
            event = get_object_or_404(Event, pk=current_event_id)
            if event.organizer != request.user:
                return HttpResponseForbidden("You do not have permission to perform this action.")
            parts = qr_data.split('-')
            if len(parts) != 4 or parts[0] != 'REG':
                return JsonResponse({'status': 'error', 'message': 'Invalid QR Code: Incorrect format.'})
            reg_id, event_id_from_qr = parts[1], parts[2]
            if str(current_event_id) != event_id_from_qr:
                other_event = get_object_or_404(Event, pk=event_id_from_qr)
                return JsonResponse({'status': 'error', 'message': f'Invalid QR Code: This ticket is for "{other_event.title}", not the current event.'})
            registration = get_object_or_404(Registration, pk=reg_id)
            if registration.attended:
                return JsonResponse({'status': 'warning', 'message': f'Warning! {registration.attendee.username} has already been checked in.'})
            registration.attended = True
            registration.attended_at = timezone.now()
            registration.save()
            return JsonResponse({'status': 'success', 'message': f'Success! Checked in {registration.attendee.username}.'})
        except (Registration.DoesNotExist, Event.DoesNotExist):
            return JsonResponse({'status': 'error', 'message': 'Invalid QR Code: Registration or Event not found.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

# --- Feedback Views ---
@login_required
def leave_feedback_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    try:
        registration = Registration.objects.get(event=event, attendee=request.user)
    except Registration.DoesNotExist:
        messages.error(request, "You are not registered for this event.")
        return redirect('my_registrations')
    if registration.has_submitted_feedback():
        messages.warning(request, "You have already submitted feedback for this event.")
        return redirect('my_registrations')
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.event = event
            feedback.user = request.user
            feedback.save()
            messages.success(request, "Thank you for your feedback! It has been submitted successfully.")
            return redirect('my_registrations')
    else:
        form = FeedbackForm()
    context = {'form': form, 'event': event}
    return render(request, 'events/leave_feedback.html', context)

# --- Analytics Views ---
@login_required
def analytics_dashboard_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.user != event.organizer:
        messages.error(request, "You are not authorized to view this page.")
        return redirect('organizer_dashboard')
    feedback_data = Feedback.objects.filter(event=event)
    total_responses = feedback_data.count()
    if total_responses > 0:
        average_rating = feedback_data.aggregate(avg=Round(Avg('rating'), 2))['avg']
    else:
        average_rating = "N/A"
    rating_counts_query = feedback_data.values('rating').annotate(count=Count('rating'))
    rating_map = {item['rating']: item['count'] for item in rating_counts_query}
    chart_labels = [f'{i} Star' for i in range(1, 6)]
    chart_data = [rating_map.get(i, 0) for i in range(1, 6)]
    recent_comments = feedback_data.exclude(comment__isnull=True).exclude(comment__exact='').order_by('-submitted_at')[:10]
    context = {
        'event': event,
        'total_responses': total_responses,
        'average_rating': average_rating,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'recent_comments': recent_comments,
    }
    return render(request, 'events/analytics_dashboard.html', context)

