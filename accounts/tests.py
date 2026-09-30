from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from travel_api.validators import validate_image_size, validate_image_type

from .serializers import UserRegistrationSerializer

User = get_user_model()


class ImageValidatorTests(APITestCase):
    """The shared image upload validators used across the models."""

    def test_rejects_non_image_extension(self):
        with self.assertRaises(ValidationError):
            validate_image_type(SimpleUploadedFile('malware.exe', b'x' * 10))

    def test_allows_png(self):
        # should not raise
        validate_image_type(SimpleUploadedFile('photo.png', b'x' * 10))

    def test_rejects_oversized_image(self):
        big = SimpleUploadedFile('big.png', b'x' * (6 * 1024 * 1024))
        with self.assertRaises(ValidationError):
            validate_image_size(big)


class RegistrationSerializerTests(APITestCase):
    """The registration serializer on its own - hashing and password matching."""

    def test_valid_registration_hashes_password(self):
        serializer = UserRegistrationSerializer(data={
            'username': 'z', 'email': 'z@test.local',
            'password': 'Str0ngPass!23', 'password2': 'Str0ngPass!23',
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        # password should be stored hashed, not in plain text
        self.assertTrue(user.check_password('Str0ngPass!23'))
        self.assertNotEqual(user.password, 'Str0ngPass!23')


class RegistrationTests(APITestCase):
    """Signing up new users."""

    def test_register_returns_tokens(self):
        resp = self.client.post('/api/v1/accounts/register/', {
            'username': 'newbie', 'email': 'new@test.local',
            'password': 'Str0ngPass!23', 'password2': 'Str0ngPass!23',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', resp.data['tokens'])
        self.assertTrue(User.objects.filter(username='newbie').exists())

    def test_register_rejects_mismatched_passwords(self):
        resp = self.client.post('/api/v1/accounts/register/', {
            'username': 'x', 'email': 'x@test.local',
            'password': 'Str0ngPass!23', 'password2': 'nope',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class AuthTests(APITestCase):
    """Login, profile access, and changing a password."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='bob', email='bob@test.local', password='Str0ngPass!23'
        )

    def tearDown(self):
        # belt-and-braces cleanup on top of the test transaction rollback
        User.objects.all().delete()

    def test_login_ok(self):
        resp = self.client.post('/api/v1/accounts/login/', {
            'username': 'bob', 'password': 'Str0ngPass!23',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data['tokens'])

    def test_login_wrong_password(self):
        resp = self.client.post('/api/v1/accounts/login/', {
            'username': 'bob', 'password': 'wrong',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_profile_needs_auth(self):
        resp = self.client.get('/api/v1/accounts/profile/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_when_authenticated(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get('/api/v1/accounts/profile/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['username'], 'bob')

    def test_change_password(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post('/api/v1/accounts/password/change/', {
            'old_password': 'Str0ngPass!23', 'new_password': 'N3wPass!456',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('N3wPass!456'))
