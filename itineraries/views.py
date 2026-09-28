from django.contrib.auth import get_user_model
from django.db.models import Count, F, Prefetch, Q, Sum
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend

from travel_api.pagination import StandardResultsPagination

from .filters import ItineraryFilter
from .models import Collaboration, Itinerary
from .permissions import CanEditItinerary, IsTripOwner
from .serializers import (
    ItineraryCreateUpdateSerializer,
    ItineraryDetailSerializer,
    ItineraryListSerializer,
)

User = get_user_model()


# --- Function-based views ---------------------------------------------------

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def trip_search(request):
    """
    GET: search the current user's trips with a few optional filters.
    POST: save the search terms onto the user's preferences for next time.
    """
    if request.method == 'GET':
        # start from trips the user can see (owns or is a collaborator on)
        trips = Itinerary.objects.filter(
            Q(owner=request.user) | Q(collaborators=request.user)
        ).select_related('destination', 'owner').distinct()

        # optional filters, all stackable
        query = request.query_params.get('q')
        if query:
            trips = trips.filter(Q(title__icontains=query) | Q(description__icontains=query))
        trip_status = request.query_params.get('status')
        if trip_status:
            trips = trips.filter(status=trip_status)
        max_budget = request.query_params.get('max_budget')
        if max_budget:
            trips = trips.filter(budget__lte=max_budget)

        serializer = ItineraryListSerializer(trips, many=True, context={'request': request})
        return Response(serializer.data)

    # POST - remember what they searched for
    prefs = request.user.travel_preferences or {}
    prefs['last_trip_search'] = request.data
    request.user.travel_preferences = prefs
    request.user.save(update_fields=['travel_preferences'])
    return Response({'saved': True}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def generate_trip_report(request, trip_id):
    """
    Pull together a single trip's numbers - budget, what's booked, how many
    days and activities - into one summary.
    """
    try:
        trip = (
            Itinerary.objects.select_related('destination', 'owner')
            .prefetch_related('bookings', 'expenses', 'daily_plans__activities')
            .get(Q(pk=trip_id) & (Q(owner=request.user) | Q(collaborators=request.user)))
        )
    except Itinerary.DoesNotExist:
        return Response({'error': 'Trip not found'}, status=status.HTTP_404_NOT_FOUND)

    # aggregate booking spend and expense totals in one query each
    booking_totals = trip.bookings.aggregate(
        total_booked=Sum('price'),
        booking_count=Count('id'),
    )
    expense_total = trip.expenses.aggregate(total_spent=Sum('amount'))['total_spent'] or 0

    report = {
        'trip': ItineraryDetailSerializer(trip, context={'request': request}).data,
        'duration_days': trip.duration_days,
        'total_activities': trip.daily_plans.aggregate(n=Count('activities'))['n'],
        'total_booked': booking_totals['total_booked'] or 0,
        'booking_count': booking_totals['booking_count'],
        'total_spent': expense_total,
        'budget': trip.budget,
        'budget_remaining': trip.budget_remaining,
    }
    return Response(report)


# --- Class-based views ------------------------------------------------------

class ItineraryListCreateView(generics.ListCreateAPIView):
    """List the trips the current user owns, or create a new one."""

    serializer_class = ItineraryListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # only their own trips here; pull destination in the same query
        return Itinerary.objects.filter(owner=self.request.user).select_related(
            'destination', 'owner'
        ).prefetch_related('daily_plans', 'bookings')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class TripCollaborationView(APIView):
    """
    Manage who a trip is shared with. Only the trip owner can add, change, or
    remove collaborators.
    """

    permission_classes = [permissions.IsAuthenticated, IsTripOwner]

    def get_trip(self, trip_id):
        trip = generics.get_object_or_404(Itinerary, pk=trip_id)
        # run the object-level owner check by hand since this isn't a generic view
        self.check_object_permissions(self.request, trip)
        return trip

    def post(self, request, trip_id):
        # add someone as a collaborator with a role
        trip = self.get_trip(trip_id)
        user = generics.get_object_or_404(User, pk=request.data.get('user_id'))
        role = request.data.get('role', 'viewer')
        collab, created = Collaboration.objects.get_or_create(
            itinerary=trip, user=user, defaults={'role': role}
        )
        return Response(
            {'user': user.username, 'role': collab.role, 'created': created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def patch(self, request, trip_id, user_id):
        # bump an existing collaborator to a different role
        trip = self.get_trip(trip_id)
        collab = generics.get_object_or_404(Collaboration, itinerary=trip, user_id=user_id)
        collab.role = request.data.get('role', collab.role)
        collab.save(update_fields=['role'])
        return Response({'user_id': user_id, 'role': collab.role})

    def delete(self, request, trip_id, user_id):
        # remove someone from the trip
        trip = self.get_trip(trip_id)
        Collaboration.objects.filter(itinerary=trip, user_id=user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- ViewSet ----------------------------------------------------------------

class ItineraryViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for itineraries, plus some handy extra actions (duplicate, share,
    upcoming). Only shows trips the user owns or collaborates on.
    """

    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ItineraryFilter
    search_fields = ['title', 'description', 'destination__name']
    ordering_fields = ['created_at', 'start_date', 'budget']

    def get_queryset(self):
        # trips they own OR collaborate on; load related rows up front so the
        # serializer doesn't fire a query per row
        return (
            Itinerary.objects.filter(
                Q(owner=self.request.user) | Q(collaborators=self.request.user)
            )
            .select_related('destination', 'owner')
            .prefetch_related(
                'daily_plans__activities',
                'bookings__accommodation',
                Prefetch('collaborators', queryset=User.objects.filter(is_active=True)),
            )
            .annotate(
                activity_count=Count('daily_plans__activities', distinct=True),
                booked_total=Sum('bookings__price'),
            )
            .distinct()
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return ItineraryListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return ItineraryCreateUpdateSerializer
        return ItineraryDetailSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, CanEditItinerary])
    def duplicate(self, request, pk=None):
        """Copy an existing trip into a fresh one (status back to planning)."""
        original = self.get_object()
        clone = Itinerary.objects.create(
            title=f"{original.title} (copy)",
            description=original.description,
            destination=original.destination,
            owner=request.user,
            start_date=original.start_date,
            end_date=original.end_date,
            budget=original.budget,
        )
        return Response(
            ItineraryDetailSerializer(clone, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='share')
    def share_with_user(self, request, pk=None):
        """Share this trip with another user by their id."""
        trip = self.get_object()
        user = generics.get_object_or_404(User, pk=request.data.get('user_id'))
        role = request.data.get('role', 'viewer')
        trip.add_collaborator(user, role=role)
        return Response({'shared_with': user.username, 'role': role}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='upcoming')
    def upcoming_trips(self, request):
        """The user's trips that haven't started yet, soonest first."""
        from django.utils import timezone
        today = timezone.now().date()
        # trim to just the columns the list serializer reads (destination/owner
        # names still come through the select_related join)
        trips = (
            self.get_queryset()
            .filter(start_date__gte=today)
            .only(
                'id', 'title', 'destination', 'owner', 'start_date', 'end_date',
                'budget', 'actual_spent', 'status', 'is_public',
            )
            .order_by('start_date')
        )
        page = self.paginate_queryset(trips)
        serializer = ItineraryListSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)
