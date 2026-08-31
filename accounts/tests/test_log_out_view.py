"""FR32: ending the session of a user who is logged in."""

from django.test import TestCase
from django.urls import reverse

from accounts.services import register_visitor

PASSWORD = "subasta-seguro-2026"


class LogOutViewTests(TestCase):
    def setUp(self):
        self.user = register_visitor(
            email="laura@bidhaus.co", full_name="Laura Gómez", password=PASSWORD
        )
        self.url = reverse("accounts:log_out")
        self.client.force_login(self.user)

    def test_ends_the_session_and_returns_to_the_catalogue(self):
        response = self.client.post(self.url)

        self.assertRedirects(response, reverse("auctions:catalogue"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_offers_the_exit_only_while_there_is_a_session(self):
        catalogue = reverse("auctions:catalogue")

        self.assertContains(self.client.get(catalogue), "Cerrar sesión")

        self.client.post(self.url)

        self.assertNotContains(self.client.get(catalogue), "Cerrar sesión")

    def test_refuses_to_close_the_session_through_a_link(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_sends_a_visitor_who_is_not_logged_in_to_the_login_page(self):
        self.client.logout()

        response = self.client.post(self.url)

        self.assertRedirects(response, f"{reverse('accounts:log_in')}?next={self.url}")

    def test_the_pages_that_need_a_session_stop_answering_afterwards(self):
        publish = reverse("auctions:auction_create")

        self.client.post(self.url)

        response = self.client.get(publish)

        self.assertRedirects(response, f"{reverse('accounts:log_in')}?next={publish}")
