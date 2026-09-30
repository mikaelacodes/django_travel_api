from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from budgets.models import Budget
from destinations.models import Destination

from .models import ActivityLog, Collaboration, Itinerary
from .permissions import CanEditItinerary, IsTripOwner, IsTripOwnerOrCollaborator
from .serializers import ItineraryCreateUpdateSerializer, ItineraryDetailSerializer

User = get_user_model()


def make_destination(name='Bali', country='Indonesia'):
    return Destination.objects.create(
        name=name, country=country, description='d', category='beach',
        climate='tropical', best_time_to_visit='Summer', avg_daily_cost=100,
    )


class ItineraryModelTests(APITestCase):
    def setUp(self):
        self.dest = make_destination()
        self.user = User.objects.create_user(username='owner', email='o@test.local', password='pass12345')
        self.trip = Itinerary.objects.create(
            title='Bali Trip', destination=self.dest, owner=self.user,
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 7), budget=2000,
        )

    def test_duration_days(self):
        self.assertEqual(self.trip.duration_days, 7)

    def test_budget_remaining(self):
        self.assertEqual(self.trip.budget_remaining, 2000)

    def test_clean_rejects_end_before_start(self):
        self.trip.end_date = date(2026, 5, 1)
        with self.assertRaises(ValidationError):
            self.trip.clean()

    def test_add_collaborator(self):
        collab = User.objects.create_user(username='c', email='c@test.local', password='pass12345')
        self.trip.add_collaborator(collab, role='editor')
        self.assertTrue(
            Collaboration.objects.filter(itinerary=self.trip, user=collab, role='editor').exists()
        )


class ItineraryAPITests(APITestCase):
    def setUp(self):
        self.dest = make_destination('Lisbon', 'Portugal')
        self.user = User.objects.create_user(username='owner', email='o@test.local', password='pass12345')
        self.other = User.objects.create_user(username='other', email='ot@test.local', password='pass12345')
        self.client.force_authenticate(self.user)
        self.trip = Itinerary.objects.create(
            title='Lisbon Trip', destination=self.dest, owner=self.user,
            start_date=date(2026, 7, 1), end_date=date(2026, 7, 10), budget=3000,
        )

    def _new_trip_payload(self, **extra):
        payload = {
            'title': 'Rome', 'destination': self.dest.id,
            'start_date': '2026-08-01', 'end_date': '2026-08-05', 'budget': 1500,
        }
        payload.update(extra)
        return payload

    def test_list_shows_only_own_trips(self):
        resp = self.client.get('/api/v1/itineraries/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 1)

    def test_create_itinerary(self):
        resp = self.client.post('/api/v1/itineraries/', self._new_trip_payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Itinerary.objects.filter(owner=self.user).count(), 2)

    def test_create_auto_creates_budget(self):
        resp = self.client.post('/api/v1/itineraries/', self._new_trip_payload(title='Oslo'), format='json')
        self.assertTrue(Budget.objects.filter(itinerary_id=resp.data['id']).exists())

    def test_update_own_trip(self):
        resp = self.client.patch(f'/api/v1/itineraries/{self.trip.id}/', {'budget': 2500}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_cannot_see_others_trip(self):
        self.client.force_authenticate(self.other)
        resp = self.client.get(f'/api/v1/itineraries/{self.trip.id}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_upcoming_action(self):
        resp = self.client.get('/api/v1/itineraries/upcoming/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class ActivityLogTests(APITestCase):
    """The audit trail: signals write log rows, and the endpoint reads them back."""

    def setUp(self):
        self.dest = make_destination('Porto', 'Portugal')
        self.user = User.objects.create_user(username='logger', email='l@test.local', password='pass12345')

    def test_creating_a_trip_writes_a_log(self):
        trip = Itinerary.objects.create(
            title='Porto Trip', destination=self.dest, owner=self.user,
            start_date=date(2026, 3, 1), end_date=date(2026, 3, 5), budget=1200,
        )
        log = ActivityLog.objects.filter(object_type='Itinerary', object_id=trip.id).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.action, ActivityLog.ActionChoices.CREATED)
        self.assertEqual(log.user, self.user)

    def test_log_endpoint_shows_only_own_activity(self):
        Itinerary.objects.create(
            title='Mine', destination=self.dest, owner=self.user,
            start_date=date(2026, 3, 1), end_date=date(2026, 3, 5), budget=1200,
        )
        self.client.force_authenticate(self.user)
        resp = self.client.get('/api/v1/activity-logs/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data['count'], 1)


class ItinerarySerializerTests(APITestCase):
    """Serializer-level validation, tested without going through a view."""

    def setUp(self):
        self.dest = make_destination('Nice', 'France')

    def test_budget_must_be_positive(self):
        serializer = ItineraryCreateUpdateSerializer(data={
            'title': 'x', 'destination': self.dest.id,
            'start_date': '2026-01-01', 'end_date': '2026-01-05', 'budget': 0,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('budget', serializer.errors)

    def test_end_date_before_start_rejected(self):
        serializer = ItineraryDetailSerializer(data={
            'title': 'x', 'destination_id': self.dest.id,
            'start_date': '2026-01-10', 'end_date': '2026-01-05', 'budget': 100,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('end_date', serializer.errors)


class ItineraryPermissionTests(APITestCase):
    """Exercise the custom permission classes directly."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.dest = make_destination('Cairo', 'Egypt')
        self.owner = User.objects.create_user(username='owner', email='o@test.local', password='pass12345')
        self.editor = User.objects.create_user(username='editor', email='e@test.local', password='pass12345')
        self.viewer = User.objects.create_user(username='viewer', email='v@test.local', password='pass12345')
        self.trip = Itinerary.objects.create(
            title='Cairo', destination=self.dest, owner=self.owner,
            start_date=date(2026, 9, 1), end_date=date(2026, 9, 5), budget=1000,
        )
        self.trip.add_collaborator(self.editor, role='editor')
        self.trip.add_collaborator(self.viewer, role='viewer')

    def _req(self, user, method='get'):
        req = getattr(self.factory, method)('/')
        req.user = user
        return req

    def test_is_trip_owner(self):
        perm = IsTripOwner()
        self.assertTrue(perm.has_object_permission(self._req(self.owner), None, self.trip))
        self.assertFalse(perm.has_object_permission(self._req(self.editor), None, self.trip))

    def test_owner_or_collaborator_can_read_not_write(self):
        perm = IsTripOwnerOrCollaborator()
        self.assertTrue(perm.has_object_permission(self._req(self.viewer, 'get'), None, self.trip))
        self.assertFalse(perm.has_object_permission(self._req(self.viewer, 'put'), None, self.trip))

    def test_can_edit_respects_role(self):
        perm = CanEditItinerary()
        self.assertTrue(perm.has_object_permission(self._req(self.owner, 'put'), None, self.trip))
        self.assertTrue(perm.has_object_permission(self._req(self.editor, 'put'), None, self.trip))
        self.assertFalse(perm.has_object_permission(self._req(self.viewer, 'put'), None, self.trip))
