from django.contrib import admin

from .models import Collaboration, DailyPlan, Itinerary


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
