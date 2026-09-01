"""FR21: the service that receives an identity document."""

from django.core.exceptions import ValidationError

from accounts.exceptions import AlreadyVerified, VerificationAlreadyPending
from accounts.models import VerificationRequest
from accounts.services import submit_verification_request
from accounts.tests.factories import (
    DocumentStoringTestCase,
    build_document,
    build_oversized_document,
    create_account,
)


class SubmitVerificationRequestTests(DocumentStoringTestCase):
    def setUp(self):
        self.seller = create_account()

    def test_stores_the_request_waiting_for_a_decision(self):
        verification_request = submit_verification_request(self.seller, build_document())

        self.assertEqual(verification_request.seller, self.seller)
        self.assertEqual(verification_request.state, VerificationRequest.State.PENDING)
        self.assertTrue(verification_request.is_pending)

    def test_stores_the_document_outside_the_public_media_folder(self):
        verification_request = submit_verification_request(self.seller, build_document())

        stored_path = verification_request.identity_document.path
        self.assertIn("private-media", stored_path)
        self.assertNotIn("/media/", stored_path)

    def test_keeps_each_document_in_the_folder_of_its_seller(self):
        verification_request = submit_verification_request(self.seller, build_document())

        self.assertTrue(
            verification_request.identity_document.name.startswith(
                f"verification/{self.seller.pk}/"
            )
        )

    def test_refuses_a_second_request_while_one_is_pending(self):
        submit_verification_request(self.seller, build_document())

        with self.assertRaises(VerificationAlreadyPending):
            submit_verification_request(self.seller, build_document())

        self.assertEqual(VerificationRequest.objects.count(), 1)

    def test_allows_a_new_request_after_one_was_rejected(self):
        first = submit_verification_request(self.seller, build_document())
        first.state = VerificationRequest.State.REJECTED
        first.save(update_fields=["state"])

        submit_verification_request(self.seller, build_document())

        self.assertEqual(VerificationRequest.objects.count(), 2)

    def test_refuses_a_seller_whose_identity_is_already_verified(self):
        self.seller.is_verified = True
        self.seller.save(update_fields=["is_verified"])

        with self.assertRaises(AlreadyVerified):
            submit_verification_request(self.seller, build_document())

        self.assertEqual(VerificationRequest.objects.count(), 0)

    def test_refuses_a_file_that_is_not_a_document_or_an_image(self):
        with self.assertRaises(ValidationError):
            submit_verification_request(self.seller, build_document("cedula.exe"))

        self.assertEqual(VerificationRequest.objects.count(), 0)

    def test_refuses_a_document_heavier_than_the_limit(self):
        with self.assertRaises(ValidationError):
            submit_verification_request(self.seller, build_oversized_document())

        self.assertEqual(VerificationRequest.objects.count(), 0)
