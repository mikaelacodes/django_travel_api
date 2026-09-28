from django.db import transaction
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend

from .filters import BookingFilter
from .models import Accommodation, Activity, Booking
from .permissions import IsBookingOwner
from .serializers import (
    AccommodationSerializer,
    ActivitySerializer,
    BookingDetailSerializer,
    BookingSerializer,
)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_update_bookings(request):
    """
    Update a bunch of the user's bookings in one go. Body looks like:
    {"ids": [1, 2, 3], "status": "confirmed"}. We only touch bookings that
    actually belong to the caller, and do it all in one transaction.
    """
    ids = request.data.get('ids', [])
    new_status = request.data.get('status')

    if not ids or not new_status:
        return Response(
            {'error': 'Send a list of "ids" and a "status" to set'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    updated, skipped = 0, 0
    try:
        with transaction.atomic():
            for booking in Booking.objects.filter(id__in=ids, user=request.user):
                booking.status = new_status
                booking.save(update_fields=['status'])
                updated += 1
        # anything asked for that we didn't own/find gets counted as skipped
        skipped = len(ids) - updated
    except Exception as exc:  # keep a bad row from 500-ing the whole request
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'updated': updated, 'skipped': skipped})


class BookingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Look at, change, or cancel a single booking - owner only."""

    serializer_class = BookingDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsBookingOwner]

    def get_queryset(self):
        # pull the related listing + trip in the same query for the detail view
        return Booking.objects.filter(user=self.request.user).select_related(
            'accommodation', 'activity', 'itinerary'
        )


class BookingViewSet(viewsets.ModelViewSet):
    """Manage the current user's bookings. Permissions tighten up for writes."""

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BookingFilter
    search_fields = ['confirmation_code', 'itinerary__title']
    ordering_fields = ['created_at', 'booking_date', 'price']

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related(
            'accommodation', 'activity', 'itinerary'
        )

    def get_serializer_class(self):
        # nest the full listing when you're looking at one booking
        if self.action == 'retrieve':
            return BookingDetailSerializer
        return BookingSerializer

    def get_permissions(self):
        # anyone logged in can create/list their own; only the owner can change/delete
        if self.action in ('update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsBookingOwner()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Mark a pending booking as confirmed."""
        booking = self.get_object()
        booking.status = Booking.StatusChoices.CONFIRMED
        booking.save(update_fields=['status'])
        return Response({'status': booking.status})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking."""
        booking = self.get_object()
        booking.status = Booking.StatusChoices.CANCELLED
        booking.save(update_fields=['status'])
        return Response({'status': booking.status})


class AccommodationViewSet(viewsets.ReadOnlyModelViewSet):
    """Browse places to stay. Read-only - these get managed in the admin."""

    serializer_class = AccommodationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['destination', 'accommodation_type', 'is_available']
    search_fields = ['name', 'address', 'destination__name']
    ordering_fields = ['name', 'price_per_night']

    def get_queryset(self):
        # only the destination FK is needed for the serializer's destination_name
        return Accommodation.objects.select_related('destination')


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """Browse activities. Read-only for the same reason as accommodations."""

    serializer_class = ActivitySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['destination', 'category', 'is_available']
    search_fields = ['name', 'description', 'destination__name']
    ordering_fields = ['name', 'price', 'duration_hours']

    def get_queryset(self):
        return Activity.objects.select_related('destination')
