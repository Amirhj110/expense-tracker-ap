from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Avg
from django.utils import timezone
from django.http import HttpResponse
from datetime import datetime, timedelta
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server
import matplotlib.pyplot as plt
import io
import base64

from .models import Expense, Category, Budget, RecurringExpense
from .serializers import (
    ExpenseSerializer, ExpenseCreateSerializer, CategorySerializer,
    BudgetSerializer, RecurringExpenseSerializer
)
from .ai_categorizer import ExpenseCategorizer
from .budget_utils import BudgetChecker
from .recurring_utils import RecurringExpenseManager


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for Category model"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class ExpenseViewSet(viewsets.ModelViewSet):
    """ViewSet for Expense model with custom actions"""
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Only show expenses of logged-in user"""
        return Expense.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Save expense with current user"""
        serializer.save(user=self.request.user)
    
    # Custom Action 1: AI Category Suggestion
    @action(detail=False, methods=['post'])
    def suggest_category(self, request):
        """Get AI category suggestions for a description"""
        description = request.data.get('description', '')
        
        if not description:
            return Response(
                {'error': 'Description is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        suggestions = ExpenseCategorizer.suggest_categories(description)
        return Response({'suggestions': suggestions})
    
    # Custom Action 2: Create Expense with AI
    @action(detail=False, methods=['post'])
    def create_with_ai(self, request):
        """Create expense with automatic AI category suggestion"""
        serializer = ExpenseCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            description = serializer.validated_data['description']
            
            # Let AI suggest category
            suggested_category = ExpenseCategorizer.categorize(description)
            
            # Use AI suggestion if no category provided
            if not serializer.validated_data.get('category'):
                serializer.validated_data['category'] = suggested_category
            
            # Save the expense
            expense = serializer.save(user=request.user)
            
            return Response({
                'expense': ExpenseSerializer(expense).data,
                'ai_used': True,
                'suggested_category': suggested_category.name
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Custom Action 3: Analytics Dashboard
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get spending analytics using pandas"""
        expenses = self.get_queryset()
        
        if not expenses.exists():
            return Response({
                'total_spent': 0,
                'average_expense': 0,
                'total_transactions': 0,
                'top_category': None,
                'spending_by_category': {},
                'monthly_trend': {}
            })
        
        # Convert to pandas DataFrame for analysis
        df = pd.DataFrame(list(expenses.values('amount', 'date', 'category__name')))
        
        # Calculate metrics
        total_spent = df['amount'].sum()
        average_expense = df['amount'].mean()
        total_transactions = len(df)
        
        # Spending by category
        category_spending = df.groupby('category__name')['amount'].sum().to_dict()
        top_category = max(category_spending, key=category_spending.get) if category_spending else None
        
        # Monthly trend (last 6 months)
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.strftime('%Y-%m')
        monthly_trend = df.groupby('month')['amount'].sum().tail(6).to_dict()
        
        return Response({
            'total_spent': round(total_spent, 2),
            'average_expense': round(average_expense, 2),
            'total_transactions': total_transactions,
            'top_category': top_category,
            'spending_by_category': {k: round(v, 2) for k, v in category_spending.items()},
            'monthly_trend': {k: round(v, 2) for k, v in monthly_trend.items()}
        })
    
    # Custom Action 4: Export as CSV
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """Export all expenses as CSV file"""
        import csv
        
        expenses = self.get_queryset()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="my_expenses.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Description', 'Amount', 'Category', 'Payment Method', 'Notes'])
        
        for expense in expenses:
            writer.writerow([
                expense.date,
                expense.description,
                expense.amount,
                expense.category.name if expense.category else 'Uncategorized',
                expense.get_payment_method_display(),
                expense.notes
            ])
        
        return response
    
    # Custom Action 5: Generate Charts
    @action(detail=False, methods=['get'])
    def charts(self, request):
        """Generate charts for expense visualization"""
        expenses = self.get_queryset()
        
        if not expenses.exists():
            return Response({'error': 'No expenses to visualize'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        # Convert to DataFrame
        df = pd.DataFrame(list(expenses.values('amount', 'date', 'category__name')))
        df['date'] = pd.to_datetime(df['date'])
        
        charts_data = {}
        
        # 1. Category Pie Chart
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Pie chart: Spending by category
        category_spending = df.groupby('category__name')['amount'].sum()
        if not category_spending.empty:
            ax1.pie(category_spending.values, labels=category_spending.index, autopct='%1.1f%%')
            ax1.set_title('Spending by Category')
        
        # Bar chart: Monthly trend
        df['month'] = df['date'].dt.strftime('%Y-%m')
        monthly_trend = df.groupby('month')['amount'].sum().tail(6)
        if not monthly_trend.empty:
            ax2.bar(monthly_trend.index, monthly_trend.values)
            ax2.set_title('Monthly Spending Trend')
            ax2.set_xlabel('Month')
            ax2.set_ylabel('Amount ($)')
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        # Convert plot to base64 string
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png')
        buf.seek(0)
        charts_data['charts'] = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close()
        
        # 2. Daily spending trend (last 30 days)
        last_30_days = datetime.now().date() - timedelta(days=30)
        daily_expenses = expenses.filter(date__gte=last_30_days)
        
        if daily_expenses.exists():
            daily_df = pd.DataFrame(list(daily_expenses.values('amount', 'date')))
            daily_df['date'] = pd.to_datetime(daily_df['date'])
            daily_spending = daily_df.groupby('date')['amount'].sum()
            
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(daily_spending.index, daily_spending.values, marker='o', linestyle='-')
            ax.set_title('Daily Spending - Last 30 Days')
            ax.set_xlabel('Date')
            ax.set_ylabel('Amount ($)')
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png')
            buf.seek(0)
            charts_data['daily_trend'] = base64.b64encode(buf.getvalue()).decode('utf-8')
            plt.close()
        
        return Response(charts_data)
    
    # Custom Action 6: Download Chart
    @action(detail=False, methods=['get'])
    def download_chart(self, request):
        """Download chart as image file"""
        chart_type = request.query_params.get('chart_type', 'pie')
        expenses = self.get_queryset()
        
        if not expenses.exists():
            return HttpResponse("No data available", status=404)
        
        df = pd.DataFrame(list(expenses.values('amount', 'category__name')))
        
        fig, ax = plt.subplots(figsize=(8, 6))
        
        if chart_type == 'pie':
            category_spending = df.groupby('category__name')['amount'].sum()
            if not category_spending.empty:
                ax.pie(category_spending.values, labels=category_spending.index, autopct='%1.1f%%')
                ax.set_title('Spending by Category')
            else:
                return HttpResponse("No category data available", status=404)
        elif chart_type == 'bar':
            category_spending = df.groupby('category__name')['amount'].sum()
            if not category_spending.empty:
                ax.bar(category_spending.index, category_spending.values)
                ax.set_title('Spending by Category')
                ax.set_xlabel('Category')
                ax.set_ylabel('Amount ($)')
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            else:
                return HttpResponse("No category data available", status=404)
        else:
            return HttpResponse("Invalid chart type. Use 'pie' or 'bar'", status=400)
        
        # Save to response
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        response = HttpResponse(buf.getvalue(), content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="expense_{chart_type}_chart.png"'
        plt.close()
        
        return response
    
    # Custom Action 7: Budget Status
    @action(detail=False, methods=['get'])
    def budget_status(self, request):
        """Get current budget status for all categories"""
        budgets = Budget.objects.filter(user=request.user, is_active=True)
        
        budget_status = []
        alerts = []
        
        for budget in budgets:
            spent = budget.get_spent_amount()
            remaining = budget.get_remaining_amount()
            percentage = budget.get_percentage_used()
            
            budget_status.append({
                'category': budget.category.name,
                'budget': float(budget.amount),
                'spent': float(spent),
                'remaining': float(remaining),
                'percentage_used': round(percentage, 2),
                'status': 'Good' if percentage < 80 else 'Warning' if percentage < 100 else 'Exceeded'
            })
            
            # Check for alerts
            budget_alerts = BudgetChecker.check_budget_thresholds(request.user, budget.category)
            alerts.extend(budget_alerts)
        
        return Response({
            'budget_status': budget_status,
            'alerts': alerts
        })


class BudgetViewSet(viewsets.ModelViewSet):
    """ViewSet for Budget model"""
    serializer_class = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)
    
    def get_serializer_context(self):
        """Pass request to serializer context"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Override create to handle duplicate budgets gracefully"""
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            # Check if it's a unique constraint error
            if 'UNIQUE constraint failed' in str(e):
                return Response(
                    {'error': 'A budget already exists for this category with the same period and start date. Please update the existing budget instead.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            raise e
    @action(detail=False, methods=['post'])
    def create_or_update(self, request):
        """Create a new budget or update existing one"""
        category_id = request.data.get('category')
        period = request.data.get('period', 'MONTHLY')
        start_date = request.data.get('start_date')
        amount = request.data.get('amount')
        
        # Check if budget exists
        existing_budget = Budget.objects.filter(
            user=request.user,
            category_id=category_id,
            period=period,
            start_date=start_date
        ).first()
        
        if existing_budget:
            # Update existing budget
            serializer = self.get_serializer(existing_budget, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'message': 'Budget updated successfully',
                    'budget': serializer.data
                })
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Create new budget
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=request.user)
                return Response({
                    'message': 'Budget created successfully',
                    'budget': serializer.data
                }, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RecurringExpenseViewSet(viewsets.ModelViewSet):
    """ViewSet for RecurringExpense model"""
    serializer_class = RecurringExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return RecurringExpense.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def process_due(self, request):
        """Manually process due recurring expenses"""
        created = RecurringExpenseManager.process_due_recurring_expenses()
        return Response({
            'processed': len(created),
            'message': f'Created {len(created)} expenses from recurring transactions'
        })
    

