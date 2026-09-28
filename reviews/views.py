from rest_framework import filters, generics, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend

from .models import Review
from .permissions import IsAuthorOrReadOnly
from .serializers import ReviewSerializer


class DestinationReviewsView(generics.ListAPIView):
    """All reviews for one destination, newest first. Public - anyone can read."""

    serializer_class = ReviewSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        destination_id = self.kwargs['destination_id']
        # pull the reviewer along, and skip the big image blob we don't show here
        return (
            Review.objects.filter(destination_id=destination_id)
            .select_related('user')
            .defer('images')
            .order_by('-created_at')
        )


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Read a review (anyone) or edit/delete it (author only)."""

    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    def get_queryset(self):
        return Review.objects.select_related('user', 'destination', 'accommodation', 'activity')


class ReviewViewSet(viewsets.ModelViewSet):
    """CRUD for reviews. Anyone can read; you have to own a review to change it."""

    serializer_class = ReviewSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['rating', 'destination', 'accommodation', 'activity']
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'rating', 'helpful_count']

    def get_queryset(self):
        # only pull the two columns the list actually leans on for related data
        return Review.objects.select_related('user', 'destination').only(
            'id', 'title', 'content', 'rating', 'helpful_count', 'created_at',
            'user__username', 'destination__name',
        )

    def get_permissions(self):
        # reads are open; writes need to be authenticated and the author
        if self.action in ('update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsAuthorOrReadOnly()]
        return [permissions.IsAuthenticatedOrReadOnly()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def mark_helpful(self, request, pk=None):
        """Bump the helpful counter on a review."""
        review = self.get_object()
        review.helpful_count += 1
        review.save(update_fields=['helpful_count'])
        return Response({'helpful_count': review.helpful_count})
