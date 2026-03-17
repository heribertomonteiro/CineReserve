from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from movies.models import Movie


class MovieApiTests(APITestCase):
	def setUp(self):
		self.movie1 = Movie.objects.create(
			title="Movie 1",
			description="Desc 1",
			duration=100,
			release_date="2026-01-01",
		)
		self.movie2 = Movie.objects.create(
			title="Movie 2",
			description="Desc 2",
			duration=120,
			release_date="2026-01-02",
		)


	def test_list_movies_is_paginated(self):
		url = reverse("movie-list")
		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("count", response.data)
		self.assertIn("results", response.data)
		self.assertGreaterEqual(response.data["count"], 2)

	def test_movie_detail_returns_200(self):
		url = reverse("movie-detail", kwargs={"pk": self.movie1.id})
		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["id"], self.movie1.id)

	def test_movie_create_not_allowed(self):
		url = reverse("movie-list")
		payload = {
			"title": "New Movie",
			"description": "Desc",
			"duration": 90,
			"release_date": "2026-02-10",
		}

		response = self.client.post(url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
