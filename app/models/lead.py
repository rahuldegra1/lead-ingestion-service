from sqlalchemy import Column, Integer, String

from app.database import Base


class LeadDB(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    budget_inr = Column(Integer, nullable=False)
    phone = Column(String, nullable=False)
    status = Column(String, nullable=False, server_default="NEW", default="NEW")
