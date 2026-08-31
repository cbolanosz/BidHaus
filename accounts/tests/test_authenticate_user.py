"""FR31: the service that checks the credentials of a registered user."""

from django.test import TestCase

from accounts.exceptions import InvalidCredentials
from accounts.services import authenticate_user, register_visitor

PASSWORD = "subasta-seguro-2026"


class AuthenticateUserTests(TestCase):
    def setUp(self):
        self.user = register_visitor(
            email="laura@bidhaus.co", full_name="Laura Gómez", password=PASSWORD
        )

    def test_returns_the_user_whose_credentials_match(self):
        self.assertEqual(authenticate_user("laura@bidhaus.co", PASSWORD), self.user)

    def test_refuses_a_wrong_password(self):
        with self.assertRaises(InvalidCredentials):
            authenticate_user("laura@bidhaus.co", "la-clave-equivocada")

    def test_refuses_an_email_that_is_not_registered(self):
        with self.assertRaises(InvalidCredentials):
            authenticate_user("nadie@bidhaus.co", PASSWORD)

    def test_refuses_an_account_that_is_not_active(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        with self.assertRaises(InvalidCredentials):
            authenticate_user("laura@bidhaus.co", PASSWORD)
