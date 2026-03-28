from django.contrib import admin
from .models import Category, Expense, Budget, RecurringExpense

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'is_default']
    search_fields = ['name']

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['date', 'description', 'amount', 'category', 'payment_method', 'user']
    list_filter = ['date', 'category', 'payment_method', 'user']
    search_fields = ['description', 'notes']
    date_hierarchy = 'date'

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['user', 'category', 'amount', 'period', 'is_active', 'start_date']
    list_filter = ['period', 'is_active', 'category']
    search_fields = ['user__username', 'category__name']

@admin.register(RecurringExpense)
class RecurringExpenseAdmin(admin.ModelAdmin):
    list_display = ['description', 'amount', 'frequency', 'user', 'is_active', 'start_date']
    list_filter = ['frequency', 'is_active', 'category']
    search_fields = ['description', 'user__username']