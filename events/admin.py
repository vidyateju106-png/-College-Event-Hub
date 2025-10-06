from django.contrib import admin
from .models import Event, Registration, Profile


class EventAdmin(admin.ModelAdmin):
	list_display = ('title', 'start_time', 'end_time', 'status')

	def save_model(self, request, obj, form, change):
		# Validate before saving to show errors in admin
		obj.full_clean()
		super().save_model(request, obj, form, change)


admin.site.register(Event, EventAdmin)
admin.site.register(Registration)
admin.site.register(Profile)
