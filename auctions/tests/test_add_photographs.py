"""Tests of the photograph upload use case (FR02)."""

import tempfile

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from auctions.exceptions import NoPhotographs, TooManyPhotographs
from auctions.models import MAX_PHOTOGRAPHS, Photograph
from auctions.services import add_photographs
from auctions.tests.factories import build_image, build_oversized_image, create_auction


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class AddPhotographsTests(TestCase):
    def setUp(self):
        self.auction = create_auction()

    def test_attaches_the_uploaded_images_to_the_auction(self):
        photographs = add_photographs(self.auction, [build_image(), build_image()])

        self.assertEqual(len(photographs), 2)
        self.assertEqual(self.auction.photographs.count(), 2)

    def test_numbers_the_photographs_from_one(self):
        add_photographs(self.auction, [build_image(), build_image(), build_image()])

        orders = list(self.auction.photographs.values_list("display_order", flat=True))
        self.assertEqual(orders, [1, 2, 3])

    def test_a_second_upload_continues_the_display_order(self):
        add_photographs(self.auction, [build_image(), build_image()])

        add_photographs(self.auction, [build_image()])

        orders = list(self.auction.photographs.values_list("display_order", flat=True))
        self.assertEqual(orders, [1, 2, 3])

    def test_rejects_an_upload_without_images(self):
        with self.assertRaises(NoPhotographs):
            add_photographs(self.auction, [])

    def test_rejects_more_photographs_than_the_maximum(self):
        images = [build_image() for _ in range(MAX_PHOTOGRAPHS + 1)]

        with self.assertRaises(TooManyPhotographs):
            add_photographs(self.auction, images)

        self.assertEqual(Photograph.objects.count(), 0)

    def test_rejects_an_upload_that_would_exceed_the_maximum(self):
        add_photographs(self.auction, [build_image() for _ in range(MAX_PHOTOGRAPHS)])

        with self.assertRaises(TooManyPhotographs) as error:
            add_photographs(self.auction, [build_image()])

        self.assertEqual(error.exception.remaining_slots, 0)
        self.assertEqual(Photograph.objects.count(), MAX_PHOTOGRAPHS)

    def test_rejects_a_photograph_heavier_than_the_limit(self):
        with self.assertRaises(ValidationError):
            add_photographs(self.auction, [build_oversized_image()])

        self.assertEqual(Photograph.objects.count(), 0)
