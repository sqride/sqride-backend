from django.core.management.base import BaseCommand
from django.db import transaction
from restaurants.models import Branch
from kitchen.models import KitchenStation, KitchenDisplay
from kitchen.services import KitchenSystemService


class Command(BaseCommand):
    help = 'Setup kitchen system for a branch'

    def add_arguments(self, parser):
        parser.add_argument(
            '--branch-id',
            type=int,
            help='Branch ID to setup kitchen for'
        )
        parser.add_argument(
            '--branch-name',
            type=str,
            help='Branch name to setup kitchen for'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Setup kitchen for all branches'
        )

    def handle(self, *args, **options):
        if options['all']:
            branches = Branch.objects.all()
        elif options['branch_id']:
            try:
                branches = [Branch.objects.get(id=options['branch_id'])]
            except Branch.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Branch with ID {options["branch_id"]} not found')
                )
                return
        elif options['branch_name']:
            try:
                branches = [Branch.objects.get(name=options['branch_name'])]
            except Branch.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Branch with name "{options["branch_name"]}" not found')
                )
                return
        else:
            self.stdout.write(
                self.style.ERROR('Please specify --branch-id, --branch-name, or --all')
            )
            return

        for branch in branches:
            self.stdout.write(f'Setting up kitchen for branch: {branch.name}')
            
            if branch.kitchen_enabled:
                self.stdout.write(
                    self.style.WARNING(f'Kitchen already enabled for {branch.name}')
                )
                continue

            success, message = KitchenSystemService.enable_kitchen_system(branch.id)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'Kitchen setup successful for {branch.name}: {message}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Kitchen setup failed for {branch.name}: {message}')
                )

        self.stdout.write(
            self.style.SUCCESS('Kitchen setup process completed')
        )
