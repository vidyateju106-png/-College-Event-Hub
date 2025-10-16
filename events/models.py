from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    ROLE_CHOICES = (
        ('Organizer', 'Event Organizer'),
        ('Participant', 'Participant'),
    )
    role = models.CharField(max_length=15, choices=ROLE_CHOICES)

    def __str__(self):
        return f'{self.user.username} - {self.role}'

class Event(models.Model):
    MODE_CHOICES = (
        ('In-Person', 'In-Person Only'),
        ('Online', 'Online Only'),
        ('Hybrid', 'Hybrid (In-Person and Online)'),
    )
    STATUS_CHOICES = (
        ('Draft', 'Draft'),
        ('Pending Approval', 'Pending Approval'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Completed', 'Completed'),
    )
    FEE_CHOICES = (
        ('Free', 'Free Entry'),
        ('Paid', 'Paid Entry'),
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    event_mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='In-Person')
    location = models.CharField(max_length=255, blank=True, null=True, help_text="Assigned by HOD upon approval.")
    stream_url = models.URLField(blank=True, null=True)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    rejection_reason = models.TextField(blank=True, null=True)
    max_seats = models.PositiveIntegerField(null=True, blank=True, help_text="Leave blank for unlimited seats.")
    entry_fee = models.CharField(max_length=10, choices=FEE_CHOICES, default='Free')
    fee_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Enter the fee amount if this is a paid event.")
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Estimated budget for the event.")

    def __str__(self):
        return self.title

    @property
    def is_full(self):
        if not self.max_seats:
            return False
        return self.registration_set.count() >= self.max_seats

    def clean(self):
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError({'end_time': 'End time must be after the start time.'})
            if self.pk is None and self.start_time < timezone.now():
                raise ValidationError({'start_time': 'The start time must be in the future.'})
            one_year_from_now = timezone.now() + timedelta(days=365)
            if self.end_time > one_year_from_now:
                raise ValidationError({'end_time': 'The end date cannot be more than one year from now.'})
        if (self.event_mode == 'Online' or self.event_mode == 'Hybrid') and not self.stream_url:
            raise ValidationError({'stream_url': 'A stream URL is required for Online or Hybrid events.'})
        if self.entry_fee == 'Paid' and not self.fee_amount:
            raise ValidationError({'fee_amount': 'A fee amount is required for paid events.'})
        if self.entry_fee == 'Free' and self.fee_amount:
            self.fee_amount = None
        if self.status == 'Completed' and self.end_time and self.end_time > timezone.now():
            raise ValidationError('An event cannot be marked as "Completed" before its end time has passed.')
        if self.location and self.start_time and self.end_time:
            conflicting_events = Event.objects.filter(
                location=self.location,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
                status='Approved'
            ).exclude(pk=self.pk)
            if conflicting_events.exists():
                raise ValidationError({'location': 'This location is already booked for an overlapping time period.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Registration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    attendee = models.ForeignKey(User, on_delete=models.CASCADE)
    registered_at = models.DateTimeField(auto_now_add=True)
    qr_code_path = models.FileField(upload_to='qr_codes/', blank=True)
    attended = models.BooleanField(default=False)
    attended_at = models.DateTimeField(null=True, blank=True)
    feedback_request_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('event', 'attendee')

    def __str__(self):
        return f'{self.attendee.username} registered for {self.event.title}'

    def has_submitted_feedback(self):
        return Feedback.objects.filter(event=self.event, user=self.attendee).exists()

class Feedback(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='feedback')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user')

    def __str__(self):
        return f'Feedback for {self.event.title} by {self.user.username}'

