"""Tests of the files a buyer attaches to their dispute (FR18)."""

import tempfile

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from auctions.tests.factories import create_bidder
from escrow.exceptions import (
    DisputeIsResolved,
    NoEvidence,
    NotTheBuyer,
    TooManyEvidenceFiles,
)
from escrow.models import MAX_EVIDENCE_FILES, Dispute, Evidence
from escrow.services import (
    attach_evidence,
    count_free_evidence_slots,
    hold_payment,
    list_evidence,
    open_dispute,
)
from escrow.tests.factories import build_evidence, create_closed_auction

COMPLAINT = "La cámara llegó con el obturador trabado."


@override_settings(DISPUTE_EVIDENCE_ROOT=tempfile.mkdtemp())
class AttachEvidenceTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder("Laura Gómez")
        self.auction = create_closed_auction(bidder=self.buyer)
        self.transaction = hold_payment(self.auction)
        self.dispute = open_dispute(self.transaction, self.buyer, COMPLAINT)

    def test_attaches_the_files_to_the_dispute(self):
        attached = attach_evidence(
            self.dispute, self.buyer, [build_evidence(), build_evidence("guia.pdf")]
        )

        self.assertEqual(len(attached), 2)
        self.assertEqual(list(list_evidence(self.dispute)), attached)

    def test_keeps_the_files_of_each_dispute_apart(self):
        attached = attach_evidence(self.dispute, self.buyer, [build_evidence()])

        self.assertIn(f"disputes/{self.dispute.pk}/", attached[0].file.name)

    def test_a_second_upload_adds_to_the_first(self):
        attach_evidence(self.dispute, self.buyer, [build_evidence("una.pdf")])
        attach_evidence(self.dispute, self.buyer, [build_evidence("otra.pdf")])

        self.assertEqual(list_evidence(self.dispute).count(), 2)

    def test_accepts_exactly_the_maximum(self):
        attach_evidence(
            self.dispute,
            self.buyer,
            [build_evidence(f"{number}.pdf") for number in range(MAX_EVIDENCE_FILES)],
        )

        self.assertEqual(list_evidence(self.dispute).count(), MAX_EVIDENCE_FILES)
        self.assertEqual(count_free_evidence_slots(self.dispute), 0)

    def test_refuses_one_file_over_the_maximum(self):
        files = [build_evidence(f"{number}.pdf") for number in range(MAX_EVIDENCE_FILES + 1)]

        with self.assertRaises(TooManyEvidenceFiles):
            attach_evidence(self.dispute, self.buyer, files)

        self.assertEqual(Evidence.objects.count(), 0)

    def test_says_how_many_still_fit(self):
        attach_evidence(self.dispute, self.buyer, [build_evidence("una.pdf")])

        with self.assertRaises(TooManyEvidenceFiles) as refusal:
            attach_evidence(
                self.dispute,
                self.buyer,
                [build_evidence(f"{number}.pdf") for number in range(MAX_EVIDENCE_FILES)],
            )

        self.assertEqual(refusal.exception.remaining_slots, MAX_EVIDENCE_FILES - 1)

    def test_refuses_an_upload_that_would_overflow_in_a_second_round(self):
        attach_evidence(
            self.dispute,
            self.buyer,
            [build_evidence(f"{number}.pdf") for number in range(MAX_EVIDENCE_FILES)],
        )

        with self.assertRaises(TooManyEvidenceFiles):
            attach_evidence(self.dispute, self.buyer, [build_evidence("sobra.pdf")])

    def test_refuses_anyone_who_is_not_the_buyer(self):
        with self.assertRaises(NotTheBuyer):
            attach_evidence(self.dispute, self.auction.seller, [build_evidence()])

        self.assertEqual(Evidence.objects.count(), 0)

    def test_refuses_an_empty_upload(self):
        with self.assertRaises(NoEvidence):
            attach_evidence(self.dispute, self.buyer, [])

    def test_refuses_a_dispute_already_resolved(self):
        Dispute.objects.filter(pk=self.dispute.pk).update(state=Dispute.State.RESOLVED)
        self.dispute.refresh_from_db()

        with self.assertRaises(DisputeIsResolved):
            attach_evidence(self.dispute, self.buyer, [build_evidence()])

    def test_refuses_a_file_of_a_kind_nobody_can_read(self):
        with self.assertRaises(ValidationError):
            attach_evidence(self.dispute, self.buyer, [build_evidence("virus.exe")])

        self.assertEqual(Evidence.objects.count(), 0)

    def test_counts_the_slots_still_free(self):
        self.assertEqual(count_free_evidence_slots(self.dispute), MAX_EVIDENCE_FILES)

        attach_evidence(self.dispute, self.buyer, [build_evidence()])

        self.assertEqual(count_free_evidence_slots(self.dispute), MAX_EVIDENCE_FILES - 1)
