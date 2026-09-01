"""DBR08: an identity document is readable by the administrator and by nobody else."""

from django.urls import reverse

from accounts.services import submit_verification_request
from accounts.tests.factories import (
    PDF_BYTES,
    DocumentStoringTestCase,
    build_document,
    create_account,
    create_administrator,
)


class IdentityDocumentViewTests(DocumentStoringTestCase):
    def setUp(self):
        self.seller = create_account()
        self.verification_request = submit_verification_request(self.seller, build_document())
        self.url = reverse(
            "accounts:identity_document", args=[self.verification_request.pk]
        )

    def test_hands_the_document_to_an_administrator(self):
        self.client.force_login(create_administrator())

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), PDF_BYTES)

    def test_refuses_another_user(self):
        self.client.force_login(create_account())

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_refuses_even_the_seller_who_sent_it(self):
        self.client.force_login(self.seller)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_sends_a_visitor_who_is_not_logged_in_to_the_login_page(self):
        response = self.client.get(self.url)

        self.assertRedirects(response, f"{reverse('accounts:log_in')}?next={self.url}")

    def test_answers_not_found_once_the_document_is_gone(self):
        self.verification_request.identity_document.delete(save=True)
        self.client.force_login(create_administrator())

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_answers_not_found_for_a_request_that_does_not_exist(self):
        self.client.force_login(create_administrator())

        response = self.client.get(reverse("accounts:identity_document", args=[9999]))

        self.assertEqual(response.status_code, 404)
