import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _now():
    return datetime.now(timezone.utc)


class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    website_url = Column(String(500))
    industry = Column(String(100))
    sub_industry = Column(String(100))
    location = Column(String(200))
    timezone = Column(String(50), default="Africa/Johannesburg")
    founded_year = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now)

    brand_dna = relationship(
        "BrandDNA", back_populates="client", uselist=False, cascade="all, delete-orphan"
    )
    personas = relationship(
        "ICPPersona",
        back_populates="client",
        cascade="all, delete-orphan",
        order_by="ICPPersona.order",
    )


class BrandDNA(Base):
    __tablename__ = "brand_dna"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Voice
    tagline = Column(String(500))
    tone = Column(String(50))           # formal / casual / playful / authoritative / warm
    language_style = Column(Text)
    personality_traits = Column(JSON)   # ["innovative", "trustworthy", ...]

    # Visual identity
    primary_color = Column(String(7))   # hex e.g. "#FF5500"
    secondary_colors = Column(JSON)     # ["#xxx", ...]
    accent_color = Column(String(7))
    heading_font = Column(String(100))
    body_font = Column(String(100))
    logo_url = Column(String(500))
    visual_style = Column(String(100))  # minimalist / bold / editorial / dark-tech / luxury / warm

    # Messaging
    usps = Column(JSON)                 # ["USP 1", ...]
    pain_points_addressed = Column(JSON)
    key_messages = Column(JSON)
    competitors = Column(JSON)
    differentiators = Column(JSON)

    enriched_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now)

    client = relationship("Client", back_populates="brand_dna")


class ICPPersona(Base):
    __tablename__ = "icp_personas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )

    persona_name = Column(String(200), nullable=False)
    age_min = Column(Integer)
    age_max = Column(Integer)
    gender_skew = Column(String(50))    # male / female / balanced
    income_bracket = Column(String(50)) # low / lower-middle / middle / upper-middle / high
    location_type = Column(String(50))  # urban / suburban / rural / mixed

    interests = Column(JSON)
    values = Column(JSON)
    pain_points = Column(JSON)
    goals = Column(JSON)
    preferred_channels = Column(JSON)
    seo_keywords = Column(JSON)
    vocabulary = Column(JSON)

    order = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now)

    client = relationship("Client", back_populates="personas")
