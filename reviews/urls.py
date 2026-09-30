from django.urls import path

from . import views

app_name = 'reviews'

urlpatterns = [
    # detail/<pk> stays clear of the ReviewViewSet's own /<pk>/ route
    path('detail/<int:pk>/', views.ReviewDetailView.as_view(), name='review-detail'),
]
