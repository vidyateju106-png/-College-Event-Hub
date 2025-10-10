from django import forms
from django.contrib.auth.forms import UserCreationForm
# Correctly import the User model from Django's auth system
from django.contrib.auth.models import User 
# Import your other models
from .models import Event, Feedback
from django.utils import timezone
from datetime import timedelta
import re

class CustomUserCreationForm(UserCreationForm):
    # This is the new, required email field
    email = forms.EmailField(required=True, help_text='Required. Please provide a valid email address.')
    
    ROLE_CHOICES = (
        ('Organizer', 'Event Organizer'),
        ('Participant', 'Participant'),
    )
    role = forms.ChoiceField(choices=ROLE_CHOICES, required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        # Ensure 'email' is included in the fields to be saved
        fields = UserCreationForm.Meta.fields + ('email',)

    def clean_username(self):
        """
        MODIFIED: Validates that the username contains only letters, numbers,
        and underscores to make it more user-friendly.
        """
        username = self.cleaned_data.get('username')
        # This regex allows letters, numbers, and underscores.
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise forms.ValidationError("Username can only contain letters, numbers, and underscores.")
        return username

    def save(self, commit=True):
        """
        Override save to ensure the email and role are saved and a Profile
        instance is created with the chosen role.
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data.get('email')
        if commit:
            user.save()
            # Create or update the Profile
            from .models import Profile
            profile, created = Profile.objects.get_or_create(user=user)
            profile.role = self.cleaned_data.get('role')
            profile.save()
        return user


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'start_time', 'end_time', 'event_mode', 'stream_url', 'max_seats']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'event_mode': forms.Select(attrs={'class': 'form-select'}),
            'stream_url': forms.URLInput(attrs={'class': 'form-control'}),
            'max_seats': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 100'}),
        }


    def clean_description(self):
        description = self.cleaned_data.get('description')
        if len(description) < 20:
            raise forms.ValidationError("The description must be at least 20 characters long.")
        return description

    def clean_start_time(self):
        start_time = self.cleaned_data.get('start_time')
        if start_time and start_time < timezone.now():
            raise forms.ValidationError("The start time must be in the future.")
        return start_time

    def clean_max_seats(self):
        max_seats = self.cleaned_data.get('max_seats')
        if max_seats is not None and max_seats <= 0:
            raise forms.ValidationError("The number of seats must be a positive number.")
        return max_seats

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        event_mode = cleaned_data.get('event_mode')
        stream_url = cleaned_data.get('stream_url')

        if start_time and end_time:
            if end_time <= start_time:
                self.add_error('end_time', "The end time must be after the start time.")
            
            one_year_from_now = timezone.now() + timedelta(days=365)
            if end_time > one_year_from_now:
                self.add_error('end_time', "The end date cannot be more than one year from now.")

        if (event_mode == 'Online' or event_mode == 'Hybrid') and not stream_url:
            self.add_error('stream_url', "A stream URL is required for Online or Hybrid events.")
            
        return cleaned_data

class RejectionForm(forms.Form):
    """A simple form for capturing the rejection reason."""
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        label="Reason for Rejection",
        required=True,
        help_text="Please provide a clear reason for rejecting this event. The organizer will see this message."
    )

class FeedbackForm(forms.ModelForm):
    # We create choices from 1 to 5 for the star rating
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]
    
    # The rating field is a ChoiceField that will be styled as stars in the HTML
    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect, # This allows us to style each choice (star) individually
        label="Your Overall Rating"
    )

    class Meta:
        model = Feedback
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell us more about your experience (optional)...'}),
        }
