from django.contrib import admin

from .models import Accommodation, Activity, Booking


@admin.register(Accommodation)
class AccommodationAdmin(admin.ModelAdmin):
    list_display = ('name', 'destination', 'accommodation_type', 'price_per_night', 'is_available')
    list_filter = ('accommodation_type', 'is_available', 'destination')
    search_fields = ('name', 'address', 'destination__name')


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('name', 'destination', 'category', 'price', 'duration_hours', 'is_available')
    list_filter = ('category', 'is_available', 'destination')
    search_fields = ('name', 'description', 'destination__name')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    # __str__ handles the "which thing is this for" label for us
    list_display = ('__str__', 'user', 'itinerary', 'status', 'price', 'booking_date')
    list_filter = ('status', 'booking_date')
    search_fields = ('user__username', 'itinerary__title', 'confirmation_code')
