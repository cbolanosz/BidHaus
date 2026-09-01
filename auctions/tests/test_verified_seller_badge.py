"""FR22: the detail page tells a bidder whether the seller is verified."""

from django.test import TestCase
from django.urls import reverse

from auctions.tests.factories import create_auction, create_bid, create_seller

BADGE = "Verificado"


class VerifiedSellerBadgeTests(TestCase):
    def setUp(self):
        self.seller = create_seller()
        self.auction = create_auction(seller=self.seller)
        self.url = reverse("auctions:auction_detail", args=[self.auction.pk])

    def verify_the_seller(self):
        self.seller.is_verified = True
        self.seller.save(update_fields=["is_verified"])

    def test_shows_the_badge_on_the_auction_of_a_verified_seller(self):
        self.verify_the_seller()

        response = self.client.get(self.url)

        self.assertContains(response, BADGE)

    def test_hides_the_badge_while_the_seller_is_not_verified(self):
        response = self.client.get(self.url)

        self.assertNotContains(response, BADGE)

    def test_shows_the_badge_on_an_auction_that_already_closed(self):
        self.verify_the_seller()
        create_bid(self.auction, "300000")

        response = self.client.get(self.url)

        self.assertContains(response, BADGE)

    def test_reads_the_verification_without_an_extra_query(self):
        """The seller already travels with the auction, so the badge costs nothing."""
        self.verify_the_seller()

        with self.assertNumQueries(3):
            self.client.get(self.url)
