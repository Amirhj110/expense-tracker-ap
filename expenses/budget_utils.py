from django.core.mail import send_mail
from django.conf import settings
from .models import Budget

class BudgetChecker:
    """Check budgets and send alerts"""
    
    @classmethod
    def check_budget_thresholds(cls, user, category, current_date=None):
        """Check if any budget thresholds are exceeded"""
        from datetime import datetime
        
        budgets = Budget.objects.filter(
            user=user,
            category=category,
            is_active=True
        )
        
        alerts = []
        for budget in budgets:
            percentage = budget.get_percentage_used(current_date)
            
            # Alert at 80% and 100%
            if percentage >= 100:
                alerts.append({
                    'type': 'EXCEEDED',
                    'budget': budget,
                    'message': f"You have exceeded your {budget.category.name} budget of ${budget.amount} by ${budget.get_spent_amount() - budget.amount:.2f}!"
                })
            elif percentage >= 80:
                alerts.append({
                    'type': 'WARNING',
                    'budget': budget,
                    'message': f"You have used {percentage:.1f}% of your {budget.category.name} budget. ${budget.get_remaining_amount():.2f} remaining."
                })
        
        return alerts
    
    @classmethod
    def send_budget_alerts(cls, user):
        """Send email alerts for budget warnings"""
        from django.contrib.auth.models import User
        
        budgets = Budget.objects.filter(user=user, is_active=True)
        alerts = []
        
        for budget in budgets:
            percentage = budget.get_percentage_used()
            if percentage >= 80:
                alerts.append(f"- {budget.category.name}: {percentage:.1f}% used (${budget.get_remaining_amount():.2f} remaining)")
        
        if alerts and user.email:
            subject = "Budget Alert: You're approaching your spending limits!"
            message = f"Hello {user.username},\n\nHere are your budget updates:\n" + "\n".join(alerts)
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])



            