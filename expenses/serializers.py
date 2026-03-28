from rest_framework import serializers
from django.utils import timezone
from .models import Expense, Category, Budget, RecurringExpense

class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model"""
    class Meta:
        model = Category
        fields = ['id', 'name', 'icon', 'is_default']

class ExpenseSerializer(serializers.ModelSerializer):
    """Serializer for Expense model"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    
    class Meta:
        model = Expense
        fields = ['id', 'amount', 'description', 'date', 'category', 'category_name', 
                  'category_icon', 'payment_method', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value

class ExpenseCreateSerializer(serializers.ModelSerializer):
    """Simpler serializer for creating expenses"""
    class Meta:
        model = Expense
        fields = ['amount', 'description', 'date', 'category', 'payment_method', 'notes']

class BudgetSerializer(serializers.ModelSerializer):
    """Serializer for Budget model"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    spent_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    percentage_used = serializers.SerializerMethodField()
    
    class Meta:
        model = Budget
        fields = ['id', 'category', 'category_name', 'amount', 'period', 
                  'start_date', 'end_date', 'is_active', 'spent_amount', 
                  'remaining_amount', 'percentage_used', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_spent_amount(self, obj):
        return float(obj.get_spent_amount())
    
    def get_remaining_amount(self, obj):
        return float(obj.get_remaining_amount())
    
    def get_percentage_used(self, obj):
        return obj.get_percentage_used()
    
    def validate_amount(self, value):
        from decimal import Decimal
        if value <= Decimal('0'):
            raise serializers.ValidationError("Amount must be greater than 0")
        return value
    
    def validate(self, data):
        from django.utils import timezone
        
        # Check if a budget already exists for this combination
        existing_budget = Budget.objects.filter(
            user=self.context['request'].user,
            category=data.get('category'),
            period=data.get('period'),
            start_date=data.get('start_date')
        ).exists()
        
        if existing_budget and not self.instance:
            raise serializers.ValidationError({
                'non_field_errors': f"A budget already exists for this category with the same period and start date."
            })
        
        # Ensure start_date is not in the past for new budgets
        if not self.instance and data.get('start_date') and data['start_date'] < timezone.now().date():
            raise serializers.ValidationError({
                'start_date': "Start date cannot be in the past"
            })
        
        return data

class RecurringExpenseSerializer(serializers.ModelSerializer):
    """Serializer for RecurringExpense model"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    next_occurrence = serializers.SerializerMethodField()
    
    class Meta:
        model = RecurringExpense
        fields = ['id', 'category', 'category_name', 'amount', 'description', 
                  'frequency', 'start_date', 'end_date', 'payment_method', 
                  'is_active', 'next_occurrence', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_next_occurrence(self, obj):
        next_date = obj.get_next_occurrence()
        return next_date.strftime('%Y-%m-%d') if next_date else None
    

