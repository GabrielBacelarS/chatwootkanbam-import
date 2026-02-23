from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, func
from backend.core.database import Base


class AIKnowledgeFile(Base):
    __tablename__ = "ai_knowledge_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"))
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    content = Column(Text)
    file_size = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "client_slug": self.client_slug,
            "filename": self.filename,
            "original_name": self.original_name,
            "file_size": self.file_size,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
