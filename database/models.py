from sqlalchemy import Column, Integer, String, Boolean, Float, Text, func
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.sql.sqltypes import DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Stock(Base):
    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    last = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    change = Column(Float, nullable=False)
    change_pct = Column(Float, nullable=False)
    growth = Column(Boolean, nullable=False)
    date = Column(DateTime, nullable=False, default=func.now())

    news = relationship("StockNews", back_populates="stock")
    compound = relationship("SentimentCompound", back_populates="stock")


class StockHistory(Base):
    __tablename__ = "stocks_history"
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False)


class DailyStockHistory(Base):
    __tablename__ = "daily_history"
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False)


class MonthlyStockHistory(Base):
    __tablename__ = "monthly_history"
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False)


class HistoryToAnalyze(Base):
    __tablename__ = "analyze_history"
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False)


class StockNews(Base):
    __tablename__ = "stock_news"
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    title = Column(String(250), nullable=False)
    link = Column(String(300), nullable=False)
    summary = Column(Text(), nullable=True)
    decrease = Column(Integer, nullable=False)
    increase = Column(Integer, nullable=False)
    informativeness = Column(Integer, nullable=True)

    stock = relationship("Stock", back_populates="news")


class SentimentCompound(Base):
    __tablename__ = "stock_compound"
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    fall_probability = Column(Float, nullable=False)
    rise_probability = Column(Float, nullable=False)

    stock = relationship("Stock", back_populates="compound")
