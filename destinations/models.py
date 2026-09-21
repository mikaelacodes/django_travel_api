from django.core.validators import MinValueValidator
from django.db import models


class Destination(models.Model):
    """
    A place someone can travel to. Everything else links back to it -
    itineraries, accommodations, activities, and reviews.
    """

    # keeping climate/category as TextChoices so the DB stays tidy and the
    # admin gives us nice dropdowns instead of free text
    class ClimateChoices(models.TextChoices):
        TROPICAL = 'tropical', 'Tropical'
        DRY = 'dry', 'Dry'
        TEMPERATE = 'temperate', 'Temperate'
        CONTINENTAL = 'continental', 'Continental'
        POLAR = 'polar', 'Polar'

    class CategoryChoices(models.TextChoices):
        BEACH = 'beach', 'Beach'
        MOUNTAIN = 'mountain', 'Mountain'
        CITY = 'city', 'City'
        CULTURAL = 'cultural', 'Cultural'
        ADVENTURE = 'adventure', 'Adventure'
        RELAXATION = 'relaxation', 'Relaxation'

    name = models.CharField(max_length=200, unique=True, help_text='Destination name (unique).')
    country = models.CharField(max_length=100, help_text='Country the destination is in.')
    description = models.TextField(help_text='Full description of the destination.')
    category = models.CharField(
        max_length=20,
        choices=CategoryChoices.choices,
        help_text='Primary category of the destination.',
    )
    climate = models.CharField(
        max_length=20,
        choices=ClimateChoices.choices,
        help_text='Predominant climate.',
    )
    best_time_to_visit = models.CharField(max_length=200, help_text='Recommended season/months to visit.')
    avg_daily_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text='Average cost per day in USD.',
    )
    image = models.ImageField(upload_to='destinations/', null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        # index the fields people actually filter/search on
        indexes = [
            models.Index(fields=['country', 'category']),
            models.Index(fields=['climate']),
        ]

    def __str__(self):
        return f"{self.name}, {self.country}"

    @property
    def average_rating(self):
        # roll up all the review scores; no reviews yet -> just call it 0
        ratings = self.reviews.aggregate(models.Avg('rating'))
        return ratings['rating__avg'] or 0
