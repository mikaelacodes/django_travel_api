from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """Anyone can read a review, but only the author can edit or delete it."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user
