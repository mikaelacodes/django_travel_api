from django.contrib import admin

from .models import ActivityLog, Collaboration, DailyPlan, Itinerary


# edit collaborators and days right on the itinerary page - way less clicking
class CollaborationInline(admin.TabularInline):
    model = Collaboration
    extra = 1


class DailyPlanInline(admin.TabularInline):
    model = DailyPlan
    extra = 0


@admin.register(Itinerary)
class ItineraryAdmin(admin.ModelAdmin):
    list_display = ('title', 'destination', 'owner', 'status', 'start_date', 'end_date', 'budget')
    list_filter = ('status', 'is_public', 'destination')
    search_fields = ('title', 'description', 'destination__name', 'owner__username')
    inlines = [CollaborationInline, DailyPlanInline]


@admin.register(DailyPlan)
class DailyPlanAdmin(admin.ModelAdmin):
    list_display = ('itinerary', 'day_number', 'date', 'title')
    list_filter = ('date',)
    search_fields = ('title', 'itinerary__title')


@admin.register(Collaboration)
class CollaborationAdmin(admin.ModelAdmin):
    list_display = ('itinerary', 'user', 'role', 'invited_at')
    list_filter = ('role',)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'object_type', 'object_id', 'itinerary', 'created_at')
    list_filter = ('action', 'object_type', 'created_at')
    search_fields = ('user__username', 'object_type')
    # audit rows are written by signals, so keep them read-only in the admin
    readonly_fields = ('user', 'itinerary', 'action', 'object_type', 'object_id', 'created_at')
