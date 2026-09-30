import os

from django.core.exceptions import ValidationError

# keep uploads sensible - 5 MB is plenty for a profile pic or a receipt
MAX_IMAGE_SIZE_MB = 5
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.gif']


def validate_image_size(image):
    """Stop someone uploading a massive file."""
    limit = MAX_IMAGE_SIZE_MB * 1024 * 1024
    if image.size > limit:
        raise ValidationError(f'Image must be {MAX_IMAGE_SIZE_MB}MB or smaller.')


def validate_image_type(image):
    """Only let through the common image types, based on the file extension."""
    ext = os.path.splitext(image.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        allowed = ', '.join(ALLOWED_IMAGE_EXTENSIONS)
        raise ValidationError(f'Unsupported file type "{ext}". Allowed types: {allowed}.')
