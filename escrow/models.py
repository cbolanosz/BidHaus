"""The money a closed auction holds until the buyer confirms (DBR05, DBR06)."""

from django.conf import settings
from django.db import models

from escrow.commission import calculate_commission
from escrow.exceptions import StateChangeIsImmutable

NO_COMMISSION = 0


class EscrowTransaction(models.Model):
    """The payment of a winning bidder, retained until the sale completes.

    One per auction at most, which the one-to-one relation enforces in the
    database rather than in a service that somebody could forget to call.
    """

    class State(models.TextChoices):
        HELD = "held", "Retenido"
        RELEASED = "released", "Liberado"
        REFUNDED = "refunded", "Reembolsado"
        IN_DISPUTE = "in_dispute", "En disputa"

    auction = models.OneToOneField(
        "auctions.Auction",
        on_delete=models.PROTECT,
        related_name="escrow_transaction",
        verbose_name="subasta",
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchases",
        verbose_name="comprador",
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sales",
        verbose_name="vendedor",
    )
    amount = models.DecimalField("monto", max_digits=12, decimal_places=2)
    commission = models.DecimalField(
        "comisión", max_digits=12, decimal_places=2, default=NO_COMMISSION
    )
    state = models.CharField(
        "estado", max_length=20, choices=State.choices, default=State.HELD
    )
    created_at = models.DateTimeField("fecha de creación", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "transacción en custodia"
        verbose_name_plural = "transacciones en custodia"

    def __str__(self):
        return f"{self.auction.title} · {self.get_state_display()}"

    @property
    def is_held(self):
        """Whether the money is still retained, waiting for the buyer."""
        return self.state == self.State.HELD

    @property
    def commission_due(self):
        """The commission of this sale: the one charged, or the one it will carry.

        While the money is retained nothing has been deducted yet, so the figure
        shown is what the current percentage would take. Once released, it is
        the amount actually kept, which never changes again even if the
        percentage of the platform does.
        """
        if self.is_held:
            return calculate_commission(self.amount)
        return self.commission

    @property
    def payout(self):
        """What reaches the seller once BidHaus takes its cut (FR16, FR20)."""
        return self.amount - self.commission_due


class StateChangeQuerySet(models.QuerySet):
    """Closes the two ways of changing rows in bulk, which skip Model.save()."""

    def update(self, **fields):
        raise StateChangeIsImmutable

    def delete(self):
        raise StateChangeIsImmutable


class StateChange(models.Model):
    """One transition of an escrow transaction (DBR06).

    The history is append-only: a dispute is resolved from it, so it is the
    evidence. The first change of a transaction has no previous state, and a
    change the system made on its own has no actor.
    """

    transaction = models.ForeignKey(
        EscrowTransaction,
        on_delete=models.CASCADE,
        related_name="state_changes",
        verbose_name="transacción",
    )
    previous_state = models.CharField(
        "estado anterior",
        max_length=20,
        choices=EscrowTransaction.State.choices,
        blank=True,
    )
    new_state = models.CharField(
        "estado nuevo", max_length=20, choices=EscrowTransaction.State.choices
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="escrow_state_changes",
        null=True,
        blank=True,
        verbose_name="responsable",
    )
    timestamp = models.DateTimeField("fecha y hora", auto_now_add=True)

    objects = StateChangeQuerySet.as_manager()

    class Meta:
        ordering = ["timestamp"]
        verbose_name = "cambio de estado"
        verbose_name_plural = "cambios de estado"

    def __str__(self):
        return f"{self.previous_state or '—'} → {self.new_state}"

    def save(self, *args, **kwargs):
        """Store the change, and refuse to modify one that already exists (DBR06)."""
        if not self._state.adding:
            raise StateChangeIsImmutable
        super().save(*args, **kwargs)


class Dispute(models.Model):
    """The claim of a buyer who did not receive what was sold (DBR07).

    At most one per transaction, which the one-to-one relation enforces in the
    database: a sale is argued once, and that single thread is what an
    administrator reads to resolve it.
    """

    class State(models.TextChoices):
        OPEN = "open", "Abierta"
        RESOLVED = "resolved", "Resuelta"

    transaction = models.OneToOneField(
        EscrowTransaction,
        on_delete=models.PROTECT,
        related_name="dispute",
        verbose_name="transacción",
    )
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="disputes_opened",
        verbose_name="abierta por",
    )
    description = models.TextField("descripción")
    state = models.CharField(
        "estado", max_length=20, choices=State.choices, default=State.OPEN
    )
    opened_at = models.DateTimeField("fecha de apertura", auto_now_add=True)

    class Meta:
        ordering = ["-opened_at"]
        verbose_name = "disputa"
        verbose_name_plural = "disputas"

    def __str__(self):
        return f"{self.transaction.auction.title} · {self.get_state_display()}"

    @property
    def is_open(self):
        """Whether the claim is still waiting for an administrator (FR19)."""
        return self.state == self.State.OPEN
