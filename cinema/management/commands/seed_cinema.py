from django.core.management.base import BaseCommand
from django.db import transaction
from cinema.models import Room, Seat


class Command(BaseCommand):
    help = "Seed cinema: create Room 'Sala 1' and seats A1..J10"

    def handle(self, *args, **options):
        rows = [chr(x) for x in range(ord('A'), ord('J') + 1)]
        seats_per_row = 10
        room_name = "Sala 1"

        with transaction.atomic():
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
