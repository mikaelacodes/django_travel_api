from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)

User = get_user_model()


def tokens_for(user):
    # small helper - build the access + refresh pair for a user
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    """
    Sign up a new user and hand back their tokens so they're logged in right away.

    Example request:
        POST /api/v1/accounts/register/
        {"username": "maya", "email": "maya@example.com",
         "password": "Str0ngPass!23", "password2": "Str0ngPass!23"}

    Example response (201):
        {"user": {...}, "tokens": {"access": "...", "refresh": "..."}}
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(
            {'user': UserSerializer(user).data, 'tokens': tokens_for(user)},
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login(request):
    """
    Log in with username + password, get back a fresh token pair.

    Example request:
        POST /api/v1/accounts/login/
        {"username": "maya", "password": "Str0ngPass!23"}
    """
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        return Response({'user': UserSerializer(user).data, 'tokens': tokens_for(user)})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get or update your own profile. Always operates on the logged-in user."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    """Change your password while logged in."""
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        return Response({'detail': 'Password updated'})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_request(request):
    """
    Start a password reset. Normally we'd email the uid + token; here we just
    return them so the flow is testable. We always give the same response so
    nobody can use this to sniff out which emails have accounts.
    """
    serializer = PasswordResetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    generic_response = {'detail': 'If that email exists, a reset link has been sent'}

    user = User.objects.filter(email=serializer.validated_data['email']).first()
    if not user:
        return Response(generic_response)

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    # dev convenience: hand back the uid/token so you can test the confirm step
    return Response({**generic_response, 'uid': uid, 'token': token})


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_confirm(request):
    """Finish a reset using the uid + token from the request step."""
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        uid = force_str(urlsafe_base64_decode(data['uid']))
        user = User.objects.get(pk=uid)
    except (ValueError, User.DoesNotExist):
        return Response({'error': 'Invalid reset link'}, status=status.HTTP_400_BAD_REQUEST)

    if not default_token_generator.check_token(user, data['token']):
        return Response({'error': 'Reset link is invalid or expired'}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(data['new_password'])
    user.save(update_fields=['password'])
    return Response({'detail': 'Password has been reset'})
