from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Destination
from .serializers import DestinationDetailSerializer

User = get_user_model()


def make_destination(**overrides):
    """Small factory so each test doesn't repeat the required fields."""
    defaults = dict(
        name='Paris', country='France', description='City of light',
        category=Destination.CategoryChoices.CITY,
        climate=Destination.ClimateChoices.TEMPERATE,
        best_time_to_visit='Spring', avg_daily_cost=150,
    )
    defaults.update(overrides)
    return Destination.objects.create(**defaults)


class DestinationModelTests(APITestCase):
    def setUp(self):
        self.dest = make_destination()

    def test_str(self):
        self.assertEqual(str(self.dest), 'Paris, France')

    def test_average_rating_with_no_reviews_is_zero(self):
        self.assertEqual(self.dest.average_rating, 0)


class DestinationSerializerTests(APITestCase):
    def test_detail_serializer_has_computed_fields(self):
        dest = make_destination(name='Rome', country='Italy')
        data = DestinationDetailSerializer(dest).data
        self.assertEqual(data['review_count'], 0)
        self.assertEqual(data['total_itineraries'], 0)
        self.assertIn('top_activities', data)


class DestinationViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='u', email='u@test.local', password='Str0ngPass!23'
        )
        self.dest = make_destination(name='Tokyo', country='Japan')

    def test_list_requires_auth(self):
        self.assertEqual(self.client.get('/api/v1/destinations/').status_code,
                         status.HTTP_401_UNAUTHORIZED)

    def test_list_destinations(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get('/api/v1/destinations/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 1)

    def test_retrieve_uses_detail_serializer(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(f'/api/v1/destinations/{self.dest.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('top_activities', resp.data)

    def test_by_country_str_converter(self):
        # public endpoint, and shows the <str:country> route works
        resp = self.client.get('/api/v1/destinations/country/Japan/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 1)
