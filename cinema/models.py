from django.db import models
from movies.models import Movie
from django.conf import settings

class Room(models.Model):
    name = models.CharField(max_length=100)
    capacity = models.IntegerField()

    def __str__(self):
        return self.name

class Seat(models.Model):
    room = models.ForeignKey(Room, related_name='seats', on_delete=models.CASCADE)
    row = models.CharField(max_length=5)
    number = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['room', 'row', 'number'], name='unique_seat_per_room')
        ]

    @property
    def label(self):
        return f"{self.row}{self.number}"
    
    def __str__(self):
        return f"{self.label} - {self.room.name}"

class Session(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="sessions")
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    starts_at = models.DateTimeField()
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["room", "starts_at"],
                name="unique_session_per_room_time",
            )
        ]

    def __str__(self):
        return f"{self.movie} - {self.starts_at}"
    
class Ticket(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="tickets")
    seat = models.ForeignKey(Seat, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "seat"],
                name="unique_ticket_per_session_seat",
            )
        ]

    def __str__(self):
        return f"{self.session} - {self.seat} - {self.user}"