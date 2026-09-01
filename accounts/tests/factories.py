"""Objects and cleanup the accounts tests need."""

from itertools import count

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from accounts.models import VerificationRequest
from accounts.validators import MAX_DOCUMENT_SIZE_BYTES

User = get_user_model()

_account_numbers = count(1)

PASSWORD = "subasta-seguro-2026"
PDF_BYTES = b"%PDF-1.4 documento de prueba"


def create_account(full_name="Laura Gómez", role=User.Role.BIDDER, **overrides):
    """Create an account with a unique email address."""
    fields = {
        "email": f"cuenta{next(_account_numbers)}@bidhaus.co",
        "full_name": full_name,
        "password": PASSWORD,
        "role": role,
    }
    fields.update(overrides)
    return User.objects.create_user(**fields)


def create_administrator():
    """Create an account with the administrator role."""
    return create_account(full_name="Admin de prueba", role=User.Role.ADMINISTRATOR)


def build_document(name="cedula.pdf"):
    """Build a small file that passes as an identity document."""
    return SimpleUploadedFile(name, PDF_BYTES, content_type="application/pdf")


def build_oversized_document(name="cedula.pdf"):
    """Build a document padded past the size limit."""
    padding = b"\x00" * (MAX_DOCUMENT_SIZE_BYTES + 1)
    return SimpleUploadedFile(name, PDF_BYTES + padding, content_type="application/pdf")


class DocumentStoringTestCase(TestCase):
    """Deletes the documents a test stored.

    Identity documents are written outside MEDIA_ROOT, to a real folder that
    no override_settings redirects, so each test cleans up after itself. The
    test database starts empty, so this only ever reaches its own files.
    """

    def tearDown(self):
        for verification_request in VerificationRequest.objects.all():
            if verification_request.identity_document:
                verification_request.identity_document.delete(save=False)
