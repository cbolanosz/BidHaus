"""FR30: the service that creates the account of a visitor."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.exceptions import EmailAlreadyRegistered
from accounts.services import register_visitor

User = get_user_model()


class RegisterVisitorTests(TestCase):
    def test_creates_the_account_with_the_data_the_visitor_gave(self):
        user = register_visitor(
            email="laura@bidhaus.co", full_name="Laura Gómez", password="subasta-seguro-2026"
        )

        self.assertEqual(user.email, "laura@bidhaus.co")
        self.assertEqual(user.full_name, "Laura Gómez")
        self.assertEqual(User.objects.count(), 1)

    def test_the_new_account_starts_as_a_bidder(self):
        user = register_visitor(
            email="laura@bidhaus.co", full_name="Laura Gómez", password="subasta-seguro-2026"
        )

        self.assertEqual(user.role, User.Role.BIDDER)
        self.assertFalse(user.is_verified)

    def test_stores_the_password_hashed_and_never_in_clear(self):
        user = register_visitor(
            email="laura@bidhaus.co", full_name="Laura Gómez", password="subasta-seguro-2026"
        )

        self.assertNotEqual(user.password, "subasta-seguro-2026")
        self.assertTrue(user.check_password("subasta-seguro-2026"))

    def test_refuses_an_email_that_is_already_registered(self):
        register_visitor(
            email="laura@bidhaus.co", full_name="Laura Gómez", password="subasta-seguro-2026"
        )

        with self.assertRaises(EmailAlreadyRegistered):
            register_visitor(
                email="laura@bidhaus.co", full_name="Otra Laura", password="otra-clave-2026"
            )

        self.assertEqual(User.objects.count(), 1)

    def test_refuses_an_email_that_differs_only_in_capitalisation(self):
        register_visitor(
            email="laura@bidhaus.co", full_name="Laura Gómez", password="subasta-seguro-2026"
        )

        with self.assertRaises(EmailAlreadyRegistered):
            register_visitor(
                email="LAURA@bidhaus.co", full_name="Otra Laura", password="otra-clave-2026"
            )

        self.assertEqual(User.objects.count(), 1)
