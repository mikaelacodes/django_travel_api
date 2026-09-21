from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'rating', 'destination', 'accommodation', 'activity', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('title', 'content', 'user__username')
