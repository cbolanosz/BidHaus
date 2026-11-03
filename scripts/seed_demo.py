"""Fill an empty installation with something to show.

Run it with:

    python manage.py shell < scripts/seed_demo.py

The database and the uploaded files are not in the repository, so a freshly
deployed server starts with nothing in it. This builds a small catalogue and
walks it through the product the way a person would: a seller publishes, an
administrator approves, a bidder bids, the closing command closes, the escrow
holds the money. No state is written by hand, so the history of every row is
true and the pages that read it have something real to show.

It is a development tool, not part of the product, which is why it lives
outside the apps: importing every app from inside one of them would add a
dependency the component diagram does not have.
"""

from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.utils import timezone
from PIL import Image, ImageDraw

from auctions.models import Auction, Category
from auctions.services import (
    approve_auction_publication,
    place_bid,
    publish_auction,
)
from escrow.services import attach_evidence, confirm_reception, open_dispute
from reputation.models import Rating
from reputation.services import rate_counterpart

User = get_user_model()

SELLER_PASSWORD = "vende1234"
BIDDER_PASSWORD = "puja1234"
CLOSES_IN = timedelta(days=6)


def coloured_photograph(colour, name="lote.png"):
    """A plain image, because the real photographs are not in the repository."""
    canvas = Image.new("RGB", (1200, 800), colour)
    brush = ImageDraw.Draw(canvas)
    brush.rectangle([60, 60, 1140, 740], outline=(255, 255, 255), width=6)
    buffer = BytesIO()
    canvas.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue(), name=name)


def account(email, full_name, role, verified=False):
    """Create the account if this is the first run, and keep its password known."""
    user, _ = User.objects.get_or_create(
        email=email, defaults={"full_name": full_name, "role": role}
    )
    user.full_name = full_name
    user.role = role
    user.is_verified = verified
    user.set_password(SELLER_PASSWORD if role == User.Role.SELLER else BIDDER_PASSWORD)
    user.save()
    return user


def publish(seller, category, title, description, price, condition, colour,
            approved=True):
    """Publish one lot and, unless it is the one left pending, approve it."""
    auction = publish_auction(
        seller=seller,
        category=Category.objects.get_or_create(name=category)[0],
        title=title,
        description=description,
        condition=condition,
        starting_price=Decimal(price),
        closing_date=timezone.now() + CLOSES_IN,
        images=[coloured_photograph(colour)],
    )
    if approved:
        approve_auction_publication(auction, ADMINISTRATOR)
    return auction


def sell(auction, buyer, amount):
    """Take a lot all the way to a retained payment, the way the product does."""
    place_bid(auction.pk, buyer, Decimal(amount))
    Auction.objects.filter(pk=auction.pk).update(
        closing_date=timezone.now() - timedelta(minutes=1)
    )
    call_command("close_auctions", verbosity=0)
    auction.refresh_from_db()
    return auction.escrow_transaction


if Auction.objects.exists():
    print("Ya hay subastas en esta base. El sembrador no vuelve a correr.")
else:
    ADMINISTRATOR = User.objects.filter(role=User.Role.ADMINISTRATOR).first()
    if ADMINISTRATOR is None:
        raise SystemExit(
            "Primero crea un administrador con: manage.py createsuperuser"
        )

    rincon = account("libreria.rincon@bidhaus.co", "Librería El Rincón",
                     User.Role.SELLER, verified=True)
    restauro = account("taller.restauro@bidhaus.co", "Taller Restauro",
                       User.Role.SELLER, verified=True)
    mora = account("archivo.mora@bidhaus.co", "Archivo Mora",
                   User.Role.SELLER, verified=True)
    duarte = account("casa.duarte@bidhaus.co", "Casa Duarte Antigüedades",
                     User.Role.SELLER, verified=True)
    andes = account("relojeria.andes@bidhaus.co", "Relojería Los Andes",
                    User.Role.SELLER, verified=True)

    laura = account("laura@bidhaus.co", "Laura Gómez", User.Role.BIDDER)
    sara = account("sara@bidhaus.co", "Sara Quintero", User.Role.BIDDER)
    miguel = account("miguel@bidhaus.co", "Miguel Ríos", User.Role.BIDDER)

    # ---- Sales already finished, so the sellers arrive with a reputation ----
    history = [
        (rincon, "Libros", "Lote de once novelas de la colección Austral",
         "Tapas blandas con el canto amarilleado, todas completas.",
         "260000", (122, 98, 72), laura, "310000", 5),
        (mora, "Fotografía", "Tres álbumes de postales de Medellín, 1940",
         "Postales en blanco y negro pegadas con esquineros.",
         "480000", (84, 96, 112), laura, "540000", 4),
        (restauro, "Muebles", "Mesa de centro en teca con la tapa rayada",
         "Estructura firme; la tapa pide un lijado.",
         "900000", (108, 86, 60), miguel, "980000", 2),
        (duarte, "Objetos Antiguos", "Juego de seis copas de cristal tallado",
         "Una de las seis tiene un desportillado en el borde.",
         "340000", (96, 108, 96), sara, "380000", 1),
    ]
    for seller, category, title, text, price, colour, buyer, bid, score in history:
        sale = sell(
            publish(seller, category, title, text, price,
                    Auction.Condition.USED, colour),
            buyer, bid,
        )
        confirm_reception(sale, buyer)
        rate_counterpart(sale, buyer, score)

    # ---- The catalogue the visitor sees -------------------------------------
    publish(rincon, "Libros", "Primera edición de «Cien años de soledad», 1967",
            "Editorial Sudamericana, Buenos Aires. Sobrecubierta original con "
            "el galeón de Vicente Rojo. Interior completo, sin subrayados, con "
            "el amarilleo propio del papel de la época.",
            "9800000", Auction.Condition.USED, (138, 112, 76))
    publish(restauro, "Muebles", "Pareja de sillas Wegner CH24, roble y papel trenzado",
            "Dinamarca, años sesenta. Estructura restaurada a mano y asiento de "
            "papel trenzado tejido de nuevo. Se venden como pareja.",
            "4200000", Auction.Condition.REFURBISHED, (116, 92, 64))
    publish(mora, "Fotografía", "Leica M3 de doble carga, 1956, con Summicron 50 mm",
            "Cuerpo con el desgaste propio del uso, obturador revisado y "
            "calibrado el año pasado. Incluye tapa frontal y correa de cuero.",
            "11500000", Auction.Condition.USED, (72, 80, 92))
    publish(duarte, "Objetos Antiguos", "Reloj de pared Junghans de péndulo, nogal",
            "Selva Negra, hacia 1910. Maquinaria limpia y en marcha, suena las "
            "horas y las medias. Caja de nogal con una fisura en el lateral.",
            "2600000", Auction.Condition.USED, (90, 76, 68))

    # ---- A request waiting for the administrator: FR36 and FR25 -------------
    pending = publish(andes, "Relojes", "Omega Speedmaster Professional 145.022, 1971",
                      "Caja de acero de 42 mm, calibre 861 con servicio reciente. "
                      "Esfera original sin retoques, bisel con marcas de uso.",
                      "16500000", Auction.Condition.USED, (62, 70, 86),
                      approved=False)

    # ---- A sale waiting for the buyer: FR15, and behind it FR16 and FR20 ----
    to_confirm = sell(
        publish(restauro, "Muebles", "Secreter danés en teca con persiana, 1964",
                "Tres cajones y tapa de persiana que corre sin trabarse. Teca "
                "lijada y aceitada. Marca de un vaso en la superficie.",
                "3100000", Auction.Condition.REFURBISHED, (104, 84, 58)),
        laura, "3400000",
    )

    # ---- A sale for the buyer to argue live: FR17 and FR18 ------------------
    to_argue = sell(
        publish(duarte, "Arte", "Óleo sobre tabla firmado, paisaje de la sabana",
                "Firmado en el ángulo inferior derecho y fechado en 1958. Marco "
                "original de madera dorada con pérdidas en dos esquinas.",
                "1900000", Auction.Condition.USED, (88, 100, 84)),
        laura, "2150000",
    )

    # ---- A dispute already open, for the administrator to resolve: FR19 -----
    argued = sell(
        publish(andes, "Relojes", "Seiko 6139-6002 «Pogue», cronógrafo automático",
                "Esfera amarilla original, bisel con decoloración uniforme. "
                "El cronógrafo arranca y vuelve a cero sin saltos.",
                "2800000", Auction.Condition.USED, (120, 104, 56)),
        sara, "3250000",
    )
    dispute = open_dispute(
        argued, sara,
        "El cronógrafo no vuelve a cero y la esfera tiene una marca de humedad "
        "que no aparece en ninguna de las fotografías de la publicación.",
    )
    attach_evidence(
        dispute, sara, [coloured_photograph((150, 70, 70), "marca-de-humedad.png")]
    )

    # ---- A finished sale nobody has rated yet: FR24 -------------------------
    to_rate = sell(
        publish(mora, "Fotografía", "Rolleiflex 2.8F con Planar 80 mm y funda",
                "Objetivo limpio, sin hongos ni rayones. Espejo de enfoque "
                "sustituido. Funda de cuero con el broche flojo.",
                "5400000", Auction.Condition.USED, (78, 86, 98)),
        laura, "5900000",
    )
    confirm_reception(to_rate, laura)
    Rating.objects.filter(transaction=to_rate).delete()

    print()
    print("Sembrado. Cuentas:")
    print("   compradores  laura@bidhaus.co, sara@bidhaus.co, miguel@bidhaus.co"
          f"   clave {BIDDER_PASSWORD}")
    print("   vendedores   libreria.rincon@, taller.restauro@, archivo.mora@,")
    print("                casa.duarte@, relojeria.andes@ (todos @bidhaus.co)"
          f"   clave {SELLER_PASSWORD}")
    print()
    print(f"   FR36 + FR25  aprobar publicación   lote {pending.pk} en el admin")
    print(f"   FR15         confirmar recepción   /escrow/transactions/{to_confirm.pk}/")
    print(f"   FR17 + FR18  abrir disputa         /escrow/transactions/{to_argue.pk}/")
    print(f"   FR19         resolver disputa      /escrow/disputes/{dispute.pk}/resolve/")
    print(f"   FR24         calificar             /reputation/sales/{to_rate.pk}/rate/")
