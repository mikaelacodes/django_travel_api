from rest_framework import serializers

from .models import Destination


class DestinationListSerializer(serializers.ModelSerializer):
    """Slim version for list pages - just enough to fill a card."""

    average_rating = serializers.ReadOnlyField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = Destination
        fields = [
            'id', 'name', 'country', 'category', 'climate',
            'avg_daily_cost', 'image', 'average_rating', 'review_count',
        ]
        read_only_fields = ['id']

    def get_review_count(self, obj):
        return obj.reviews.count()


class DestinationDetailSerializer(DestinationListSerializer):
    """
    The full destination for its own page. Builds on the list serializer so we
    don't repeat the review_count / average_rating setup.
    """

    total_itineraries = serializers.SerializerMethodField()
    top_activities = serializers.SerializerMethodField()

    class Meta(DestinationListSerializer.Meta):
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_itineraries(self, obj):
        return obj.itineraries.count()

    def get_top_activities(self, obj):
        # grab the first five activities here; import locally to avoid a loop
        from bookings.serializers import ActivitySerializer
        return ActivitySerializer(obj.activities.all()[:5], many=True).data
