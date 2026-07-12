"""Create UserAccount when a User is created."""

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import AuthorProfile, UserAccount
from accounts.roles import sync_django_staff_flags


@receiver(post_save, sender=User)
def create_user_profiles(sender, instance, created, **kwargs):
    if created:
        UserAccount.objects.get_or_create(user=instance)
        AuthorProfile.objects.get_or_create(
            user=instance,
            defaults={"display_name": instance.username},
        )
    else:
        sync_django_staff_flags(instance)
