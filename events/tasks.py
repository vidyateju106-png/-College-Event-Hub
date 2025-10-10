from django.utils import timezone
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.contrib.sites.models import Site
from .models import Event, Registration
from datetime import timedelta

def complete_past_events():
    """
    A scheduled task that finds events whose end time has passed,
    updates their status to 'Completed', and sends a feedback request
    email to all registered attendees.
    """
    now = timezone.now()
    local_now = timezone.localtime(now)
    print(f"[{local_now.strftime('%Y-%m-%d %H:%M:%S')}] --- Running Scheduled Task: Checking for past events ---")
    print(f"Current UTC time is: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # The event should be marked Completed immediately after end_time has passed.
    events_to_complete = Event.objects.filter(status='Approved', end_time__lt=now)

    # Use configured grace window for sending feedback (default 1 minute)
    grace_minutes = getattr(settings, 'FEEDBACK_GRACE_PERIOD_MINUTES', 1)
    feedback_grace = timedelta(minutes=grace_minutes)

    # Phase 1: mark Approved events as Completed (do this immediately)
    if events_to_complete.exists():
        for event in events_to_complete:
            print(f"Processing event for completion: '{event.title}' (ID: {event.id})")
            print(f"--> Event End Time (UTC): {event.end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            event.status = 'Completed'
            event.save()
            print(f"--> Status for '{event.title}' updated to Completed.")
    else:
        print("No events found to mark as completed.")

    # Phase 2: send feedback emails for events whose end_time + grace has passed.
    send_cutoff = now - feedback_grace
    send_ready_events = Event.objects.filter(status__in=['Approved', 'Completed'], end_time__lte=send_cutoff)

    if not send_ready_events.exists():
        print("No events are ready for feedback sending at this time.")
        print("--- Scheduled Task Finished ---")
        return

    for event in send_ready_events:
        print(f"Processing event for feedback sending: '{event.title}' (ID: {event.id})")
        print(f"--> Event End Time (UTC): {event.end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

        registrations = Registration.objects.filter(event=event)
        print(f"--> Found {registrations.count()} registrations for this event.")

        for reg in registrations:
            attendee = reg.attendee

            # Skip if feedback already sent or user has no email
            if reg.feedback_request_sent_at is not None:
                print(f"----> Skipping {attendee.username}: feedback_request_sent_at already set.")
                continue

            if reg.has_submitted_feedback():
                print(f"----> Skipping {attendee.username}: already submitted feedback.")
                continue

            if not attendee.email:
                print(f"----> Skipping {attendee.username}: no email address.")
                continue

            # Only send if the user attended (for in-person) or if it was an online/hybrid event.
            is_online_event = (event.event_mode == 'Online' or event.event_mode == 'Hybrid')
            if not (reg.attended or is_online_event):
                print(f"----> Skipping {attendee.username}: did not attend in-person event.")
                continue

            print(f"----> Sending feedback request to: {attendee.username} ({attendee.email})")

            mail_subject = f'How was {event.title}? We\'d love your feedback!'
            
            # Build absolute URL using the Sites framework
            current_site = Site.objects.get_current()
            feedback_path = reverse('leave_feedback', args=[event.id])
            feedback_url = f"http://{current_site.domain}{feedback_path}"

            email_context = {
                'user': attendee,
                'event': event,
                'feedback_url': feedback_url,
            }

            html_content = render_to_string('events/emails/feedback_request.html', email_context)
            text_content = render_to_string('events/emails/feedback_request.txt', email_context)

            email = EmailMultiAlternatives(
                mail_subject,
                text_content,
                settings.EMAIL_HOST_USER,
                [attendee.email]
            )
            email.attach_alternative(html_content, "text/html")

            try:
                email.send(fail_silently=False)
                reg.feedback_request_sent_at = timezone.now()
                reg.save(update_fields=['feedback_request_sent_at'])
            except Exception as e:
                print(f"----> ERROR sending email to {attendee.email}: {e}")

    print(f"--- Scheduled Task Finished: Completed {len(events_to_complete)} event(s). ---")

