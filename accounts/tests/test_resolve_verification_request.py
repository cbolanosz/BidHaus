"""FR23: the services an administrator decides a verification request with."""

from pathlib import Path

from django.contrib.auth import get_user_model

from accounts.exceptions import NotAnAdministrator, VerificationAlreadyResolved
from accounts.models import VerificationRequest
from accounts.services import (
    approve_verification_request,
    reject_verification_request,
    submit_verification_request,
)
from accounts.tests.factories import (
    DocumentStoringTestCase,
    build_document,
    create_account,
    create_administrator,
)

User = get_user_model()


class ApproveVerificationRequestTests(DocumentStoringTestCase):
    def setUp(self):
        self.seller = create_account()
        self.administrator = create_administrator()
        self.request = submit_verification_request(self.seller, build_document())

    def approve(self):
        return approve_verification_request(self.request, self.administrator)

    def test_marks_the_request_as_approved(self):
        self.approve()

        self.request.refresh_from_db()
        self.assertEqual(self.request.state, VerificationRequest.State.APPROVED)
        self.assertFalse(self.request.is_pending)

    def test_grants_the_seller_role_and_the_badge(self):
        self.approve()

        self.seller.refresh_from_db()
        self.assertEqual(self.seller.role, User.Role.SELLER)
        self.assertTrue(self.seller.is_verified)

    def test_records_who_decided_and_when(self):
        self.approve()

        self.request.refresh_from_db()
        self.assertEqual(self.request.resolved_by, self.administrator)
        self.assertIsNotNone(self.request.resolved_at)

    def test_destroys_the_identity_document(self):
        stored_path = self.request.identity_document.path

        self.approve()

        self.request.refresh_from_db()
        self.assertFalse(self.request.identity_document)
        self.assertFalse(Path(stored_path).exists())

    def test_refuses_a_user_who_is_not_an_administrator(self):
        with self.assertRaises(NotAnAdministrator):
            approve_verification_request(self.request, create_account())

        self.seller.refresh_from_db()
        self.assertEqual(self.seller.role, User.Role.BIDDER)

    def test_refuses_to_decide_twice(self):
        self.approve()

        with self.assertRaises(VerificationAlreadyResolved):
            self.approve()

    def test_lets_the_seller_publish_afterwards(self):
        """The gap FR23 closes: an approved request and an account that agrees."""
        self.approve()

        self.seller.refresh_from_db()
        self.assertEqual(self.seller.role, User.Role.SELLER)


class RejectVerificationRequestTests(DocumentStoringTestCase):
    def setUp(self):
        self.seller = create_account()
        self.administrator = create_administrator()
        self.request = submit_verification_request(self.seller, build_document())

    def test_marks_the_request_as_rejected(self):
        reject_verification_request(self.request, self.administrator)

        self.request.refresh_from_db()
        self.assertEqual(self.request.state, VerificationRequest.State.REJECTED)

    def test_leaves_the_account_as_it_was(self):
        reject_verification_request(self.request, self.administrator)

        self.seller.refresh_from_db()
        self.assertEqual(self.seller.role, User.Role.BIDDER)
        self.assertFalse(self.seller.is_verified)

    def test_destroys_the_identity_document_too(self):
        reject_verification_request(self.request, self.administrator)

        self.request.refresh_from_db()
        self.assertFalse(self.request.identity_document)

    def test_lets_the_seller_send_a_new_document(self):
        reject_verification_request(self.request, self.administrator)

        submit_verification_request(self.seller, build_document())

        self.assertEqual(VerificationRequest.objects.count(), 2)

    def test_refuses_a_user_who_is_not_an_administrator(self):
        with self.assertRaises(NotAnAdministrator):
            reject_verification_request(self.request, create_account())
