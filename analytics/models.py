"""How much an auction can be trusted, and why (DBR10)."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from analytics.trust_factors import MAXIMUM_SCORE, MINIMUM_SCORE


class TrustScore(models.Model):
    """A figure between 0 and 100 for one auction, with the reasons behind it.

    The factors are stored next to the figure, not recomputed on reading: a
    visitor is owed the reasons that produced the number they are looking at,
    and those reasons must not change under them when the catalogue does.
    """

    auction = models.OneToOneField(
        "auctions.Auction",
        on_delete=models.CASCADE,
        related_name="trust_score",
        verbose_name="subasta",
    )
    score = models.PositiveSmallIntegerField(
        "índice de confianza",
        validators=[MinValueValidator(MINIMUM_SCORE), MaxValueValidator(MAXIMUM_SCORE)],
    )
    factors = models.JSONField("factores", default=list)
    calculated_at = models.DateTimeField("fecha de cálculo", auto_now_add=True)

    class Meta:
        ordering = ["-calculated_at"]
        verbose_name = "índice de confianza"
        verbose_name_plural = "índices de confianza"

    def __str__(self):
        return f"{self.auction.title} · {self.score}/{MAXIMUM_SCORE}"

    @property
    def met_factors(self):
        """The reasons the auction earned points for."""
        return [factor for factor in self.factors if factor["met"]]

    @property
    def unmet_factors(self):
        """What the auction would have to do to score higher."""
        return [factor for factor in self.factors if not factor["met"]]
