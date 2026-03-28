from django.utils import timezone
from datetime import datetime, timedelta
from .models import RecurringExpense, Expense

class RecurringExpenseManager:
    """Manage recurring expenses"""
    
    @classmethod
    def process_due_recurring_expenses(cls):
        """Process all recurring expenses that are due"""
        today = timezone.now().date()
        
        # Get active recurring expenses
        recurring_expenses = RecurringExpense.objects.filter(
            is_active=True,
            start_date__lte=today
        ).exclude(
            end_date__lt=today
        )
        
        created_expenses = []
        
        for recurring in recurring_expenses:
            # Check if already processed for today
            existing = Expense.objects.filter(
                user=recurring.user,
                description__icontains=recurring.description,
                date=today,
                notes__icontains=f"#{recurring.id}"
            ).exists()
            
            if not existing:
                # Determine if this should be created today
                days_since_start = (today - recurring.start_date).days
                
                should_create = False
                
                if recurring.frequency == 'DAILY':
                    should_create = days_since_start >= 0
                elif recurring.frequency == 'WEEKLY':
                    should_create = days_since_start % 7 == 0
                elif recurring.frequency == 'BIWEEKLY':
                    should_create = days_since_start % 14 == 0
                elif recurring.frequency == 'MONTHLY':
                    # Check if same day of month
                    should_create = today.day == recurring.start_date.day
                elif recurring.frequency == 'QUARTERLY':
                    # Check if 3 months apart
                    months_diff = (today.year - recurring.start_date.year) * 12 + (today.month - recurring.start_date.month)
                    should_create = months_diff % 3 == 0 and today.day == recurring.start_date.day
                else:  # YEARLY
                    should_create = today.month == recurring.start_date.month and today.day == recurring.start_date.day
                
                if should_create:
                    expense = recurring.create_expense_instance(today)
                    expense.save()
                    created_expenses.append(expense)
        
        return created_expenses