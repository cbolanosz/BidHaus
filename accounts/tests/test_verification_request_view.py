"""FR21: the page where a seller sends the document that proves who they are."""

from django.urls import reverse

from accounts.models import VerificationRequest
from accounts.services import submit_verification_request
from accounts.tests.factories import (
    DocumentStoringTestCase,
    build_document,
    create_account,
)


class VerificationRequestViewTests(DocumentStoringTestCase):
    def setUp(self):
        self.seller = create_account()
        self.url = reverse("accounts:verification_request")
        self.client.force_login(self.seller)

    def test_sends_a_visitor_who_is_not_logged_in_to_the_login_page(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertRedirects(response, f"{reverse('accounts:log_in')}?next={self.url}")

    def test_shows_the_form(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/verification_request.html")
        self.assertContains(response, "Enviar documento")

    def test_receives_the_document_and_stays_on_the_page(self):
        response = self.client.post(self.url, {"identity_document": build_document()})

        self.assertRedirects(response, self.url)
        verification_request = VerificationRequest.objects.get()
        self.assertEqual(verification_request.seller, self.seller)
        self.assertTrue(verification_request.is_pending)

    def test_requires_a_document(self):
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este campo es obligatorio.")
        self.assertEqual(VerificationRequest.objects.count(), 0)

    def test_reports_a_file_that_is_not_a_document_or_an_image(self):
        response = self.client.post(
            self.url, {"identity_document": build_document("cedula.exe")}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(VerificationRequest.objects.count(), 0)

    def test_replaces_the_form_with_the_state_while_a_request_waits(self):
        submit_verification_request(self.seller, build_document())

        response = self.client.get(self.url)

        self.assertContains(response, "está esperando respuesta")
        self.assertNotContains(response, "Enviar documento")

    def test_tells_a_verified_seller_there_is_nothing_to_send(self):
        self.seller.is_verified = True
        self.seller.save(update_fields=["is_verified"])

        response = self.client.get(self.url)

        self.assertContains(response, "ya está verificada")
        self.assertNotContains(response, "Enviar documento")

    def test_offers_the_page_from_the_header_until_the_seller_is_verified(self):
        catalogue = reverse("auctions:catalogue")

        self.assertContains(self.client.get(catalogue), "Verifica tu identidad")

        self.seller.is_verified = True
        self.seller.save(update_fields=["is_verified"])

        self.assertNotContains(self.client.get(catalogue), "Verifica tu identidad")
