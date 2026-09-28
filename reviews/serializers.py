from rest_framework import serializers

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    """
    A review. The author and helpful_count are set by the system, not the user,
    so they're read-only.
    """

    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Review
        fields = '__all__'
        read_only_fields = ['id', 'user', 'helpful_count', 'created_at', 'updated_at']

    def validate(self, data):
        # a review is about exactly one thing - destination, accommodation, or activity
        targets = [data.get('destination'), data.get('accommodation'), data.get('activity')]
        if sum(1 for t in targets if t) != 1:
            raise serializers.ValidationError('A review has to be about exactly one thing')
        return data

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError('Rating has to be between 1 and 5')
        return value

    def update(self, instance, validated_data):
        # don't let people move a review onto a different target after the fact
        for field in ('destination', 'accommodation', 'activity'):
            validated_data.pop(field, None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance
