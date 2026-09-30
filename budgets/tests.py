from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from destinations.models import Destination
from itineraries.models import Itinerary

from .models import Budget
from .serializers import ExpenseSerializer

User = get_user_model()


def make_trip(username='u'):
    dest = Destination.objects.create(
        name='Berlin', country='Germany', description='d', category='city',
        climate='continental', best_time_to_visit='Summer', avg_daily_cost=130,
    )
    user = User.objects.create_user(username=username, email=f'{username}@test.local', password='pass12345')
    trip = Itinerary.objects.create(
        title='Berlin', destination=dest, owner=user,
        start_date=date(2026, 5, 1), end_date=date(2026, 5, 5), budget=2000,
    )
    return user, trip


class BudgetModelTests(APITestCase):
    def setUp(self):
        self.user, self.trip = make_trip()

    def test_total_budget_sums_categories(self):
        budget = Budget.objects.create(
            itinerary=self.trip, accommodation_budget=500, food_budget=300,
        )
        self.assertEqual(budget.total_budget, 800)


class ExpenseSerializerTests(APITestCase):
    def setUp(self):
        self.user, self.trip = make_trip()

    def test_amount_must_be_positive(self):
        serializer = ExpenseSerializer(data={
            'itinerary': self.trip.id, 'category': 'food',
            'description': 'lunch', 'amount': -5, 'date': '2026-05-02',
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)


class AnalyticsAPITests(APITestCase):
    def setUp(self):
        self.user, self.trip = make_trip()
        self.client.force_authenticate(self.user)

    def test_analytics_list(self):
        resp = self.client.get('/api/v1/analytics/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['trip_count'], 1)

    def test_budget_summary(self):
        resp = self.client.get('/api/v1/analytics/budget_summary/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('per_trip', resp.data)
