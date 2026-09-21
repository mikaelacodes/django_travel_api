from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Reuse Django's built-in UserAdmin so we don't lose the nice password handling."""

    list_display = ('username', 'email', 'full_name', 'is_staff', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    # tack our profile fields onto the default edit form
    fieldsets = UserAdmin.fieldsets + (
        ('Travel profile', {
            'fields': ('phone', 'date_of_birth', 'bio', 'profile_picture', 'travel_preferences'),
        }),
    )
