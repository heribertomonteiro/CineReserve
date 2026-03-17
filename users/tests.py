from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class UserAuthApiTests(APITestCase):
	def setUp(self):
		user_model = get_user_model()
		self.user = user_model.objects.create_user(
			username="user1",
			email="user1@test.com",
			password="12345678",
		)

	def test_register_creates_user(self):
		url = reverse("register")
		payload = {
			"username": "newuser",
			"email": "newuser@test.com",
			"password": "12345678",
		}

		response = self.client.post(url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertTrue(get_user_model().objects.filter(email="newuser@test.com").exists())

	def test_login_returns_jwt_pair(self):
		url = reverse("token_obtain_pair")
		payload = {
			"username": "user1",
			"password": "12345678",
		}

		response = self.client.post(url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("access", response.data)
		self.assertIn("refresh", response.data)

	def test_refresh_returns_new_access_token(self):
		login_url = reverse("token_obtain_pair")
		login_response = self.client.post(
			login_url,
			{"username": "user1", "password": "12345678"},
			format="json",
		)
		refresh_token = login_response.data["refresh"]

		refresh_url = reverse("token_refresh")
		response = self.client.post(refresh_url, {"refresh": refresh_token}, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("access", response.data)

	def test_protected_endpoint_requires_authentication(self):
		url = reverse("my-tickets")
		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_protected_endpoint_accepts_bearer_token(self):
		login_url = reverse("token_obtain_pair")
		login_response = self.client.post(
			login_url,
			{"username": "user1", "password": "12345678"},
			format="json",
		)
		access_token = login_response.data["access"]

		url = reverse("my-tickets")
		response = self.client.get(url, HTTP_AUTHORIZATION=f"Bearer {access_token}")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("results", response.data)
