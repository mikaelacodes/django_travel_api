from django.core.validators import MinValueValidator
from django.db import models

from itineraries.models import Itinerary
from travel_api.validators import validate_image_size, validate_image_type


class Budget(models.Model):
    """
    The planned spend for a trip, broken out by category. One-to-one with an
    itinerary - each trip gets exactly one of these (we auto-create it later
    when the itinerary is made).
    """

    itinerary = models.OneToOneField(
        Itinerary,
        on_delete=models.CASCADE,
        related_name='budget_detail',
    )
    accommodation_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    activities_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    food_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transport_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shopping_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    miscellaneous_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Budget for {self.itinerary.title}"

    @property
    def total_budget(self):
        # add up every category so callers don't have to
        return (
            self.accommodation_budget
            + self.activities_budget
            + self.food_budget
            + self.transport_budget
            + self.shopping_budget
            + self.miscellaneous_budget
        )


class Expense(models.Model):
    """A single thing someone actually spent money on during a trip."""

    class CategoryChoices(models.TextChoices):
        ACCOMMODATION = 'accommodation', 'Accommodation'
        ACTIVITIES = 'activities', 'Activities'
        FOOD = 'food', 'Food'
        TRANSPORT = 'transport', 'Transport'
        SHOPPING = 'shopping', 'Shopping'
        MISCELLANEOUS = 'miscellaneous', 'Miscellaneous'

    itinerary = models.ForeignKey(
        Itinerary,
        on_delete=models.CASCADE,
        related_name='expenses',
    )
    category = models.CharField(
        max_length=20,
        choices=CategoryChoices.choices,
        help_text='Expense category.',
    )
    description = models.CharField(max_length=200)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    date = models.DateField()
    receipt = models.ImageField(
        upload_to='receipts/',
        null=True,
        blank=True,
        validators=[validate_image_size, validate_image_type],
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['itinerary', 'category']),
        ]

    def __str__(self):
        return f"{self.description} - ${self.amount}"
