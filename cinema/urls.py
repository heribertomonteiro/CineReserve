from django.urls import path
from .views import SessionSeatMapAPIView

urlpatterns = [
    path('sessions/<int:pk>/seats/', SessionSeatMapAPIView.as_view(), name='session-seat-map'),
]