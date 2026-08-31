"""FR30: the page where a visitor creates an account."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

VALID_SIGN_UP = {
    "full_name": "Laura Gómez",
    "email": "laura@bidhaus.co",
    "password1": "subasta-seguro-2026",
    "password2": "subasta-seguro-2026",
}


class SignUpViewTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:sign_up")

    def test_shows_the_form(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Crear cuenta")

    def test_creates_the_account_and_returns_to_the_catalogue(self):
        response = self.client.post(self.url, VALID_SIGN_UP)

        self.assertRedirects(response, reverse("auctions:catalogue"))
        user = User.objects.get(email="laura@bidhaus.co")
        self.assertEqual(user.full_name, "Laura Gómez")
        self.assertEqual(user.role, User.Role.BIDDER)

    def test_refuses_two_passwords_that_do_not_match(self):
        response = self.client.post(
            self.url, VALID_SIGN_UP | {"password2": "otra-clave-distinta"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "password2", self.mismatch_message())
        self.assertFalse(User.objects.exists())

    def test_refuses_a_password_that_is_too_short(self):
        response = self.client.post(
            self.url, VALID_SIGN_UP | {"password1": "abc", "password2": "abc"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(User.objects.exists())

    def test_refuses_an_email_that_is_already_registered(self):
        self.client.post(self.url, VALID_SIGN_UP)

        response = self.client.post(self.url, VALID_SIGN_UP | {"full_name": "Otra Laura"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"]["email"].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_refuses_an_email_that_differs_only_in_capitalisation(self):
        self.client.post(self.url, VALID_SIGN_UP)

        response = self.client.post(self.url, VALID_SIGN_UP | {"email": "LAURA@bidhaus.co"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"]["email"].errors)
        self.assertEqual(User.objects.count(), 1)

    def mismatch_message(self):
        """The message Django itself raises when the two passwords differ."""
        from django.contrib.auth.forms import SetPasswordMixin

        return SetPasswordMixin.error_messages["password_mismatch"]
