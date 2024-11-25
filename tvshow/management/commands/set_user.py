from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tvshow.models import Show
import argparse

class Command(BaseCommand):
    help = 'Update Show objects with the specified user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the user to assign to Shows')

    def handle(self, *args, **options):
        username = options['username']
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"User '{username}' not found."))
            return
        for show in Show.objects.all():
            show.user = user
            show.save()
        self.stdout.write(self.style.SUCCESS(f"Successfully updated Show objects with user '{username}'"))