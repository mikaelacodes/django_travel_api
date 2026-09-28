from django.db.models import Avg, Count, F, Q, Sum
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend

from itineraries.models import Itinerary

from .models import Budget, Expense
from .serializers import BudgetSerializer, ExpenseSerializer


class ExpenseViewSet(viewsets.ModelViewSet):
    """CRUD for expenses. You only ever see expenses on your own trips."""

    serializer_class = ExpenseSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'itinerary']
    search_fields = ['description']
    ordering_fields = ['date', 'amount']

    def get_queryset(self):
        # scope to expenses that belong to trips this user owns
        return Expense.objects.filter(itinerary__owner=self.request.user).select_related('itinerary')


class BudgetViewSet(viewsets.ReadOnlyModelViewSet):
    """Read a trip's budget breakdown. Budgets get created with the trip."""

    serializer_class = BudgetSerializer

    def get_queryset(self):
        return Budget.objects.filter(itinerary__owner=self.request.user).select_related('itinerary')


class TripAnalyticsViewSet(viewsets.ViewSet):
    """
    Numbers across all of a user's trips - totals, spending by category, and a
    look at which kinds of destinations they book most. This one's a plain
    ViewSet since it isn't backed by a single model.
    """

    permission_classes = [permissions.IsAuthenticated]

    def _user_trips(self, request):
        return Itinerary.objects.filter(owner=request.user)

    def list(self, request):
        """Overall stats: how many trips, total budget, average, and days planned."""
        trips = self._user_trips(request)
        stats = trips.aggregate(
            trip_count=Count('id'),
            total_budget=Sum('budget'),
            total_spent=Sum('actual_spent'),
            average_budget=Avg('budget'),
        )
        # how many trips are running over what was planned (F compares two columns)
        stats['over_budget_trips'] = trips.filter(actual_spent__gt=F('budget')).count()
        return Response(stats)

    @action(detail=False, methods=['get'])
    def budget_summary(self, request):
        """Planned vs actual per trip, with the gap worked out in the query."""
        trips = (
            self._user_trips(request)
            # budget_variance = what's left (or overspent) per trip
            .annotate(budget_variance=F('budget') - F('actual_spent'))
            .values('id', 'title', 'budget', 'actual_spent', 'budget_variance')
        )
        # spend logged by category, across every trip
        by_category = (
            Expense.objects.filter(itinerary__owner=request.user)
            .values('category')
            .annotate(total=Sum('amount'), count=Count('id'))
            .order_by('-total')
        )
        return Response({'per_trip': list(trips), 'by_category': list(by_category)})

    @action(detail=False, methods=['get'])
    def destination_preferences(self, request):
        """Which destination categories and countries this user books most."""
        prefs = (
            self._user_trips(request)
            .values('destination__category', 'destination__country')
            .annotate(trip_count=Count('id'))
            .order_by('-trip_count')
        )
        return Response(list(prefs))
