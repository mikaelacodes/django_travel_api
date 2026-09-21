from django.contrib import admin

from .models import Destination


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    # quick at-a-glance columns plus filters for the stuff we sort by most
    list_display = ('name', 'country', 'category', 'climate', 'avg_daily_cost', 'is_active')
    list_filter = ('category', 'climate', 'is_active', 'country')
    search_fields = ('name', 'country', 'description')
