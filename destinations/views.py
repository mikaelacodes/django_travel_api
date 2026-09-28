from django.db.models import Count, Prefetch, Q
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend

from bookings.models import Activity

from .filters import DestinationFilter
from .models import Destination
from .serializers import DestinationDetailSerializer, DestinationListSerializer


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def destination_wishlist(request):
    """
    GET: the destinations the user has saved to their wishlist.
    POST: add a destination to it (send {"destination_id": 5}).
    """
    prefs = request.user.travel_preferences or {}
    wishlist = prefs.get('wishlist', [])

    if request.method == 'POST':
        dest_id = request.data.get('destination_id')
        # make sure it's a real, active destination before saving it
        if not Destination.objects.filter(pk=dest_id, is_active=True).exists():
            return Response({'error': 'Destination not found'}, status=status.HTTP_404_NOT_FOUND)
        if dest_id not in wishlist:
            wishlist.append(dest_id)
            prefs['wishlist'] = wishlist
            request.user.travel_preferences = prefs
            request.user.save(update_fields=['travel_preferences'])
        return Response({'wishlist': wishlist}, status=status.HTTP_201_CREATED)

    # GET - return the saved destinations themselves, not just their ids
    destinations = Destination.objects.filter(pk__in=wishlist)
    return Response(DestinationListSerializer(destinations, many=True, context={'request': request}).data)


class DestinationSearchView(APIView):
    """
    Custom search over destinations. Anyone can search (read), but you have to
    be logged in to save a search as a preference.
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request):
        # free-text query that looks across a few fields at once
        query = request.query_params.get('q', '')
        results = Destination.objects.filter(is_active=True)
        if query:
            results = results.filter(
                Q(name__icontains=query)
                | Q(country__icontains=query)
                | Q(description__icontains=query)
            )
        # rank by how many reviews each place has, most-reviewed first
        results = (
            results.annotate(num_reviews=Count('reviews'))
            .prefetch_related('reviews')
            .order_by('-num_reviews', 'name')
        )
        serializer = DestinationListSerializer(results, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        # stash the search text on the user's travel_preferences so they can reuse it
        prefs = request.user.travel_preferences or {}
        saved = prefs.get('saved_searches', [])
        saved.append(request.data.get('q', ''))
        prefs['saved_searches'] = saved
        request.user.travel_preferences = prefs
        request.user.save(update_fields=['travel_preferences'])
        return Response({'saved_searches': saved})


class DestinationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Browse destinations (read-only for regular users - they get created in the
    admin). Uses a light serializer for the list and the full one for detail.
    """

    # prefetch the available activities (via a Prefetch object so we can filter
    # them) and reviews, since the detail serializer reaches for both
    queryset = Destination.objects.filter(is_active=True).prefetch_related(
        Prefetch('activities', queryset=Activity.objects.filter(is_available=True)),
        'reviews',
    )
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DestinationFilter
    search_fields = ['name', 'description', 'country']
    ordering_fields = ['name', 'avg_daily_cost', 'created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DestinationDetailSerializer
        return DestinationListSerializer

    @action(detail=True, methods=['get'])
    def popular_activities(self, request, pk=None):
        """Top activities at this destination, ranked by how often they're booked."""
        destination = self.get_object()
        # annotate each activity with its booking count, busiest first
        activities = (
            destination.activities.annotate(booking_count=Count('bookings'))
            .order_by('-booking_count')[:10]
        )
        from bookings.serializers import ActivitySerializer
        return Response(ActivitySerializer(activities, many=True, context={'request': request}).data)

    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """All reviews for this destination."""
        destination = self.get_object()
        # only pull the reviewer along - that's all the serializer needs here
        qs = destination.reviews.select_related('user').all()
        from reviews.serializers import ReviewSerializer
        return Response(ReviewSerializer(qs, many=True, context={'request': request}).data)
