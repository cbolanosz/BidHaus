"""Tests of the pages where a participant scores the counterpart (FR24)."""

from django.test import TestCase
from django.urls import reverse

from auctions.tests.factories import create_bidder
from escrow.services import hold_payment
from escrow.tests.factories import create_closed_auction
from reputation.models import Rating
from reputation.services import rate_counterpart
from reputation.tests.factories import create_completed_sale


class SalesToRatePageTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder("Laura Gómez")
        self.sale = create_completed_sale(bidder=self.buyer)
        self.url = reverse("reputation:sales_to_rate")
        self.client.force_login(self.buyer)

    def test_sends_a_visitor_who_is_not_logged_in_to_the_login_page(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertRedirects(response, f"{reverse('accounts:log_in')}?next={self.url}")

    def test_lists_the_sale_and_links_to_its_form(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.sale.auction.title)
        self.assertContains(response, reverse("reputation:rate", args=[self.sale.pk]))

    def test_says_who_the_counterpart_was(self):
        response = self.client.get(self.url)

        self.assertContains(response, f"Le compraste a {self.sale.seller.full_name}")

    def test_says_so_when_there_is_nothing_pending(self):
        rate_counterpart(self.sale, self.buyer, 5)

        response = self.client.get(self.url)

        self.assertContains(response, "Nada por calificar")

    def test_the_header_offers_it_while_something_is_pending(self):
        response = self.client.get(reverse("auctions:catalogue"))

        self.assertContains(response, "por calificar")
        self.assertContains(response, reverse("reputation:rate", args=[self.sale.pk]))

    def test_the_header_stops_offering_it_once_scored(self):
        rate_counterpart(self.sale, self.buyer, 5)

        response = self.client.get(reverse("auctions:catalogue"))

        self.assertNotContains(response, "por calificar")


class RatePageTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder("Laura Gómez")
        self.sale = create_completed_sale(bidder=self.buyer)
        self.url = reverse("reputation:rate", args=[self.sale.pk])
        self.client.force_login(self.buyer)

    def test_names_the_counterpart(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reputation/rate.html")
        self.assertContains(response, f"Califica a {self.sale.seller.full_name}")

    def test_registers_the_score_and_returns_to_the_list(self):
        response = self.client.post(self.url, {"score": "5"})

        self.assertRedirects(response, reverse("reputation:sales_to_rate"))
        self.assertEqual(Rating.objects.get().score, 5)

    def test_refuses_a_submission_with_no_score(self):
        response = self.client.post(self.url, {})

        self.assertContains(response, "Elige cuántas estrellas le das.")
        self.assertEqual(Rating.objects.count(), 0)

    def test_refuses_a_score_outside_the_range(self):
        response = self.client.post(self.url, {"score": "9"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Rating.objects.count(), 0)

    def test_says_so_when_this_side_already_scored(self):
        rate_counterpart(self.sale, self.buyer, 5)

        response = self.client.post(self.url, {"score": "1"})

        self.assertContains(response, "Ya calificaste")
        self.assertEqual(Rating.objects.count(), 1)

    def test_says_so_when_the_sale_is_not_completed(self):
        retained = hold_payment(create_closed_auction(bidder=self.buyer))

        response = self.client.post(
            reverse("reputation:rate", args=[retained.pk]), {"score": "5"}
        )

        self.assertContains(response, "todavía no se completó")
        self.assertEqual(Rating.objects.count(), 0)

    def test_closes_the_page_to_somebody_outside_the_sale(self):
        self.client.force_login(create_bidder("Alguien más"))

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_answers_404_for_a_sale_that_does_not_exist(self):
        response = self.client.get(reverse("reputation:rate", args=[9999]))

        self.assertEqual(response.status_code, 404)
