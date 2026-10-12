"""Tests of releasing the funds and of the commission charged (FR16, FR20)."""

from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from auctions.tests.factories import create_bidder, create_seller
from escrow.commission import calculate_commission
from escrow.exceptions import TransactionIsNotHeld
from escrow.models import EscrowTransaction
from escrow.services import confirm_reception, hold_payment, release_funds
from escrow.tests.factories import create_closed_auction


def retained_payment(amount="400000", seller=None, bidder=None):
    """A closed auction whose payment is already in escrow."""
    return hold_payment(
        create_closed_auction(amount=amount, seller=seller, bidder=bidder)
    )


@override_settings(COMMISSION_PERCENTAGE=Decimal("5"))
class CalculateCommissionTests(TestCase):
    def test_takes_the_configured_percentage(self):
        self.assertEqual(calculate_commission(Decimal("400000.00")), Decimal("20000.00"))

    def test_rounds_to_the_cent(self):
        self.assertEqual(calculate_commission(Decimal("333.33")), Decimal("16.67"))

    @override_settings(COMMISSION_PERCENTAGE=Decimal("0"))
    def test_a_platform_that_charges_nothing_takes_nothing(self):
        self.assertEqual(calculate_commission(Decimal("400000.00")), Decimal("0.00"))

    @override_settings(COMMISSION_PERCENTAGE=Decimal("12.5"))
    def test_accepts_a_percentage_with_decimals(self):
        self.assertEqual(calculate_commission(Decimal("400000.00")), Decimal("50000.00"))


@override_settings(COMMISSION_PERCENTAGE=Decimal("5"))
class ReleaseFundsTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder()
        self.seller = create_seller()
        self.transaction = retained_payment(
            amount="400000", seller=self.seller, bidder=self.buyer
        )

    def test_marks_the_money_as_released(self):
        release_funds(self.transaction, actor=self.buyer)

        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.state, EscrowTransaction.State.RELEASED)

    def test_charges_the_commission_when_it_releases(self):
        release_funds(self.transaction, actor=self.buyer)

        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.commission, Decimal("20000.00"))

    def test_the_seller_receives_the_amount_minus_the_commission(self):
        release_funds(self.transaction, actor=self.buyer)

        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.payout, Decimal("380000.00"))

    def test_the_commission_and_the_payout_add_up_to_the_amount(self):
        released = release_funds(self.transaction, actor=self.buyer)

        self.assertEqual(released.commission + released.payout, released.amount)

    def test_records_the_transition_with_its_actor(self):
        release_funds(self.transaction, actor=self.buyer)

        last_change = self.transaction.state_changes.last()
        self.assertEqual(last_change.previous_state, EscrowTransaction.State.HELD)
        self.assertEqual(last_change.new_state, EscrowTransaction.State.RELEASED)
        self.assertEqual(last_change.actor, self.buyer)

    def test_refuses_to_release_what_is_no_longer_retained(self):
        release_funds(self.transaction, actor=self.buyer)

        with self.assertRaises(TransactionIsNotHeld):
            release_funds(self.transaction, actor=self.buyer)

    def test_a_settled_sale_keeps_the_commission_it_was_charged(self):
        """Raising the percentage later must not rewrite what was already paid."""
        release_funds(self.transaction, actor=self.buyer)

        with override_settings(COMMISSION_PERCENTAGE=Decimal("30")):
            self.transaction.refresh_from_db()
            self.assertEqual(self.transaction.commission, Decimal("20000.00"))
            self.assertEqual(self.transaction.payout, Decimal("380000.00"))


@override_settings(COMMISSION_PERCENTAGE=Decimal("5"))
class WhatTheSellerIsToldBeforeTheReleaseTests(TestCase):
    def setUp(self):
        self.transaction = retained_payment(amount="400000")

    def test_announces_the_commission_the_sale_will_carry(self):
        self.assertEqual(self.transaction.commission_due, Decimal("20000.00"))

    def test_announces_what_the_seller_will_receive(self):
        self.assertEqual(self.transaction.payout, Decimal("380000.00"))

    def test_nothing_is_charged_until_the_money_moves(self):
        self.assertEqual(self.transaction.commission, Decimal("0.00"))


@override_settings(COMMISSION_PERCENTAGE=Decimal("5"))
class ConfirmingReleasesTheFundsTests(TestCase):
    """FR15 is what triggers FR16: confirming is the only way money moves."""

    def setUp(self):
        self.buyer = create_bidder()
        self.seller = create_seller()
        self.transaction = retained_payment(
            amount="400000", seller=self.seller, bidder=self.buyer
        )

    def test_confirming_charges_the_commission(self):
        confirm_reception(self.transaction, self.buyer)

        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.commission, Decimal("20000.00"))
        self.assertEqual(self.transaction.payout, Decimal("380000.00"))


@override_settings(COMMISSION_PERCENTAGE=Decimal("5"))
class TheBreakdownIsOnThePageTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder()
        self.seller = create_seller()
        self.transaction = retained_payment(
            amount="400000", seller=self.seller, bidder=self.buyer
        )
        self.url = reverse("escrow:transaction_detail", args=[self.transaction.pk])

    def test_the_seller_sees_what_they_will_receive(self):
        self.client.force_login(self.seller)

        response = self.client.get(self.url)

        self.assertContains(response, "Comisión de BidHaus")
        self.assertContains(response, "380.000")

    def test_the_buyer_is_not_shown_what_the_platform_charges(self):
        """The buyer pays their bid; what BidHaus charges is between it and the seller."""
        self.client.force_login(self.buyer)

        response = self.client.get(self.url)

        self.assertContains(response, "400.000")
        self.assertNotContains(response, "Comisión de BidHaus")
        self.assertNotContains(response, "380.000")

    def test_an_administrator_is_shown_the_breakdown(self):
        from accounts.tests.factories import create_administrator

        self.client.force_login(create_administrator())

        response = self.client.get(self.url)

        self.assertContains(response, "Comisión de BidHaus")

    def test_after_the_release_it_reads_in_the_past(self):
        self.client.force_login(self.seller)
        confirm_reception(self.transaction, self.buyer)

        response = self.client.get(self.url)

        self.assertContains(response, "Recibió el vendedor")
