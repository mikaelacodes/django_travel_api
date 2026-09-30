from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from destinations.models import Destination

from .models import Review
from .permissions import IsAuthorOrReadOnly
from .serializers import ReviewSerializer

User = get_user_model()


def make_destination(name='Oslo', country='Norway'):
    return Destination.objects.create(
        name=name, country=country, description='d', category='city',
        climate='continental', best_time_to_visit='Summer', avg_daily_cost=180,
    )


class ReviewModelTests(APITestCase):
    def setUp(self):
        self.dest = make_destination()
        self.user = User.objects.create_user(username='u', email='u@test.local', password='pass12345')

    def test_clean_needs_exactly_one_target(self):
        review = Review(user=self.user, rating=5, title='t', content='c', visit_date=date(2026, 1, 1))
        with self.assertRaises(ValidationError):
            review.clean()

    def test_clean_ok_with_one_target(self):
        review = Review(
            user=self.user, destination=self.dest, rating=5, title='t',
            content='c', visit_date=date(2026, 1, 1),
        )
        # should not raise
        review.clean()


class ReviewSerializerTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', email='u@test.local', password='pass12345')

    def test_review_needs_a_target(self):
        serializer = ReviewSerializer(data={
            'rating': 5, 'title': 't', 'content': 'c', 'visit_date': '2026-01-01',
        })
        self.assertFalse(serializer.is_valid())


class ReviewAPITests(APITestCase):
    def setUp(self):
        self.dest = make_destination('Kyoto', 'Japan')
        self.author = User.objects.create_user(username='author', email='a@test.local', password='pass12345')
        self.other = User.objects.create_user(username='other', email='o@test.local', password='pass12345')
        self.review = Review.objects.create(
            user=self.author, destination=self.dest, rating=4, title='Nice',
            content='Good', visit_date=date(2026, 1, 1),
        )

    def test_create_review_sets_current_user(self):
        self.client.force_authenticate(self.author)
        resp = self.client.post('/api/v1/reviews/', {
            'destination': self.dest.id, 'rating': 5, 'title': 'Great',
            'content': 'Loved it', 'visit_date': '2026-02-01',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_reviews_are_publicly_readable(self):
        resp = self.client.get('/api/v1/reviews/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_author_only_permission(self):
        factory = APIRequestFactory()
        # a stranger can read but not write
        get_req = factory.get('/')
        get_req.user = self.other
        self.assertTrue(IsAuthorOrReadOnly().has_object_permission(get_req, None, self.review))
        put_req = factory.put('/')
        put_req.user = self.other
        self.assertFalse(IsAuthorOrReadOnly().has_object_permission(put_req, None, self.review))
        # the author can write
        put_req.user = self.author
        self.assertTrue(IsAuthorOrReadOnly().has_object_permission(put_req, None, self.review))
