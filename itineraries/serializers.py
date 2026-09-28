from rest_framework import serializers

from destinations.models import Destination
from destinations.serializers import DestinationListSerializer

from .models import Collaboration, DailyPlan, Itinerary


class CollaborationSerializer(serializers.ModelSerializer):
    """Who a trip is shared with, plus what they're allowed to do."""

    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Collaboration
        fields = ['id', 'user', 'username', 'email', 'role', 'invited_at']
        read_only_fields = ['invited_at']


class DailyPlanSerializer(serializers.ModelSerializer):
    """A single day, with a quick count of how many activities are on it."""

    activities_count = serializers.SerializerMethodField()

    class Meta:
        model = DailyPlan
        fields = ['id', 'day_number', 'date', 'title', 'notes', 'activities', 'activities_count']

    def get_activities_count(self, obj):
        return obj.activities.count()


class ItineraryListSerializer(serializers.ModelSerializer):
    """Light list view - names instead of full nested objects to keep it fast."""

    destination_name = serializers.CharField(source='destination.name', read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    duration_days = serializers.ReadOnlyField()
    budget_remaining = serializers.ReadOnlyField()

    class Meta:
        model = Itinerary
        fields = [
            'id', 'title', 'destination', 'destination_name', 'owner', 'owner_username',
            'start_date', 'end_date', 'duration_days', 'budget', 'budget_remaining',
            'status', 'is_public',
        ]
        read_only_fields = ['id', 'owner']


class ItineraryDetailSerializer(serializers.ModelSerializer):
    """
    Full trip view with the destination, days, and collaborators nested in.
    Read gives you the whole picture; on write you pass destination_id.
    """

    destination = DestinationListSerializer(read_only=True)
    # let clients set the destination by id without exposing the nested object as writable
    destination_id = serializers.PrimaryKeyRelatedField(
        queryset=Destination.objects.all(),
        source='destination',
        write_only=True,
    )
    daily_plans = DailyPlanSerializer(many=True, read_only=True)
    collaborations = CollaborationSerializer(many=True, read_only=True)
    bookings_count = serializers.SerializerMethodField()
    duration_days = serializers.ReadOnlyField()
    budget_remaining = serializers.ReadOnlyField()

    class Meta:
        model = Itinerary
        fields = '__all__'
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def get_bookings_count(self, obj):
        return obj.bookings.count()

    def validate(self, data):
        # same rule as the model - a trip can't end before it starts
        start = data.get('start_date')
        end = data.get('end_date')
        if start and end and end < start:
            raise serializers.ValidationError({'end_date': 'End date must be after start date'})
        return data

    def create(self, validated_data):
        # make the trip, then give it an empty budget to fill in later
        itinerary = Itinerary.objects.create(**validated_data)
        from budgets.models import Budget
        Budget.objects.get_or_create(itinerary=itinerary)
        return itinerary


class ItineraryCreateUpdateSerializer(serializers.ModelSerializer):
    """Leaner serializer for create/update - only the fields a user actually fills in."""

    class Meta:
        model = Itinerary
        fields = ['title', 'description', 'destination', 'start_date', 'end_date', 'budget', 'is_public']

    def validate_budget(self, value):
        if value <= 0:
            raise serializers.ValidationError('Budget has to be more than zero')
        return value

    def create(self, validated_data):
        # same auto-budget behaviour so it works no matter which serializer creates the trip
        itinerary = Itinerary.objects.create(**validated_data)
        from budgets.models import Budget
        Budget.objects.get_or_create(itinerary=itinerary)
        return itinerary

    def to_representation(self, instance):
        # respond with the full detail shape so the client gets everything back
        return ItineraryDetailSerializer(instance, context=self.context).data
