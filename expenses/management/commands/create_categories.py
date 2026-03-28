from django.core.management.base import BaseCommand
from expenses.models import Category

class Command(BaseCommand):
    help = 'Create default expense categories'
    
    def handle(self, *args, **options):
        categories = [
            ('Food & Dining', '🍔', True),
            ('Transportation', '🚗', True),
            ('Shopping', '🛍️', True),
            ('Entertainment', '🎬', True),
            ('Bills & Utilities', '💡', True),
            ('Healthcare', '🏥', True),
            ('Education', '📚', True),
            ('Travel', '✈️', True),
            ('Other', '📦', True),
        ]
        
        for name, icon, is_default in categories:
            category, created = Category.objects.get_or_create(
                name=name,
                defaults={'icon': icon, 'is_default': is_default}
            )
            if created:
                self.stdout.write(f'Created category: {name}')
            else:
                self.stdout.write(f'Category already exists: {name}')
        
        self.stdout.write(self.style.SUCCESS('Successfully created all default categories!'))




        