from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .cache_utils import invalidate_movie_sessions_cache, invalidate_seat_map_cache
from .models import Session, Ticket


@receiver(pre_save, sender=Session)
def session_store_previous_movie(sender, instance, **kwargs):
    instance._previous_movie_id = None

    if not instance.pk:
        return

    try:
        previous = sender.objects.only("movie_id").get(pk=instance.pk)
        instance._previous_movie_id = previous.movie_id
    except sender.DoesNotExist:
        instance._previous_movie_id = None


@receiver(post_save, sender=Session)
def session_invalidate_cache_on_save(sender, instance, **kwargs):
    invalidate_movie_sessions_cache(instance.movie_id)

    previous_movie_id = getattr(instance, "_previous_movie_id", None)
    if previous_movie_id and previous_movie_id != instance.movie_id:
        invalidate_movie_sessions_cache(previous_movie_id)


@receiver(post_delete, sender=Session)
def session_invalidate_cache_on_delete(sender, instance, **kwargs):
    invalidate_movie_sessions_cache(instance.movie_id)


@receiver(post_save, sender=Ticket)
def ticket_invalidate_seatmap(sender, instance, **kwargs):
    invalidate_seat_map_cache(instance.session_id)


@receiver(post_delete, sender=Ticket)
def ticket_invalidate_seatmap_on_delete(sender, instance, **kwargs):
    invalidate_seat_map_cache(instance.session_id)
