"""FR31: the page where a registered user starts a session."""

from django.test import TestCase
from django.urls import reverse

from accounts.services import register_visitor

PASSWORD = "subasta-seguro-2026"


class LogInViewTests(TestCase):
    def setUp(self):
        self.user = register_visitor(
            email="laura@bidhaus.co", full_name="Laura Gómez", password=PASSWORD
        )
        self.url = reverse("accounts:log_in")

    def post(self, **overrides):
        payload = {"email": "laura@bidhaus.co", "password": PASSWORD}
        payload.update(overrides)
        return self.client.post(self.url, payload)

    def test_shows_the_form(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")

    def test_starts_the_session_and_returns_to_the_catalogue(self):
        response = self.post()

        self.assertRedirects(response, reverse("auctions:catalogue"))
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

    def test_greets_the_user_by_name(self):
        response = self.client.post(
            self.url, {"email": "laura@bidhaus.co", "password": PASSWORD}, follow=True
        )

        self.assertContains(response, "Laura Gómez")

    def test_reports_a_wrong_password_without_starting_a_session(self):
        response = self.post(password="la-clave-equivocada")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "El correo o la contraseña no coinciden.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_reports_an_email_that_is_not_registered(self):
        response = self.post(email="nadie@bidhaus.co")

        self.assertContains(response, "El correo o la contraseña no coinciden.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_returns_to_the_page_that_asked_for_the_session(self):
        destination = reverse("auctions:auction_create")

        response = self.post(next=destination)

        self.assertRedirects(
            response, destination, target_status_code=200, fetch_redirect_response=False
        )

    def test_ignores_a_destination_outside_this_site(self):
        response = self.post(next="https://example.com/robo")

        self.assertRedirects(response, reverse("auctions:catalogue"))
