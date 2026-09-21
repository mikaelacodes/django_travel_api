from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from bookings.models import Accommodation, Activity
from destinations.models import Destination


class Review(models.Model):
    """
    A star rating + write-up from a user. It's about exactly one thing: a
    destination, an accommodation, or an activity (enforced in clean()).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    # all three targets are nullable - only one of them gets filled in per review
    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name='reviews',
        null=True,
        blank=True,
    )
    accommodation = models.ForeignKey(
        Accommodation,
        on_delete=models.CASCADE,
        related_name='reviews',
        null=True,
        blank=True,
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='reviews',
        null=True,
        blank=True,
    )
    # validators keep it to a sane 1-5 stars
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Star rating from 1 to 5.',
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    visit_date = models.DateField(help_text='When the user visited.')
    images = models.JSONField(default=list, blank=True, help_text='List of image URLs.')
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['destination', 'rating']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.title} by {self.user.username}"

    def clean(self):
        # count how many targets are set - it has to be exactly one
        review_targets = [self.destination, self.accommodation, self.activity]
        if sum(1 for target in review_targets if target) != 1:
            raise ValidationError('Review must be for exactly one item')
