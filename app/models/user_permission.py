from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import ARRAY
from app.core.database import Base


class UserPermission(Base):
    __tablename__ = "user_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"))
    chatwoot_user_id = Column(Integer, nullable=False)
    user_name = Column(String(255))
    user_email = Column(String(255))
    user_role = Column(String(50))
    is_admin = Column(Boolean, default=False)
    allowed_labels = Column(ARRAY(String), default=[])
    allowed_boards = Column(ARRAY(String), default=[])
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "client_slug": self.client_slug,
            "chatwoot_user_id": self.chatwoot_user_id,
            "user_name": self.user_name,
            "user_email": self.user_email,
            "user_role": self.user_role,
            "is_admin": self.is_admin,
            "allowed_labels": self.allowed_labels or [],
            "allowed_boards": self.allowed_boards or []
        }
