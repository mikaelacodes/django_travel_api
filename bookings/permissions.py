from rest_framework import permissions


class IsBookingOwner(permissions.BasePermission):
    """Only the person who made the booking can view or change it."""

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
