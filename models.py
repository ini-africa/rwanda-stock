from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    name = Column(String)
    current_price = Column(Float)
    change = Column(Float)
    volume = Column(Integer, default=0)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    history = relationship("PriceHistory", back_populates="stock")

class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    stock = relationship("Stock", back_populates="history")

class MarketStat(Base):
    __tablename__ = "market_stats"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True) # e.g., "Total Market Capitalization"
    value = Column(String)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

class Bond(Base):
    __tablename__ = "bonds"

    id = Column(Integer, primary_key=True, index=True)
    security = Column(String, unique=True, index=True) # ISIN or Name
    coupon = Column(String)
    maturity = Column(String)
    price = Column(Float)
    yield_percentage = Column(Float)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
