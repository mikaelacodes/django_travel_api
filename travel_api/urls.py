"""
Top-level URL config. Everything API lives under /api/v1/. ViewSets are wired
up through a DefaultRouter; the function/class views live in each app's own
urls.py, included just above the router so their specific paths win.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter

from bookings.views import (
    AccommodationViewSet,
    ActivityViewSet,
    BookingViewSet,
)
from budgets.views import BudgetViewSet, ExpenseViewSet, TripAnalyticsViewSet
from destinations.views import DestinationViewSet
from itineraries.views import ActivityLogViewSet, ItineraryViewSet
from reviews.views import ReviewViewSet

router = DefaultRouter()
router.register(r'itineraries', ItineraryViewSet, basename='itinerary')
router.register(r'destinations', DestinationViewSet, basename='destination')
router.register(r'accommodations', AccommodationViewSet, basename='accommodation')
router.register(r'activities', ActivityViewSet, basename='activity')
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'budgets', BudgetViewSet, basename='budget')
router.register(r'analytics', TripAnalyticsViewSet, basename='analytics')
router.register(r'activity-logs', ActivityLogViewSet, basename='activity-log')

urlpatterns = [
    path('admin/', admin.site.urls),

    # API docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # App-specific routes go before the router so a path like /itineraries/search/
    # isn't mistaken for /itineraries/<pk>/
    path('api/v1/accounts/', include('accounts.urls')),
    path('api/v1/destinations/', include('destinations.urls')),
    path('api/v1/itineraries/', include('itineraries.urls')),
    path('api/v1/bookings/', include('bookings.urls')),
    path('api/v1/reviews/', include('reviews.urls')),
    path('api/v1/budgets/', include('budgets.urls')),

    # ViewSet routes
    path('api/v1/', include(router.urls)),
]

# serve uploaded media in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
