from rest_framework import serializers

from .models import Accommodation, Activity, Booking


class AccommodationSerializer(serializers.ModelSerializer):
    """A place to stay, plus the destination name so the client doesn't have to look it up."""

    destination_name = serializers.CharField(source='destination.name', read_only=True)

    class Meta:
        model = Accommodation
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class ActivitySerializer(serializers.ModelSerializer):
    """Something to do, with the destination name tagged on for convenience."""

    destination_name = serializers.CharField(source='destination.name', read_only=True)

    class Meta:
        model = Activity
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class BookingSerializer(serializers.ModelSerializer):
    """A booking. user gets set from the request in the view, so it's read-only here."""

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def validate(self, data):
        # same rule as the model: exactly one of accommodation / activity
        accommodation = data.get('accommodation')
        activity = data.get('activity')
        if not accommodation and not activity:
            raise serializers.ValidationError('A booking needs either an accommodation or an activity')
        if accommodation and activity:
            raise serializers.ValidationError("A booking can't have both an accommodation and an activity")
        return data


class BookingDetailSerializer(BookingSerializer):
    """
    Same as BookingSerializer but with the accommodation and activity fully
    nested, for when you're looking at one booking on its own.
    """

    accommodation = AccommodationSerializer(read_only=True)
    activity = ActivitySerializer(read_only=True)
