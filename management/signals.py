from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User

from management.models import UserProfile, Project
from api.utils import run_command_as_user, sys_delete_user, get_user_home



@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.create_for_user(instance)


@receiver(pre_delete, sender=Project)
def execute_custom_code_before_project_delete(sender, instance: Project, **kwargs):
    instance.before_delete_cleanup()


@receiver(post_delete, sender=UserProfile)
def execute_custom_code_after_user_delete(sender, instance: UserProfile, **kwargs):
    system_user = f"{instance.user.username}-{str(instance.id).split('-')[0]}"
    sys_delete_user(system_user)
