"""ORM-модели SQLAlchemy"""

from app.models.base import Base
from app.models.contact import ContactSubmission

__all__ = ["Base", "ContactSubmission"]
