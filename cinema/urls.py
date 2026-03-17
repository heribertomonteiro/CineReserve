from django.urls import path
from . import views

urlpatterns = [
    path('sessions/', views.SessionListCreateAPIView.as_view(), name='session-list-create'),
    path('movies/<int:movie_id>/sessions/', views.MovieSessionsAPIView.as_view(), name='movie-sessions'),
    path('sessions/<int:pk>/seats/', views.SessionSeatMapAPIView.as_view(), name='session-seat-map'),
    path('sessions/<int:session_pk>/seats/<int:seat_id>/lock/', views.SeatLockAPIView.as_view(), name='seat-lock'),
    path('tickets/', views.TicketCreateAPIView.as_view(), name='ticket-create'),
    path('me/tickets/', views.MyTicketsAPIView.as_view(), name='my-tickets'),
]