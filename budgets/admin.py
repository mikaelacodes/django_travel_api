from django.contrib import admin

from .models import Budget, Expense


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    # total_budget is a property, so show it read-only via the list
    list_display = ('itinerary', 'total_budget', 'updated_at')
    search_fields = ('itinerary__title',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('description', 'itinerary', 'category', 'amount', 'date')
    list_filter = ('category', 'date')
    search_fields = ('description', 'itinerary__title')
