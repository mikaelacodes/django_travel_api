from rest_framework import serializers

from .models import Budget, Expense


class ExpenseSerializer(serializers.ModelSerializer):
    """One logged expense on a trip."""

    class Meta:
        model = Expense
        fields = '__all__'
        read_only_fields = ['id', 'created_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount has to be more than zero')
        return value


class BudgetSerializer(serializers.ModelSerializer):
    """
    The per-category budget for a trip. total_budget comes from the model
    property, and we pull in the trip's expenses so you can compare plan vs spend.
    """

    total_budget = serializers.ReadOnlyField()
    expenses = ExpenseSerializer(source='itinerary.expenses', many=True, read_only=True)

    class Meta:
        model = Budget
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
