from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """What we send back when we talk about a user - the safe, public-ish fields."""

    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'date_of_birth', 'bio', 'profile_picture',
            'travel_preferences', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def update(self, instance, validated_data):
        # plain profile update - just copy over whatever they sent and save
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Handles sign-up. Takes the password twice so we can catch typos, and never
    sends it back out (write_only).
    """

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'password', 'password2']

    def validate(self, data):
        # the two passwords have to match
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'The two passwords do not match'})
        return data

    def create(self, validated_data):
        # drop the confirm field, hash the real password properly
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def to_representation(self, instance):
        # after creating, hand back the normal user shape (no password fields)
        return UserSerializer(instance, context=self.context).data


class LoginSerializer(serializers.Serializer):
    """Checks a username + password and, if they're good, tucks the user into the data."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Wrong username or password')
        data['user'] = user
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Swap an old password for a new one - you have to prove you know the old first."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_old_password(self, value):
        # the user is on the request, so we can check their current password here
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Your current password is wrong')
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    """Kicks off a reset by email. We don't say whether the email exists, on purpose."""

    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Finishes a reset - takes the uid + token from the email and the new password."""

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
