from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from destinations.models import Destination
from itineraries.models import Itinerary

from .models import Accommodation, Activity, Booking
from .permissions import IsBookingOwner

User = get_user_model()


def setup_world(username='u'):
    """Build a destination + trip + accommodation + activity for a user."""
    dest = Destination.objects.create(
        name='NYC', country='USA', description='d', category='city',
        climate='temperate', best_time_to_visit='Fall', avg_daily_cost=250,
    )
    user = User.objects.create_user(username=username, email=f'{username}@test.local', password='pass12345')
    trip = Itinerary.objects.create(
        title='NYC', destination=dest, owner=user,
        start_date=date(2026, 10, 1), end_date=date(2026, 10, 5), budget=5000,
    )
    acc = Accommodation.objects.create(
        name='Hotel', destination=dest, accommodation_type='hotel', description='d',
        price_per_night=200, max_guests=2, address='addr',
        contact_email='h@test.local', contact_phone='123',
    )
    act = Activity.objects.create(
        name='Tour', destination=dest, category='tour', description='d',
        duration_hours=2, price=50,
    )
    return dest, user, trip, acc, act


class BookingModelTests(APITestCase):
    def setUp(self):
        self.dest, self.user, self.trip, self.acc, self.act = setup_world()

    def test_clean_needs_a_target(self):
        booking = Booking(user=self.user, itinerary=self.trip, booking_date=date(2026, 10, 1), price=200)
        with self.assertRaises(ValidationError):
            booking.clean()

    def test_clean_rejects_both_targets(self):
        booking = Booking(
            user=self.user, itinerary=self.trip, accommodation=self.acc, activity=self.act,
            booking_date=date(2026, 10, 1), price=200,
        )
        with self.assertRaises(ValidationError):
            booking.clean()

    def test_str_uses_accommodation_name(self):
        booking = Booking.objects.create(
            user=self.user, itinerary=self.trip, accommodation=self.acc,
            booking_date=date(2026, 10, 1), price=200,
        )
        self.assertIn('Hotel', str(booking))


class BookingAPITests(APITestCase):
    def setUp(self):
        self.dest, self.owner, self.trip, self.acc, self.act = setup_world('owner')
        self.other = User.objects.create_user(username='other', email='ot@test.local', password='pass12345')
        self.booking = Booking.objects.create(
            user=self.owner, itinerary=self.trip, activity=self.act,
            booking_date=date(2026, 10, 1), price=80,
        )
        self.client.force_authenticate(self.owner)

    def test_create_booking_sets_current_user(self):
        resp = self.client.post('/api/v1/bookings/', {
            'itinerary': self.trip.id, 'activity': self.act.id,
            'booking_date': '2026-10-02', 'price': 80,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Booking.objects.filter(user=self.owner).count(), 2)

    def test_confirm_action(self):
        resp = self.client.post(f'/api/v1/bookings/{self.booking.id}/confirm/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'confirmed')

    def test_bulk_update(self):
        resp = self.client.post('/api/v1/bookings/bulk-update/', {
            'ids': [self.booking.id], 'status': 'confirmed',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['updated'], 1)

    def test_is_booking_owner_permission(self):
        factory = APIRequestFactory()
        req = factory.get('/')
        req.user = self.other
        self.assertFalse(IsBookingOwner().has_object_permission(req, None, self.booking))
        req.user = self.owner
        self.assertTrue(IsBookingOwner().has_object_permission(req, None, self.booking))
