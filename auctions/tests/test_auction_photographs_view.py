"""Tests of the photograph page of an auction (FR02)."""

import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from auctions.models import MAX_PHOTOGRAPHS, Photograph
from auctions.services import add_photographs
from auctions.tests.factories import build_image, build_oversized_image, create_auction


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class AuctionPhotographsViewTests(TestCase):
    def setUp(self):
        self.auction = create_auction()
        self.url = reverse("auctions:auction_photographs", args=[self.auction.pk])

    def test_shows_the_upload_form(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auctions/photograph_form.html")

    def test_answers_not_found_for_an_auction_that_does_not_exist(self):
        response = self.client.get(reverse("auctions:auction_photographs", args=[9999]))

        self.assertEqual(response.status_code, 404)

    def test_uploads_the_chosen_images(self):
        response = self.client.post(self.url, {"images": [build_image(), build_image()]})

        self.assertRedirects(response, self.url)
        self.assertEqual(self.auction.photographs.count(), 2)

    def test_requires_at_least_one_image(self):
        response = self.client.post(self.url, {})

        self.assertEqual(Photograph.objects.count(), 0)
        self.assertContains(response, "Este campo es obligatorio.")

    def test_reports_a_photograph_heavier_than_the_limit(self):
        response = self.client.post(self.url, {"images": [build_oversized_image()]})

        self.assertEqual(Photograph.objects.count(), 0)
        self.assertContains(response, "pesa más de 5 MB")

    def test_reports_an_upload_that_exceeds_the_maximum(self):
        images = [build_image() for _ in range(MAX_PHOTOGRAPHS + 1)]

        response = self.client.post(self.url, {"images": images})

        self.assertEqual(Photograph.objects.count(), 0)
        self.assertContains(response, "una subasta admite 8 en total")

    def test_reports_an_upload_to_an_auction_that_is_already_full(self):
        add_photographs(self.auction, [build_image() for _ in range(MAX_PHOTOGRAPHS)])

        response = self.client.post(self.url, {"images": [build_image()]})

        self.assertEqual(Photograph.objects.count(), MAX_PHOTOGRAPHS)
        self.assertContains(response, "Solo caben 0 fotografías más")

    def test_hides_the_form_once_the_auction_is_full(self):
        add_photographs(self.auction, [build_image() for _ in range(MAX_PHOTOGRAPHS)])

        response = self.client.get(self.url)

        self.assertContains(response, "ya tiene el máximo de 8 fotografías")
        self.assertNotContains(response, "Subir fotografías")
