from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from src.config.settings import settings
from src.core.models import HubEvent, AdapterResult

Base = declarative_base()

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True)
    task_id = Column(String, index=True)
    adapter = Column(String)
    event_type = Column(String)
    request_payload = Column(JSON)
    response_payload = Column(JSON)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

class AuditLog:
    def write(self, task_id: str, adapter: str, event_type: str, request: dict, result: AdapterResult):
        db = SessionLocal()
        try:
            entry = AuditEvent(
                id=task_id, # Для v1 используем task_id как PK
                task_id=task_id,
                adapter=adapter,
                event_type=event_type,
                request_payload=request,
                response_payload=result.response_data if result.success else {"error": result.error_message},
                status="DONE" if result.success else "FAILED"
            )
            db.add(entry)
            db.commit()
        finally:
            db.close()

audit_log = AuditLog()
