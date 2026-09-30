from django.urls import path

from . import views

app_name = 'bookings'

urlpatterns = [
    path('bulk-update/', views.bulk_update_bookings, name='bulk-update'),
    # detail/<pk> keeps this CBV clear of the BookingViewSet's own /<pk>/ route
    path('detail/<int:pk>/', views.BookingDetailView.as_view(), name='booking-detail'),
]
