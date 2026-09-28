from django_filters import rest_framework as filters

from .models import Booking


class BookingFilter(filters.FilterSet):
    """Filters for a user's bookings - price range, date range, status, and trip."""

    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    booking_date_after = filters.DateFilter(field_name='booking_date', lookup_expr='gte')
    booking_date_before = filters.DateFilter(field_name='booking_date', lookup_expr='lte')

    class Meta:
        model = Booking
        fields = ['status', 'itinerary']
