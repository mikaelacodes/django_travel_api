from django.urls import path

from . import views

app_name = 'itineraries'

urlpatterns = [
    path('search/', views.trip_search, name='trip-search'),
    path('list-create/', views.ItineraryListCreateView.as_view(), name='list-create'),
    # nested routes hanging off a specific trip
    path('<int:trip_id>/report/', views.generate_trip_report, name='trip-report'),
    path('<int:trip_id>/collaborators/', views.TripCollaborationView.as_view(), name='collaborators'),
    path(
        '<int:trip_id>/collaborators/<int:user_id>/',
        views.TripCollaborationView.as_view(),
        name='collaborator-detail',
    ),
]
