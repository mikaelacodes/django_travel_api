from django.contrib.auth.models import AbstractUser
from django.db import models

from travel_api.validators import validate_image_size, validate_image_type


class User(AbstractUser):
    """
    Our own user model so we can hang travel stuff off it later.
    Email has to be unique since we let people log in with it.
    """

    email = models.EmailField(unique=True, help_text='Unique email address used for the account.')
    phone = models.CharField(max_length=20, blank=True, help_text='Optional contact phone number.')
    date_of_birth = models.DateField(null=True, blank=True, help_text='Optional date of birth.')
    bio = models.TextField(max_length=500, blank=True, help_text='Short biography (max 500 chars).')
    profile_picture = models.ImageField(
        upload_to='profiles/',
        null=True,
        blank=True,
        validators=[validate_image_size, validate_image_type],
        help_text='Optional profile picture.',
    )
    # keeping a JSON blob here so preferences can grow without new migrations
    travel_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text='Free-form JSON of user travel preferences (climate, budget, etc.).',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username

    @property
    def full_name(self):
        # fall back to username if they never filled in their name
        return f"{self.first_name} {self.last_name}".strip() or self.username
