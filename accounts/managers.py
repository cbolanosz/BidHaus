"""Creation of users. BidHaus identifies a person by email, not by username."""

from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """Builds users whose login identifier is the email address."""

    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        """Create a regular user with a normalised email and a hashed password."""
        if not email:
            raise ValueError("The user needs an email address.")

        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create an administrator with access to the Django admin."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", self.model.Role.ADMINISTRATOR)
        extra_fields.setdefault("is_verified", True)

        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("A superuser needs is_staff and is_superuser enabled.")

        return self.create_user(email, password, **extra_fields)
