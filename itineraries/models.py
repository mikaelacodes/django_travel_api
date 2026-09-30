from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from destinations.models import Destination


class Itinerary(models.Model):
    """
    One person's plan for one trip. Has a single owner, but can be shared with
    other people (collaborators) through the Collaboration model below.
    """

    class StatusChoices(models.TextChoices):
        PLANNING = 'planning', 'Planning'
        BOOKED = 'booked', 'Booked'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    title = models.CharField(max_length=200, help_text='Trip title.')
    description = models.TextField(blank=True, help_text='Optional trip description.')
    # PROTECT so we can't delete a destination that trips still depend on
    destination = models.ForeignKey(
        Destination,
        on_delete=models.PROTECT,
        related_name='itineraries',
        help_text='Primary destination for this trip.',
    )
    # if the owner's account goes, their trips go with it
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_itineraries',
        help_text='User who owns/created this itinerary.',
    )
    # through model lets us store a per-person role, not just "is a collaborator"
    collaborators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='Collaboration',
        related_name='shared_itineraries',
        blank=True,
        help_text='Users this itinerary is shared with.',
    )
    start_date = models.DateField(help_text='Trip start date.')
    end_date = models.DateField(help_text='Trip end date.')
    budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text='Planned total budget in USD.',
    )
    actual_spent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Amount actually spent so far.',
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PLANNING,
        help_text='Current trip status.',
    )
    is_public = models.BooleanField(default=False, help_text='Whether the itinerary is publicly visible.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name_plural = 'Itineraries'
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.title} - {self.destination.name}"

    def clean(self):
        # a trip that ends before it starts makes no sense
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError('End date must be after start date')

    @property
    def duration_days(self):
        # +1 because both the first and last day count
        return (self.end_date - self.start_date).days + 1

    @property
    def budget_remaining(self):
        return self.budget - self.actual_spent

    def add_collaborator(self, user, role='viewer'):
        # little helper so views don't have to touch Collaboration directly
        return Collaboration.objects.create(itinerary=self, user=user, role=role)


class Collaboration(models.Model):
    """
    The link between an itinerary and someone it's shared with. Lives as its own
    model so each share can carry a role (viewer / editor / admin).
    """

    class RoleChoices(models.TextChoices):
        VIEWER = 'viewer', 'Viewer'
        EDITOR = 'editor', 'Editor'
        ADMIN = 'admin', 'Admin'

    itinerary = models.ForeignKey(
        Itinerary,
        on_delete=models.CASCADE,
        related_name='collaborations',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='collaborations',
    )
    role = models.CharField(
        max_length=10,
        choices=RoleChoices.choices,
        default=RoleChoices.VIEWER,
        help_text='Access level of the collaborator.',
    )
    invited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # can't invite the same person to the same trip twice
        unique_together = ['itinerary', 'user']

    def __str__(self):
        return f"{self.user.username} - {self.itinerary.title} ({self.role})"


class DailyPlan(models.Model):
    """One day inside a trip - what's happening and which activities are on it."""

    itinerary = models.ForeignKey(
        Itinerary,
        on_delete=models.CASCADE,
        related_name='daily_plans',
    )
    day_number = models.PositiveIntegerField(help_text='1-based day index within the trip.')
    date = models.DateField(help_text='Calendar date for this day.')
    title = models.CharField(max_length=200, help_text='Short title for the day.')
    notes = models.TextField(blank=True, help_text='Free-form notes for the day.')
    # string reference to dodge a circular import with the bookings app
    activities = models.ManyToManyField(
        'bookings.Activity',
        related_name='daily_plans',
        blank=True,
        help_text='Activities planned for this day.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['day_number']
        # one "Day 3" per trip, not two
        unique_together = ['itinerary', 'day_number']

    def __str__(self):
        return f"Day {self.day_number}: {self.title}"


class ActivityLog(models.Model):
    """
    A simple audit trail - who did what, and when. object_type / object_id let
    us point at any record without needing a hard FK to every single model.
    Rows are written automatically by signals (see signals.py).
    """

    class ActionChoices(models.TextChoices):
        CREATED = 'created', 'Created'
        UPDATED = 'updated', 'Updated'
        DELETED = 'deleted', 'Deleted'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activity_logs',
    )
    # nullable: if the trip gets deleted we still want to keep the log entry
    itinerary = models.ForeignKey(
        Itinerary,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
    )
    action = models.CharField(max_length=20, choices=ActionChoices.choices, help_text='What happened.')
    object_type = models.CharField(max_length=50, help_text='Which model, e.g. "Itinerary".')
    object_id = models.PositiveIntegerField(null=True, blank=True, help_text='PK of the affected row.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Activity logs'
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user} {self.action} {self.object_type}#{self.object_id}"
