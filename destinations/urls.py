from django.urls import path

from reviews.views import DestinationReviewsView

from . import views

app_name = 'destinations'

urlpatterns = [
    path('search/', views.DestinationSearchView.as_view(), name='search'),
    path('wishlist/', views.destination_wishlist, name='wishlist'),
    # <str:country> shows off a string path converter
    path('country/<str:country>/', views.DestinationsByCountryView.as_view(), name='by-country'),
    # nested route: reviews that belong to one destination
    path('<int:destination_id>/reviews/', DestinationReviewsView.as_view(), name='reviews'),
]
