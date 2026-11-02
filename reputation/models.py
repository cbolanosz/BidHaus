"""What each side of a completed sale says about the other (DBR09)."""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

MINIMUM_SCORE = 1
MAXIMUM_SCORE = 5


class Rating(models.Model):
    """One score a participant gives the counterpart of a completed sale.

    The three rules of DBR09 are constraints in the database and not only
    checks in a service: a score between one and five, nobody rating
    themselves, and one rating per participant per sale.
    """

    transaction = models.ForeignKey(
        "escrow.EscrowTransaction",
        on_delete=models.PROTECT,
        related_name="ratings",
        verbose_name="transacción",
    )
    rater = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ratings_given",
        verbose_name="califica",
    )
    rated = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ratings_received",
        verbose_name="calificado",
    )
    score = models.PositiveSmallIntegerField(
        "puntaje",
        validators=[MinValueValidator(MINIMUM_SCORE), MaxValueValidator(MAXIMUM_SCORE)],
    )
    created_at = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["transaction", "rater"],
                name="one_rating_per_participant_per_sale",
            ),
            models.CheckConstraint(
                condition=~models.Q(rater=models.F("rated")),
                name="nobody_rates_themselves",
            ),
            models.CheckConstraint(
                condition=models.Q(score__gte=MINIMUM_SCORE, score__lte=MAXIMUM_SCORE),
                name="score_between_one_and_five",
            ),
        ]
        verbose_name = "calificación"
        verbose_name_plural = "calificaciones"

    def __str__(self):
        return f"{self.rated} · {self.score}/{MAXIMUM_SCORE}"
