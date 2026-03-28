from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExpenseViewSet, CategoryViewSet, BudgetViewSet, RecurringExpenseViewSet

router = DefaultRouter()
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'budgets', BudgetViewSet, basename='budget')
router.register(r'recurring', RecurringExpenseViewSet, basename='recurring')

urlpatterns = [
    path('', include(router.urls)),
]