from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import ActivityLog, Itinerary


@receiver(post_save, sender=Itinerary)
def log_itinerary_saved(sender, instance, created, **kwargs):
    # record whether a trip was just created or edited
    if not instance.owner_id:
        return
    ActivityLog.objects.create(
        user_id=instance.owner_id,
        itinerary=instance,
        action=ActivityLog.ActionChoices.CREATED if created else ActivityLog.ActionChoices.UPDATED,
        object_type='Itinerary',
        object_id=instance.pk,
    )


@receiver(post_delete, sender=Itinerary)
def log_itinerary_deleted(sender, instance, **kwargs):
    # the trip is gone now, so leave the itinerary link null
    if not instance.owner_id:
        return
    ActivityLog.objects.create(
        user_id=instance.owner_id,
        itinerary=None,
        action=ActivityLog.ActionChoices.DELETED,
        object_type='Itinerary',
        object_id=instance.pk,
    )
