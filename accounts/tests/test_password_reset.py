"""Tests of recovering a forgotten password through an emailed link (FR33)."""

import re

from django.contrib.auth import authenticate, get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from auctions.tests.mailbox import NotificationTestCase
from accounts.services import (
    find_user_for_password_reset,
    password_reset_credentials,
    register_visitor,
    request_password_reset,
    reset_password,
)

OLD_PASSWORD = "cuadernoAzul92"
NEW_PASSWORD = "ventanaVerde74"
User = get_user_model()


def create_account(email="laura@bidhaus.co"):
    return register_visitor(
        email=email, full_name="Laura Gómez", password=OLD_PASSWORD
    )


def link_in(message):
    """The recovery address the email carries."""
    return re.search(r"https?://\S+/password-reset/\S+", message.body).group()


class RequestTheLinkTests(NotificationTestCase):
    def setUp(self):
        self.user = create_account()

    def test_writes_to_the_address_of_the_account(self):
        self.deliver(lambda: request_password_reset(self.user.email))

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_the_email_carries_a_link_that_opens_the_account(self):
        self.deliver(lambda: request_password_reset(self.user.email))

        self.assertIn("/password-reset/", link_in(mail.outbox[0]))

    def test_the_address_is_matched_without_regard_to_case(self):
        self.deliver(lambda: request_password_reset(self.user.email.upper()))

        self.assertEqual(len(mail.outbox), 1)

    def test_writes_to_nobody_when_the_address_is_not_registered(self):
        self.assertIsNone(self.deliver(lambda: request_password_reset("nadie@bidhaus.co")))
        self.assertEqual(mail.outbox, [])

    def test_skips_an_account_with_no_usable_password(self):
        self.user.set_unusable_password()
        self.user.save(update_fields=["password"])

        self.assertIsNone(self.deliver(lambda: request_password_reset(self.user.email)))
        self.assertEqual(mail.outbox, [])


class WhatTheLinkIsWorthTests(TestCase):
    def setUp(self):
        self.user = create_account()
        self.uidb64, self.token = password_reset_credentials(self.user)

    def test_a_fresh_link_opens_its_account(self):
        self.assertEqual(find_user_for_password_reset(self.uidb64, self.token), self.user)

    def test_a_tampered_token_opens_nothing(self):
        self.assertIsNone(find_user_for_password_reset(self.uidb64, "no-es-el-token"))

    def test_a_tampered_address_opens_nothing(self):
        self.assertIsNone(find_user_for_password_reset("bWFs", self.token))

    def test_the_link_of_one_account_does_not_open_another(self):
        other_uidb64, _ = password_reset_credentials(create_account("otra@bidhaus.co"))

        self.assertIsNone(find_user_for_password_reset(other_uidb64, self.token))

    def test_it_stops_working_once_the_password_changes(self):
        """The token is derived from the stored hash, so it is good for one use."""
        reset_password(self.user, NEW_PASSWORD)

        self.assertIsNone(find_user_for_password_reset(self.uidb64, self.token))

    @override_settings(PASSWORD_RESET_TIMEOUT=-1)
    def test_it_stops_working_once_it_is_too_old(self):
        self.assertIsNone(find_user_for_password_reset(self.uidb64, self.token))


class ResetThePasswordTests(TestCase):
    def setUp(self):
        self.user = create_account()

    def test_the_new_password_is_the_one_that_works(self):
        reset_password(self.user, NEW_PASSWORD)

        self.assertIsNotNone(authenticate(username=self.user.email, password=NEW_PASSWORD))

    def test_the_old_password_stops_working(self):
        reset_password(self.user, NEW_PASSWORD)

        self.assertIsNone(authenticate(username=self.user.email, password=OLD_PASSWORD))

    def test_it_is_stored_hashed_like_any_other(self):
        reset_password(self.user, NEW_PASSWORD)

        self.user.refresh_from_db()
        self.assertNotIn(NEW_PASSWORD, self.user.password)
        self.assertTrue(self.user.password.startswith("pbkdf2_sha256$"))


class TheWholeJourneyThroughThePagesTests(NotificationTestCase):
    def setUp(self):
        self.user = create_account()
        self.request_url = reverse("accounts:password_reset_request")

    def ask_for_a_link(self, email=None):
        return self.deliver(
            lambda: self.client.post(
                self.request_url, {"email": email or self.user.email}
            )
        )

    def test_the_login_page_offers_the_way_in(self):
        response = self.client.get(reverse("accounts:log_in"))

        self.assertContains(response, self.request_url)
        self.assertContains(response, "Olvidé mi contraseña")

    def test_asking_leads_to_the_same_page_whether_the_account_exists_or_not(self):
        known = self.ask_for_a_link()
        unknown = self.ask_for_a_link("nadie@bidhaus.co")

        self.assertEqual(known.status_code, unknown.status_code)
        self.assertTemplateUsed(known, "accounts/password_reset_sent.html")
        self.assertTemplateUsed(unknown, "accounts/password_reset_sent.html")
        self.assertContains(unknown, "Si ")

    def test_following_the_link_offers_the_form(self):
        self.ask_for_a_link()

        response = self.client.get(link_in(mail.outbox[0]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Elige una contraseña nueva")

    def test_the_whole_journey_leaves_the_account_with_the_new_password(self):
        self.ask_for_a_link()
        link = link_in(mail.outbox[0])

        response = self.client.post(
            link, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD}
        )

        self.assertRedirects(response, reverse("accounts:log_in"))
        self.assertIsNotNone(authenticate(username=self.user.email, password=NEW_PASSWORD))

    def test_the_link_cannot_be_used_a_second_time(self):
        self.ask_for_a_link()
        link = link_in(mail.outbox[0])
        self.client.post(link, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD})

        response = self.client.get(link)

        self.assertContains(response, "Este enlace ya no sirve")

    def test_refuses_two_passwords_that_differ(self):
        self.ask_for_a_link()

        response = self.client.post(
            link_in(mail.outbox[0]),
            {"new_password1": NEW_PASSWORD, "new_password2": "otraCosa88"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(authenticate(username=self.user.email, password=NEW_PASSWORD))

    def test_refuses_a_password_the_validators_reject(self):
        """The same gate as sign-up: short, common and numeric are turned away."""
        self.ask_for_a_link()

        response = self.client.post(
            link_in(mail.outbox[0]),
            {"new_password1": "12345678", "new_password2": "12345678"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(authenticate(username=self.user.email, password="12345678"))

    def test_an_invented_link_says_so_instead_of_breaking(self):
        response = self.client.get(
            reverse("accounts:password_reset_confirm", args=["bWFs", "no-es-el-token"])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este enlace ya no sirve")
