from rest_framework import permissions


class IsTripOwner(permissions.BasePermission):
    """Only the person who owns the trip gets through."""

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class IsTripOwnerOrCollaborator(permissions.BasePermission):
    """
    Owner can do anything. Collaborators can read the trip (safe methods) but
    not change it - editing stays with the owner.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.owner == request.user or request.user in obj.collaborators.all()
        return obj.owner == request.user


class CanEditItinerary(permissions.BasePermission):
    """
    Owner can always edit. A collaborator can edit only if their role is editor
    or admin - plain viewers can look but not touch.
    """

    def has_object_permission(self, request, view, obj):
        if obj.owner == request.user:
            return True
        collaboration = obj.collaborations.filter(user=request.user).first()
        return bool(collaboration and collaboration.role in ['editor', 'admin'])
