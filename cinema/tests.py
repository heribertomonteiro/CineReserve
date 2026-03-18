from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APITestCase

from cinema.cache_utils import movie_sessions_cache_key, session_seat_map_cache_key
from cinema.models import Room, Seat, Session, Ticket
from movies.models import Movie


class CinemaApiTests(APITestCase):
	def setUp(self):
		cache.clear()
		user_model = get_user_model()
		self.user = user_model.objects.create_user(
			username="user1", email="user1@test.com", password="12345678"
		)
		self.other_user = user_model.objects.create_user(
			username="user2", email="user2@test.com", password="12345678"
		)

		self.movie = Movie.objects.create(
			title="Filme Teste",
			description="Desc",
			duration=120,
			release_date="2026-03-17",
		)
		self.room = Room.objects.create(name="Sala Teste", capacity=10)
		self.seat = Seat.objects.create(room=self.room, row="A", number=1)
		self.session = Session.objects.create(
			movie=self.movie,
			room=self.room,
			starts_at="2026-03-20T20:00:00Z",
		)

	def _lock_key(self):
		return f"lock:session:{self.session.id}:seat:{self.seat.id}"

	def _seat_map_cache_key(self):
		url = reverse("session-seat-map", kwargs={"pk": self.session.id})
		return session_seat_map_cache_key(self.session.id, url)

	def test_seat_map_returns_available(self):
		url = reverse("session-seat-map", kwargs={"pk": self.session.id})
		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		seat_payload = next(s for s in response.data["seats"] if s["id"] == self.seat.id)
		self.assertEqual(seat_payload["status"], "available")

	def test_seat_map_returns_reserved(self):
		cache.set(self._lock_key(), str(self.user.id), timeout=600)
		url = reverse("session-seat-map", kwargs={"pk": self.session.id})

		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		seat_payload = next(s for s in response.data["seats"] if s["id"] == self.seat.id)
		self.assertEqual(seat_payload["status"], "reserved")

	def test_seat_map_returns_purchased(self):
		Ticket.objects.create(user=self.user, session=self.session, seat=self.seat)
		url = reverse("session-seat-map", kwargs={"pk": self.session.id})

		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		seat_payload = next(s for s in response.data["seats"] if s["id"] == self.seat.id)
		self.assertEqual(seat_payload["status"], "purchased")

	def test_lock_and_unlock_flow(self):
		self.client.force_authenticate(user=self.user)
		lock_url = reverse(
			"seat-lock", kwargs={"session_pk": self.session.id, "seat_id": self.seat.id}
		)

		lock_response = self.client.post(lock_url, data={}, format="json")
		self.assertEqual(lock_response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(lock_response.data["status"], "reserved")

		unlock_response = self.client.delete(lock_url)
		self.assertEqual(unlock_response.status_code, status.HTTP_204_NO_CONTENT)
		self.assertIsNone(cache.get(self._lock_key()))

	def test_checkout_success(self):
		cache.set(self._lock_key(), str(self.user.id), timeout=600)
		self.client.force_authenticate(user=self.user)
		checkout_url = reverse("ticket-create")

		response = self.client.post(
			checkout_url,
			{"session_id": self.session.id, "seat_id": self.seat.id},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertTrue(
			Ticket.objects.filter(session=self.session, seat=self.seat, user=self.user).exists()
		)
		self.assertIsNone(cache.get(self._lock_key()))

	@patch("cinema.views.send_ticket_confirmation_email.delay")
	def test_checkout_enqueues_confirmation_email(self, delay_mock):
		cache.set(self._lock_key(), str(self.user.id), timeout=600)
		self.client.force_authenticate(user=self.user)
		checkout_url = reverse("ticket-create")

		with self.captureOnCommitCallbacks(execute=True):
			response = self.client.post(
				checkout_url,
				{"session_id": self.session.id, "seat_id": self.seat.id},
				format="json",
			)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		delay_mock.assert_called_once_with(response.data["ticket_id"])

	def test_checkout_fails_without_reservation(self):
		self.client.force_authenticate(user=self.user)
		checkout_url = reverse("ticket-create")

		response = self.client.post(
			checkout_url,
			{"session_id": self.session.id, "seat_id": self.seat.id},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_checkout_fails_if_reservation_owned_by_another_user(self):
		cache.set(self._lock_key(), str(self.other_user.id), timeout=600)
		self.client.force_authenticate(user=self.user)
		checkout_url = reverse("ticket-create")

		response = self.client.post(
			checkout_url,
			{"session_id": self.session.id, "seat_id": self.seat.id},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_checkout_conflict_when_already_purchased(self):
		Ticket.objects.create(user=self.other_user, session=self.session, seat=self.seat)
		cache.set(self._lock_key(), str(self.user.id), timeout=600)
		self.client.force_authenticate(user=self.user)
		checkout_url = reverse("ticket-create")

		response = self.client.post(
			checkout_url,
			{"session_id": self.session.id, "seat_id": self.seat.id},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

	def test_movie_sessions_cache_invalidated_on_session_create(self):
		url = reverse("movie-sessions", kwargs={"movie_id": self.movie.id})

		first_response = self.client.get(url)
		self.assertEqual(first_response.status_code, status.HTTP_200_OK)

		cache_key = movie_sessions_cache_key(self.movie.id, url)
		self.assertIsNotNone(cache.get(cache_key))

		Session.objects.create(
			movie=self.movie,
			room=self.room,
			starts_at="2026-03-21T20:00:00Z",
		)

		self.assertIsNone(cache.get(cache_key))

	def test_movie_sessions_cache_invalidated_on_session_update(self):
		url = reverse("movie-sessions", kwargs={"movie_id": self.movie.id})

		first_response = self.client.get(url)
		self.assertEqual(first_response.status_code, status.HTTP_200_OK)

		cache_key = movie_sessions_cache_key(self.movie.id, url)
		self.assertIsNotNone(cache.get(cache_key))

		self.session.starts_at = "2026-03-22T20:00:00Z"
		self.session.save(update_fields=["starts_at"])

		self.assertIsNone(cache.get(cache_key))

	def test_seat_map_cache_invalidated_on_lock(self):
		seat_map_url = reverse("session-seat-map", kwargs={"pk": self.session.id})
		first_response = self.client.get(seat_map_url)
		self.assertEqual(first_response.status_code, status.HTTP_200_OK)

		cache_key = self._seat_map_cache_key()
		self.assertIsNotNone(cache.get(cache_key))

		self.client.force_authenticate(user=self.user)
		lock_url = reverse(
			"seat-lock", kwargs={"session_pk": self.session.id, "seat_id": self.seat.id}
		)
		lock_response = self.client.post(lock_url, data={}, format="json")
		self.assertEqual(lock_response.status_code, status.HTTP_201_CREATED)

		self.assertIsNone(cache.get(cache_key))

	def test_seat_map_cache_invalidated_on_checkout(self):
		seat_map_url = reverse("session-seat-map", kwargs={"pk": self.session.id})
		first_response = self.client.get(seat_map_url)
		self.assertEqual(first_response.status_code, status.HTTP_200_OK)

		cache_key = self._seat_map_cache_key()
		self.assertIsNotNone(cache.get(cache_key))

		cache.set(self._lock_key(), str(self.user.id), timeout=600)
		self.client.force_authenticate(user=self.user)
		checkout_url = reverse("ticket-create")
		checkout_response = self.client.post(
			checkout_url,
			{"session_id": self.session.id, "seat_id": self.seat.id},
			format="json",
		)
		self.assertEqual(checkout_response.status_code, status.HTTP_201_CREATED)

		self.assertIsNone(cache.get(cache_key))

	def test_seat_map_cache_invalidated_on_ticket_delete(self):
		# Create a ticket, then populate the seat-map cache, then delete the ticket
		ticket = Ticket.objects.create(user=self.user, session=self.session, seat=self.seat)

		seat_map_url = reverse("session-seat-map", kwargs={"pk": self.session.id})
		first_response = self.client.get(seat_map_url)
		self.assertEqual(first_response.status_code, status.HTTP_200_OK)

		cache_key = self._seat_map_cache_key()
		self.assertIsNotNone(cache.get(cache_key))

		# Delete ticket -> should invalidate
		ticket.delete()
		self.assertIsNone(cache.get(cache_key))

	def test_my_tickets_default_scope_returns_all(self):
		past_session = Session.objects.create(
			movie=self.movie,
			room=self.room,
			starts_at=timezone.now() - timedelta(days=1),
		)
		future_session = Session.objects.create(
			movie=self.movie,
			room=self.room,
			starts_at=timezone.now() + timedelta(days=1),
		)
		past_seat = Seat.objects.create(room=self.room, row="B", number=1)
		future_seat = Seat.objects.create(room=self.room, row="B", number=2)

		Ticket.objects.create(user=self.user, session=past_session, seat=past_seat)
		Ticket.objects.create(user=self.user, session=future_session, seat=future_seat)

		self.client.force_authenticate(user=self.user)
		url = reverse("my-tickets")
		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["count"], 2)

	def test_my_tickets_scope_active_filters_future(self):
		past_session = Session.objects.create(
			movie=self.movie,
			room=self.room,
			starts_at=timezone.now() - timedelta(days=1),
		)
		future_session = Session.objects.create(
			movie=self.movie,
			room=self.room,
			starts_at=timezone.now() + timedelta(days=1),
		)
		past_seat = Seat.objects.create(room=self.room, row="C", number=1)
		future_seat = Seat.objects.create(room=self.room, row="C", number=2)

		Ticket.objects.create(user=self.user, session=past_session, seat=past_seat)
		Ticket.objects.create(user=self.user, session=future_session, seat=future_seat)

		self.client.force_authenticate(user=self.user)
		url = reverse("my-tickets")
		response = self.client.get(url, {"scope": "active"})

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["count"], 1)

	def test_my_tickets_scope_history_filters_past(self):
		past_session = Session.objects.create(
			movie=self.movie,
			room=self.room,
			starts_at=timezone.now() - timedelta(days=1),
		)
		future_session = Session.objects.create(
			movie=self.movie,
			room=self.room,
			starts_at=timezone.now() + timedelta(days=1),
		)
		past_seat = Seat.objects.create(room=self.room, row="D", number=1)
		future_seat = Seat.objects.create(room=self.room, row="D", number=2)

		Ticket.objects.create(user=self.user, session=past_session, seat=past_seat)
		Ticket.objects.create(user=self.user, session=future_session, seat=future_seat)

		self.client.force_authenticate(user=self.user)
		url = reverse("my-tickets")
		response = self.client.get(url, {"scope": "history"})

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["count"], 1)

	@patch("cinema.tasks.send_mail")
	def test_send_ticket_confirmation_email_sends_expected_payload(self, send_mail_mock):
		ticket = Ticket.objects.create(user=self.user, session=self.session, seat=self.seat)

		from cinema.tasks import send_ticket_confirmation_email

		send_ticket_confirmation_email.run(ticket.id)

		send_mail_mock.assert_called_once()
		kwargs = send_mail_mock.call_args.kwargs
		self.assertEqual(kwargs["recipient_list"], [self.user.email])
		self.assertEqual(kwargs["from_email"], "noreply@cinereserve.local")
		self.assertIn("Filme Teste", kwargs["message"])
		self.assertIn("A1", kwargs["message"])
