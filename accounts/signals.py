"""Account signals."""

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import AuthorProfile


@receiver(post_save, sender=User)
def create_author_profile(sender, instance, created, **kwargs):
    if created:
        AuthorProfile.objects.get_or_create(
            user=instance,
            defaults={"display_name": instance.username},
        )
