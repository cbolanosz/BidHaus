"""Tests of the page where a buyer attaches evidence to a dispute (FR18)."""

import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.tests.factories import create_administrator
from auctions.tests.factories import create_bidder
from escrow.models import MAX_EVIDENCE_FILES, Dispute, Evidence
from escrow.services import attach_evidence, hold_payment, open_dispute
from escrow.tests.factories import build_evidence, create_closed_auction

COMPLAINT = "La cámara llegó con el obturador trabado."


@override_settings(DISPUTE_EVIDENCE_ROOT=tempfile.mkdtemp())
class EvidencePageTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder("Laura Gómez")
        self.auction = create_closed_auction(bidder=self.buyer)
        self.transaction = hold_payment(self.auction)
        self.dispute = open_dispute(self.transaction, self.buyer, COMPLAINT)
        self.url = reverse("escrow:dispute_evidence", args=[self.dispute.pk])
        self.client.force_login(self.buyer)

    def test_sends_a_visitor_who_is_not_logged_in_to_the_login_page(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertRedirects(response, f"{reverse('accounts:log_in')}?next={self.url}")

    def test_shows_the_upload_form_to_the_buyer(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "escrow/evidence_form.html")
        self.assertContains(response, "Pruebas de la disputa")

    def test_attaches_what_the_buyer_uploads(self):
        response = self.client.post(self.url, {"files": [build_evidence()]})

        self.assertRedirects(response, self.url)
        self.assertEqual(Evidence.objects.count(), 1)

    def test_attaches_several_files_at_once(self):
        self.client.post(
            self.url,
            {"files": [build_evidence("una.pdf"), build_evidence("otra.pdf")]},
        )

        self.assertEqual(Evidence.objects.count(), 2)

    def test_names_the_limit_when_the_upload_does_not_fit(self):
        files = [build_evidence(f"{number}.pdf") for number in range(MAX_EVIDENCE_FILES + 1)]

        response = self.client.post(self.url, {"files": files})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"admite {MAX_EVIDENCE_FILES} en total")
        self.assertEqual(Evidence.objects.count(), 0)

    def test_refuses_an_upload_with_no_file(self):
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Elige al menos un archivo")

    def test_closes_the_page_to_the_seller(self):
        self.client.force_login(self.auction.seller)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_answers_404_for_a_dispute_that_does_not_exist(self):
        response = self.client.get(reverse("escrow:dispute_evidence", args=[9999]))

        self.assertEqual(response.status_code, 404)

    def test_says_so_once_the_dispute_is_full(self):
        attach_evidence(
            self.dispute,
            self.buyer,
            [build_evidence(f"{number}.pdf") for number in range(MAX_EVIDENCE_FILES)],
        )

        response = self.client.get(self.url)

        self.assertContains(response, "el máximo de archivos")

    def test_does_not_offer_the_form_once_the_dispute_is_resolved(self):
        Dispute.objects.filter(pk=self.dispute.pk).update(state=Dispute.State.RESOLVED)

        response = self.client.post(self.url, {"files": [build_evidence()]})

        self.assertContains(response, "ya se resolvió")
        self.assertEqual(Evidence.objects.count(), 0)


@override_settings(DISPUTE_EVIDENCE_ROOT=tempfile.mkdtemp())
class WhoCanOpenAnEvidenceFileTests(TestCase):
    """Evidence lives outside MEDIA_ROOT so that this check cannot be skipped."""

    def setUp(self):
        self.buyer = create_bidder("Laura Gómez")
        self.auction = create_closed_auction(bidder=self.buyer)
        self.transaction = hold_payment(self.auction)
        self.dispute = open_dispute(self.transaction, self.buyer, COMPLAINT)
        self.evidence = attach_evidence(self.dispute, self.buyer, [build_evidence()])[0]
        self.url = reverse("escrow:evidence_file", args=[self.evidence.pk])

    def test_the_buyer_opens_it(self):
        self.client.force_login(self.buyer)

        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_the_seller_opens_it(self):
        self.client.force_login(self.auction.seller)

        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_an_administrator_opens_it(self):
        self.client.force_login(create_administrator())

        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_a_stranger_does_not(self):
        self.client.force_login(create_bidder("Alguien más"))

        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_a_visitor_who_is_not_logged_in_does_not(self):
        response = self.client.get(self.url)

        self.assertRedirects(response, f"{reverse('accounts:log_in')}?next={self.url}")

    def test_answers_404_for_a_file_that_does_not_exist(self):
        self.client.force_login(self.buyer)

        response = self.client.get(reverse("escrow:evidence_file", args=[9999]))

        self.assertEqual(response.status_code, 404)

    def test_the_payment_page_lists_the_evidence_for_the_seller(self):
        self.client.force_login(self.auction.seller)

        response = self.client.get(
            reverse("escrow:transaction_detail", args=[self.transaction.pk])
        )

        # Django appends a suffix when a name is taken, so the stored name is
        # the one to look for, not the one that was uploaded.
        self.assertContains(response, self.evidence.filename)
        self.assertContains(response, self.url)

    def test_the_payment_page_offers_the_buyer_to_attach_more(self):
        self.client.force_login(self.buyer)

        response = self.client.get(
            reverse("escrow:transaction_detail", args=[self.transaction.pk])
        )

        self.assertContains(
            response, reverse("escrow:dispute_evidence", args=[self.dispute.pk])
        )

    def test_the_payment_page_does_not_offer_that_to_the_seller(self):
        self.client.force_login(self.auction.seller)

        response = self.client.get(
            reverse("escrow:transaction_detail", args=[self.transaction.pk])
        )

        self.assertNotContains(
            response, reverse("escrow:dispute_evidence", args=[self.dispute.pk])
        )


@override_settings(DISPUTE_EVIDENCE_ROOT=tempfile.mkdtemp())
class TheHeaderLeadsBackToTheDisputeTests(TestCase):
    """A payment in dispute leaves the «to confirm» list, so it needs its own way back."""

    def setUp(self):
        self.buyer = create_bidder("Laura Gómez")
        self.auction = create_closed_auction(bidder=self.buyer)
        self.transaction = hold_payment(self.auction)
        self.catalogue = reverse("auctions:catalogue")
        self.client.force_login(self.buyer)

    def test_offers_nothing_while_there_is_no_dispute(self):
        response = self.client.get(self.catalogue)

        self.assertNotContains(response, "en disputa")

    def test_offers_the_dispute_once_it_is_open(self):
        dispute = open_dispute(self.transaction, self.buyer, COMPLAINT)

        response = self.client.get(self.catalogue)

        self.assertContains(response, "en disputa")
        self.assertContains(
            response, reverse("escrow:dispute_evidence", args=[dispute.pk])
        )

    def test_does_not_offer_it_to_the_seller(self):
        open_dispute(self.transaction, self.buyer, COMPLAINT)
        self.client.force_login(self.auction.seller)

        response = self.client.get(self.catalogue)

        self.assertNotContains(response, "en disputa")

    def test_stops_offering_it_once_it_is_resolved(self):
        dispute = open_dispute(self.transaction, self.buyer, COMPLAINT)
        Dispute.objects.filter(pk=dispute.pk).update(state=Dispute.State.RESOLVED)

        response = self.client.get(self.catalogue)

        self.assertNotContains(response, "en disputa")
