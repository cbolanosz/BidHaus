"""Tests of how a password is stored (NFR1).

The requirement names the OWASP password storage standard. What it asks for is
checked here and not assumed, so that a change of settings or of Django version
cannot quietly take the project below it.
"""

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import PBKDF2PasswordHasher, identify_hasher
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.services import register_visitor
from accounts.tests.factories import create_administrator

# What OWASP asks of PBKDF2-HMAC-SHA256. Django's own default is far above it,
# and this is the line the project refuses to fall under.
OWASP_MINIMUM_ITERATIONS = 600_000

PASSWORD = "cuadernoAzul92"
User = get_user_model()


def iterations_of(stored):
    """The iteration count written inside the stored hash.

    Not the one the project is configured with right now: an old hash keeps
    the count it was derived with until its owner authenticates again.
    """
    return identify_hasher(stored).decode(stored)["iterations"]


class WeakPBKDF2Hasher(PBKDF2PasswordHasher):
    """A hasher of a single iteration, standing in for an outdated stored hash."""

    iterations = 1


class WhatIsStoredTests(TestCase):
    def setUp(self):
        self.user = register_visitor(
            email="laura@bidhaus.co", full_name="Laura Gómez", password=PASSWORD
        )

    def test_the_password_itself_is_never_stored(self):
        self.user.refresh_from_db()

        self.assertNotIn(PASSWORD, self.user.password)
        self.assertNotEqual(self.user.password, PASSWORD)

    def test_what_is_stored_still_recognises_the_password(self):
        self.assertTrue(self.user.check_password(PASSWORD))
        self.assertFalse(self.user.check_password("otra cosa"))

    def test_it_is_stored_with_the_algorithm_the_standard_names(self):
        self.assertEqual(identify_hasher(self.user.password).algorithm, "pbkdf2_sha256")

    def test_two_people_with_the_same_password_get_different_hashes(self):
        """Each hash carries its own salt, so one cracked gives nothing away."""
        other = register_visitor(
            email="miguel@bidhaus.co", full_name="Miguel Ríos", password=PASSWORD
        )

        self.assertNotEqual(self.user.password, other.password)


class HowTheProjectIsConfiguredTests(TestCase):
    def test_the_iterations_stay_above_what_the_standard_asks(self):
        user = register_visitor(
            email="otra@bidhaus.co", full_name="Otra", password=PASSWORD
        )

        self.assertGreaterEqual(iterations_of(user.password), OWASP_MINIMUM_ITERATIONS)

    def test_no_weaker_algorithm_is_left_able_to_verify(self):
        self.assertEqual(
            settings.PASSWORD_HASHERS,
            ["django.contrib.auth.hashers.PBKDF2PasswordHasher"],
        )

    def test_a_password_shorter_than_the_standard_allows_is_refused(self):
        with self.assertRaises(ValidationError):
            validate_password("corta12")

    def test_a_password_everybody_uses_is_refused(self):
        with self.assertRaises(ValidationError):
            validate_password("password123")

    def test_a_password_of_only_digits_is_refused(self):
        with self.assertRaises(ValidationError):
            validate_password("84736152")


class AnOutdatedHashIsReplacedTests(TestCase):
    """OWASP asks that a stored hash be brought up to date when its owner logs in."""

    def setUp(self):
        self.user = register_visitor(
            email="antigua@bidhaus.co", full_name="Cuenta antigua", password=PASSWORD
        )
        with override_settings(
            PASSWORD_HASHERS=["accounts.tests.test_password_storage.WeakPBKDF2Hasher"]
        ):
            self.user.set_password(PASSWORD)
            self.user.save(update_fields=["password"])

    def test_the_weak_hash_is_what_was_stored(self):
        self.assertEqual(iterations_of(self.user.password), 1)

    def test_authenticating_rewrites_it_with_the_iterations_in_force(self):
        authenticate(username=self.user.email, password=PASSWORD)

        self.user.refresh_from_db()
        self.assertGreaterEqual(iterations_of(self.user.password), OWASP_MINIMUM_ITERATIONS)

    def test_the_person_notices_nothing(self):
        self.assertIsNotNone(authenticate(username=self.user.email, password=PASSWORD))


class WhereAPasswordMustNotAppearTests(TestCase):
    def setUp(self):
        self.user = register_visitor(
            email="laura@bidhaus.co", full_name="Laura Gómez", password=PASSWORD
        )

    def test_the_account_does_not_name_it_when_printed(self):
        self.assertNotIn(PASSWORD, str(self.user))

    def test_the_admin_shows_the_hash_and_not_the_password(self):
        administrator = create_administrator()
        administrator.is_staff = True
        administrator.is_superuser = True
        administrator.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(administrator)

        response = self.client.get(
            reverse("admin:accounts_user_change", args=[self.user.pk])
        )

        self.assertNotContains(response, PASSWORD)
        self.assertContains(response, "algoritmo")

    def test_the_login_form_does_not_send_it_back_on_a_mistake(self):
        """A rejected form must not echo the password into the page it returns."""
        response = self.client.post(
            reverse("accounts:log_in"),
            {"email": self.user.email, "password": PASSWORD + "mal"},
        )

        self.assertNotContains(response, PASSWORD + "mal")
