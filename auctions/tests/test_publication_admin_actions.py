"""FR36: administrators resolve auction publication requests from Django Admin."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from analytics.models import TrustScore
from auctions.models import Auction
from auctions.services import reject_auction_publication
from auctions.tests.factories import create_auction

User = get_user_model()


class AuctionPublicationAdminActionTests(TestCase):
    def setUp(self):
        self.administrator = User.objects.create_user(
            email="admin@bidhaus.co",
            password="admin-password",
            full_name="Admin de prueba",
            role=User.Role.ADMINISTRATOR,
            is_staff=True,
            is_superuser=True,
        )
        self.auction = create_auction(state=Auction.State.PENDING)
        self.url = reverse("admin:auctions_auction_changelist")
        self.client.login(email=self.administrator.email, password="admin-password")

    def run_action(self, action):
        return self.client.post(
            self.url,
            {"action": action, "_selected_action": [str(self.auction.pk)]},
            follow=True,
        )

    def test_approving_publishes_and_scores_the_auction(self):
        response = self.run_action("approve")

        self.assertEqual(response.status_code, 200)
        self.auction.refresh_from_db()
        self.assertEqual(self.auction.state, Auction.State.OPEN)
        self.assertEqual(self.auction.resolved_by, self.administrator)
        self.assertIsNotNone(self.auction.resolved_at)
        self.assertTrue(TrustScore.objects.filter(auction=self.auction).exists())

    def test_rejecting_keeps_the_auction_and_records_the_decision(self):
        response = self.run_action("reject")

        self.assertEqual(response.status_code, 200)
        self.auction.refresh_from_db()
        self.assertEqual(self.auction.state, Auction.State.REJECTED)
        self.assertEqual(self.auction.resolved_by, self.administrator)
        self.assertIsNotNone(self.auction.resolved_at)
        self.assertFalse(TrustScore.objects.filter(auction=self.auction).exists())

    def test_an_already_resolved_request_is_reported(self):
        reject_auction_publication(self.auction, self.administrator)

        response = self.run_action("approve")

        self.assertContains(response, "ya tenía una decisión")

    def test_resolution_fields_cannot_be_edited_by_hand(self):
        change_url = reverse("admin:auctions_auction_change", args=[self.auction.pk])

        response = self.client.get(change_url)

        self.assertNotContains(response, 'name="state"')
        self.assertNotContains(response, 'name="resolved_by"')
