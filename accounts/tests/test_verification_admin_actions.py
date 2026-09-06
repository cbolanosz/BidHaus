"""FR23: the two actions an administrator resolves a request with, from the admin."""

from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import VerificationRequest
from accounts.services import submit_verification_request
from accounts.tests.factories import (
    PASSWORD,
    DocumentStoringTestCase,
    build_document,
    create_account,
    create_administrator,
)

User = get_user_model()


class VerificationAdminActionTests(DocumentStoringTestCase):
    def setUp(self):
        self.administrator = create_administrator()
        self.administrator.is_staff = True
        self.administrator.is_superuser = True
        self.administrator.save(update_fields=["is_staff", "is_superuser"])

        self.seller = create_account()
        self.request = submit_verification_request(self.seller, build_document())

        self.url = reverse("admin:accounts_verificationrequest_changelist")
        self.client.login(email=self.administrator.email, password=PASSWORD)

    def run_action(self, action):
        return self.client.post(
            self.url,
            {"action": action, "_selected_action": [str(self.request.pk)]},
            follow=True,
        )

    def test_approving_grants_the_role_and_the_badge(self):
        response = self.run_action("approve")

        self.assertEqual(response.status_code, 200)
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.role, User.Role.SELLER)
        self.assertTrue(self.seller.is_verified)

    def test_rejecting_leaves_the_account_untouched(self):
        self.run_action("reject")

        self.request.refresh_from_db()
        self.seller.refresh_from_db()
        self.assertEqual(self.request.state, VerificationRequest.State.REJECTED)
        self.assertEqual(self.seller.role, User.Role.BIDDER)

    def test_reports_a_request_that_already_carried_a_decision(self):
        self.run_action("approve")

        response = self.run_action("approve")

        self.assertContains(response, "ya tenía una decisión")

    def test_the_state_cannot_be_edited_by_hand(self):
        """Writing the state directly would approve nothing: the account would not change."""
        change_url = reverse(
            "admin:accounts_verificationrequest_change", args=[self.request.pk]
        )

        response = self.client.get(change_url)

        self.assertNotContains(response, 'name="state"')
