from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from destinations.models import Destination
from itineraries.models import Itinerary


class Accommodation(models.Model):
    """Somewhere to stay at a destination - hotel, hostel, rental, whatever."""

    class TypeChoices(models.TextChoices):
        HOTEL = 'hotel', 'Hotel'
        HOSTEL = 'hostel', 'Hostel'
        RENTAL = 'rental', 'Vacation Rental'
        RESORT = 'resort', 'Resort'
        BNB = 'bnb', 'B&B'

    name = models.CharField(max_length=200, help_text='Name of the property.')
    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name='accommodations',
    )
    accommodation_type = models.CharField(
        max_length=10,
        choices=TypeChoices.choices,
        help_text='Type of lodging.',
    )
    description = models.TextField()
    price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text='Nightly price in USD.',
    )
    max_guests = models.PositiveIntegerField(help_text='Maximum number of guests.')
    # just a list of strings like ["wifi", "pool"] - flexible without a side table
    amenities = models.JSONField(default=list, blank=True, help_text='List of amenity strings.')
    address = models.CharField(max_length=300)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    image = models.ImageField(upload_to='accommodations/', null=True, blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['destination', 'accommodation_type']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_accommodation_type_display()})"


class Activity(models.Model):
    """Stuff to do at a destination - tours, attractions, dining, etc."""

    class CategoryChoices(models.TextChoices):
        TOUR = 'tour', 'Tour'
        ATTRACTION = 'attraction', 'Attraction'
        DINING = 'dining', 'Dining'
        SHOPPING = 'shopping', 'Shopping'
        ENTERTAINMENT = 'entertainment', 'Entertainment'
        OUTDOOR = 'outdoor', 'Outdoor'

    name = models.CharField(max_length=200)
    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name='activities',
    )
    category = models.CharField(
        max_length=20,
        choices=CategoryChoices.choices,
        help_text='Type of activity.',
    )
    description = models.TextField()
    duration_hours = models.DecimalField(max_digits=4, decimal_places=1, help_text='Duration in hours.')
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text='Price per participant in USD.',
    )
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    requirements = models.TextField(blank=True)
    image = models.ImageField(upload_to='activities/', null=True, blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Activities'
        indexes = [
            models.Index(fields=['destination', 'category']),
        ]

    def __str__(self):
        return f"{self.name} - {self.destination.name}"


class Booking(models.Model):
    """
    A reservation on someone's trip. It's either for an accommodation OR an
    activity - exactly one of the two (see clean() below).
    """

    class StatusChoices(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'
        COMPLETED = 'completed', 'Completed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    itinerary = models.ForeignKey(
        Itinerary,
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    # SET_NULL: if the hotel/activity listing is removed we keep the booking record
    accommodation = models.ForeignKey(
        Accommodation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings',
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings',
    )
    booking_date = models.DateField(help_text='Date the booking is made for.')
    check_in = models.DateField(null=True, blank=True, help_text='Check-in date (accommodations).')
    check_out = models.DateField(null=True, blank=True, help_text='Check-out date (accommodations).')
    guests_count = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )
    confirmation_code = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['itinerary']),
        ]

    def __str__(self):
        if self.accommodation:
            return f"Booking: {self.accommodation.name}"
        elif self.activity:
            return f"Booking: {self.activity.name}"
        return f"Booking #{self.id}"

    def clean(self):
        # a booking has to be for one thing - not zero, not both
        if not self.accommodation and not self.activity:
            raise ValidationError('Booking must have either accommodation or activity')
        if self.accommodation and self.activity:
            raise ValidationError('Booking cannot have both accommodation and activity')
