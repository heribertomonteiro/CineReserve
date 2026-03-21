from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from cinema.models import Room, Seat, Session
from movies.models import Movie


class Command(BaseCommand):
    help = "Seed cinema: create Room 'Sala 1', seats A1..J10, sample movies and sessions"

    def handle(self, *args, **options):
        rows = [chr(x) for x in range(ord('A'), ord('J') + 1)]
        seats_per_row = 10
        room_name = "Sala 1"

        # Sample movies to create
        sample_movies = [
            {
                "title": "Filme Teste 1",
                "description": "Filme de exemplo 1",
                "duration": 95,
                "release_date": "2026-03-01",
            },
            {
                "title": "Filme Teste 2",
                "description": "Filme de exemplo 2",
                "duration": 120,
                "release_date": "2026-03-10",
            },
            {
                "title": "Filme Teste 3",
                "description": "Filme de exemplo 3",
                "duration": 110,
                "release_date": "2026-02-20",
            },
        ]

        with transaction.atomic():
            # Room + seats
            room, created = Room.objects.get_or_create(
                name=room_name,
                defaults={"capacity": len(rows) * seats_per_row},
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created room {room.name}"))
            else:
                self.stdout.write(f"Room {room.name} already exists")

            created_count = 0
            for row in rows:
                for n in range(1, seats_per_row + 1):
                    seat, screated = Seat.objects.get_or_create(
                        room=room, row=row, number=n
                    )
                    if screated:
                        created_count += 1

            total = room.seats.count()
            if room.capacity != total:
                room.capacity = total
                room.save(update_fields=["capacity"]) 

            self.stdout.write(self.style.SUCCESS(f"Ensured {total} seats for room {room.name} (created {created_count} new seats)"))

            # Movies
            created_movies = []
            for m in sample_movies:
                movie, mcreated = Movie.objects.get_or_create(
                    title=m["title"],
                    defaults={
                        "description": m["description"],
                        "duration": m["duration"],
                        "release_date": m["release_date"],
                    },
                )
                created_movies.append(movie)
                if mcreated:
                    self.stdout.write(self.style.SUCCESS(f"Created movie {movie.title}"))
                else:
                    self.stdout.write(f"Movie {movie.title} already exists")

            # Sessions: create a couple of sessions for each movie in the room
            now = timezone.now()
            session_times = [
                (1, 20, 0),  # tomorrow 20:00
                (2, 18, 30), # day after tomorrow 18:30
            ]

            created_sessions = 0
            for movie in created_movies:
                for days_offset, hour, minute in session_times:
                    starts_at = (now + timedelta(days=days_offset)).replace(
                        hour=hour, minute=minute, second=0, microsecond=0
                    )
                    session, screated = Session.objects.get_or_create(
                        room=room, starts_at=starts_at, defaults={'movie': movie}
                    )
                    if screated:
                        created_sessions += 1

            self.stdout.write(self.style.SUCCESS(f"Ensured {len(created_movies)} movies and {created_sessions} sessions"))
