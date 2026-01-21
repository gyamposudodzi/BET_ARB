from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Bookmaker(Base):
    __tablename__ = "bookmakers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100))
    api_available = Column(Boolean, default=False)
    scrape_required = Column(Boolean, default=False)
    base_url = Column(String(255))
    auth_type = Column(String(20))
    credentials = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Sport(Base):
    __tablename__ = "sports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    key = Column(String(50), unique=True, nullable=False)
    active = Column(Boolean, default=True)
    priority = Column(Integer, default=1)
    last_scan = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sport_id = Column(Integer, ForeignKey("sports.id"))
    external_id = Column(String(100), nullable=False)
    home_team = Column(String(100), nullable=False)
    away_team = Column(String(100), nullable=False)
    league = Column(String(100))
    commence_time = Column(DateTime, nullable=False)
    status = Column(String(20), default="upcoming")
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sport = relationship("Sport")
    
    __table_args__ = (
        UniqueConstraint("sport_id", "external_id", name="uix_sport_external"),
    )

class Market(Base):
    __tablename__ = "markets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    market_type = Column(String(50), nullable=False)  # h2h, spreads, totals
    description = Column(String(200))
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    event = relationship("Event")
    odds = relationship("Odds", back_populates="market", cascade="all, delete-orphan")

class Odds(Base):
    __tablename__ = "odds"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    market_id = Column(Integer, ForeignKey("markets.id"))
    bookmaker_id = Column(Integer, ForeignKey("bookmakers.id"))
    outcome = Column(String(50), nullable=False)  # home, away, over, under
    price = Column(Float, nullable=False)  # Decimal odds
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    market = relationship("Market", back_populates="odds")
    bookmaker = relationship("Bookmaker")
    
    __table_args__ = (
        UniqueConstraint("market_id", "bookmaker_id", "outcome", name="uix_market_bookmaker_outcome"),
    )

class Opportunity(Base):
    __tablename__ = "opportunities"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    sport_key = Column(String(50), nullable=False)
    market_type = Column(String(50), nullable=False)
    
    # Opportunity details
    profit_percentage = Column(Float, nullable=False)
    total_investment = Column(Float)
    guaranteed_return = Column(Float)
    stake_allocations = Column(JSON, nullable=False)
    
    # Timing
    detected_at = Column(DateTime, default=datetime.utcnow)
    expiry_time = Column(DateTime)
    
    # Status
    status = Column(String(20), default="detected")  # detected, executing, completed, expired
    
    # Relationships
    event = relationship("Event")

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False)  # info, warning, error, success
    category = Column(String(50), nullable=False)  # opportunity, system, balance
    message = Column(Text, nullable=False)
    data = Column(JSON)
    
    sent_to_telegram = Column(Boolean, default=False)
    acknowledged = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime)

class SystemLog(Base):
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False)
    module = Column(String(100))
    message = Column(Text, nullable=False)
    data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)