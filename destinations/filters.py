from django_filters import rest_framework as filters

from .models import Destination


class DestinationFilter(filters.FilterSet):
    """
    Filters for browsing destinations. On top of the plain field matches, we add
    a cost range and a "budget/moderate/luxury" bucket that maps to price bands.
    """

    climate = filters.MultipleChoiceFilter(choices=Destination.ClimateChoices.choices)
    min_cost = filters.NumberFilter(field_name='avg_daily_cost', lookup_expr='gte')
    max_cost = filters.NumberFilter(field_name='avg_daily_cost', lookup_expr='lte')
    budget_range = filters.CharFilter(method='filter_by_budget')

    def filter_by_budget(self, queryset, name, value):
        # translate a friendly word into an actual price band
        if value == 'budget':
            return queryset.filter(avg_daily_cost__lt=100)
        elif value == 'moderate':
            return queryset.filter(avg_daily_cost__gte=100, avg_daily_cost__lt=250)
        elif value == 'luxury':
            return queryset.filter(avg_daily_cost__gte=250)
        return queryset

    class Meta:
        model = Destination
        fields = ['country', 'category', 'climate']
