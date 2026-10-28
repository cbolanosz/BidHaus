"""Tests of the list of auctions a user has published (FR12)."""

import tempfile
from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from auctions.models import Auction
from auctions.tests.factories import (
    build_image,
    create_auction,
    create_bid,
    create_bidder,
    create_seller,
)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class MyAuctionsViewTests(TestCase):
    def setUp(self):
        self.seller = create_seller()
        self.url = reverse("auctions:my_auctions")
        self.client.force_login(self.seller)

    def test_sends_a_visitor_who_is_not_logged_in_to_the_login_page(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertRedirects(response, f"{reverse('accounts:log_in')}?next={self.url}")

    def test_lists_the_auctions_of_the_user_in_session(self):
        create_auction(seller=self.seller, title="Cámara Yashica FX-3")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auctions/my_auctions.html")
        self.assertContains(response, "Cámara Yashica FX-3")

    def test_links_each_auction_to_the_seller_detail(self):
        auction = create_auction(
            seller=self.seller, state=Auction.State.PENDING
        )

        response = self.client.get(self.url)

        self.assertContains(
            response,
            reverse("auctions:my_auction_detail", args=[auction.pk]),
        )

    def test_hides_the_auctions_of_another_seller(self):
        create_auction(seller=create_seller(), title="Reloj de otra vendedora")

        response = self.client.get(self.url)

        self.assertNotContains(response, "Reloj de otra vendedora")

    def test_lists_the_closed_auctions_too(self):
        """«All the auctions they have published» includes the ones already closed."""
        create_auction(seller=self.seller, title="Vajilla inglesa", state=Auction.State.CLOSED)

        response = self.client.get(self.url)

        self.assertContains(response, "Vajilla inglesa")

    def test_shows_the_state_of_each_auction(self):
        create_auction(seller=self.seller, state=Auction.State.CLOSED)

        response = self.client.get(self.url)

        self.assertContains(response, "Cerrada")

    def test_names_the_buyer_of_an_auction_that_sold(self):
        auction = create_auction(seller=self.seller, state=Auction.State.CLOSED)
        auction.winning_bid = create_bid(auction, "400000", create_bidder("Laura Gómez"))
        auction.save(update_fields=["winning_bid"])

        response = self.client.get(self.url)

        self.assertContains(response, "Laura Gómez")

    def test_says_so_when_a_closed_auction_got_no_bids(self):
        create_auction(seller=self.seller, state=Auction.State.CLOSED)

        response = self.client.get(self.url)

        self.assertContains(response, "Cerró sin pujas")

    def test_orders_the_auctions_from_the_newest_to_the_oldest(self):
        older = create_auction(seller=self.seller, title="Lote antiguo")
        Auction.objects.filter(pk=older.pk).update(
            published_at=timezone.now() - timedelta(days=3)
        )
        create_auction(seller=self.seller, title="Lote reciente")

        response = self.client.get(self.url)

        body = response.content.decode()
        self.assertLess(body.index("Lote reciente"), body.index("Lote antiguo"))

    def test_invites_a_user_with_nothing_published_to_publish(self):
        response = self.client.get(self.url)

        self.assertContains(response, "Aún no has publicado nada")

    def test_a_bidder_sees_their_own_empty_list(self):
        """Any registered user may open the list; a bidder simply has nothing in it."""
        self.client.force_login(create_bidder())

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aún no has publicado nada")

    def test_fetches_the_whole_list_in_a_fixed_number_of_queries(self):
        """The page must answer within 3 seconds, so it cannot query per auction."""
        from auctions.services import add_photographs

        for index in range(5):
            auction = create_auction(seller=self.seller, title=f"Lote {index}")
            add_photographs(auction, [build_image()])

        # session, user, the payments the header offers, auctions, photographs:
        # five, whatever the list holds.
        with self.assertNumQueries(5):
            self.client.get(self.url)

    def test_offers_the_list_from_the_header(self):
        response = self.client.get(reverse("auctions:catalogue"))

        self.assertContains(response, 'href="/auctions/mine/"')

    def test_shows_a_pending_auction_to_its_owner(self):
        auction = create_auction(
            seller=self.seller,
            title="Solicitud pendiente",
            state=Auction.State.PENDING,
        )

        response = self.client.get(
            reverse("auctions:my_auction_detail", args=[auction.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auctions/my_auction_detail.html")
        self.assertContains(response, "Pendiente de aprobación")
        self.assertContains(response, "está esperando la revisión")

    def test_photograph_form_links_pending_auction_to_private_detail(self):
        auction = create_auction(
            seller=self.seller, state=Auction.State.PENDING
        )

        response = self.client.get(
            reverse("auctions:auction_photographs", args=[auction.pk])
        )

        self.assertContains(
            response,
            reverse("auctions:my_auction_detail", args=[auction.pk]),
        )
        self.assertNotContains(
            response,
            reverse("auctions:auction_detail", args=[auction.pk]),
        )

    def test_does_not_show_another_sellers_auction(self):
        auction = create_auction(
            seller=create_seller(), state=Auction.State.PENDING
        )

        response = self.client.get(
            reverse("auctions:my_auction_detail", args=[auction.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_requires_login_for_the_seller_detail(self):
        auction = create_auction(seller=self.seller)
        self.client.logout()

        response = self.client.get(
            reverse("auctions:my_auction_detail", args=[auction.pk])
        )

        self.assertRedirects(
            response,
            f"{reverse('accounts:log_in')}?next={reverse('auctions:my_auction_detail', args=[auction.pk])}",
        )


class SellerReachesThePaymentTests(TestCase):
    """A sold lot has money behind it, and its page is where the seller finds it."""

    def setUp(self):
        from auctions.tests.factories import create_bid, create_bidder
        from escrow.services import hold_payment

        self.seller = create_seller()
        self.auction = create_auction(seller=self.seller, state=Auction.State.CLOSED)
        self.auction.winning_bid = create_bid(self.auction, "400000", create_bidder())
        self.auction.save(update_fields=["winning_bid"])
        self.transaction = hold_payment(self.auction)
        self.url = reverse("auctions:my_auction_detail", args=[self.auction.pk])
        self.client.force_login(self.seller)

    def test_offers_the_link_to_the_retained_payment(self):
        response = self.client.get(self.url)

        self.assertContains(response, "Ver el pago en custodia")
        self.assertContains(
            response, reverse("escrow:transaction_detail", args=[self.transaction.pk])
        )

    def test_a_lot_with_no_payment_offers_nothing(self):
        auction = create_auction(seller=self.seller, state=Auction.State.CLOSED)

        response = self.client.get(
            reverse("auctions:my_auction_detail", args=[auction.pk])
        )

        self.assertNotContains(response, "Ver el pago en custodia")
