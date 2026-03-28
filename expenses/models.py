from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from datetime import timedelta
import math


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=10, blank=True, help_text='Emoji for category')
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = 'Category'

class Expense(models.Model):
    PAYMENT_CHOICES = [
        ('CASH','Cash'),
        ('CARD','Card'),
        ('UPI','UPI'),
        ('BANK','Bank Transfer'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    description = models.TextField()
    date = models.DateField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='CASH')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.date} - {self.description[:30]} - ${self.amount}'

    class Meta:
        ordering = ['-date']   

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import timedelta  # Add this for timedelta

# ... (your existing Category and Expense models)

class Budget(models.Model):
    """Budget model for spending limits"""
    PERIOD_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
        ('WEEKLY', 'Weekly'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets')
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='MONTHLY')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'category', 'period', 'start_date']
    
    def __str__(self):
        return f"{self.user.username} - {self.category.name} - {self.amount} ({self.period})"
    
    def get_spent_amount(self, current_date=None):
        """Calculate how much has been spent in this budget period"""
        from django.utils import timezone
        from datetime import datetime
        from django.db.models import Sum
        
        if not current_date:
            current_date = timezone.now().date()
        
        # Determine date range based on period
        if self.period == 'MONTHLY':
            start = datetime(current_date.year, current_date.month, 1).date()
            if current_date.month == 12:
                end = datetime(current_date.year + 1, 1, 1).date()
            else:
                end = datetime(current_date.year, current_date.month + 1, 1).date()
        elif self.period == 'WEEKLY':
            start = current_date - timedelta(days=current_date.weekday())
            end = start + timedelta(days=7)
        else:  # YEARLY
            start = datetime(current_date.year, 1, 1).date()
            end = datetime(current_date.year + 1, 1, 1).date()
        
        # Calculate total spent in this category for the period
        total_spent = Expense.objects.filter(
            user=self.user,
            category=self.category,
            date__gte=start,
            date__lt=end
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        return total_spent
    
    def get_remaining_amount(self, current_date=None):
        """Calculate remaining budget amount"""
        spent = self.get_spent_amount(current_date)
        return max(Decimal('0'), self.amount - spent)
    
    def get_percentage_used(self, current_date=None):
        """Calculate percentage of budget used"""
        spent = self.get_spent_amount(current_date)
        if self.amount > 0:
            return float((spent / self.amount) * 100)
        return 0.0


class RecurringExpense(models.Model):
    """Recurring expenses model"""
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('BIWEEKLY', 'Bi-weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_expenses')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='recurring_expenses')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    description = models.TextField()
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='MONTHLY')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=10, choices=Expense.PAYMENT_CHOICES, default='CARD')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.description} - {self.frequency} - ${self.amount}"
    
    def get_next_occurrence(self, from_date=None):
        """Calculate next occurrence date"""
        from dateutil.relativedelta import relativedelta
        from datetime import datetime
        
        if not from_date:
            from_date = datetime.now().date()
        
        if from_date < self.start_date:
            return self.start_date
        
        if self.end_date and from_date > self.end_date:
            return None
        
        if self.frequency == 'DAILY':
            next_date = from_date + timedelta(days=1)
        elif self.frequency == 'WEEKLY':
            next_date = from_date + timedelta(weeks=1)
        elif self.frequency == 'BIWEEKLY':
            next_date = from_date + timedelta(weeks=2)
        elif self.frequency == 'MONTHLY':
            next_date = from_date + relativedelta(months=1)
        elif self.frequency == 'QUARTERLY':
            next_date = from_date + relativedelta(months=3)
        else:  # YEARLY
            next_date = from_date + relativedelta(years=1)
        
        if self.end_date and next_date > self.end_date:
            return None
        
        return next_date
    
    def create_expense_instance(self, date):
        """Create an actual expense from this recurring expense"""
        return Expense(
            user=self.user,
            category=self.category,
            amount=self.amount,
            description=f"{self.description} (Recurring)",
            date=date,
            payment_method=self.payment_method,
            notes=f"Auto-generated from recurring expense #{self.id}"
        )




