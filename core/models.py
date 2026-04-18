from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, func, Text

from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True)
    name = Column(String)
    phone = Column(String, nullable=True)
    appointments = relationship("Appointment", back_populates="user")

class Master(Base):
    __tablename__ = "masters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    specialization = Column(String)
    is_active = Column(Boolean, default=True)
    schedule = Column(String, nullable=True)
    appointments = relationship("Appointment", back_populates="master")

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    price = Column(Float)
    duration_min = Column(Integer)
    appointments = relationship("Appointment", back_populates="service")

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    master_id = Column(Integer, ForeignKey("masters.id"))
    service_id = Column(Integer, ForeignKey("services.id"))
    date_time = Column(String) # Храним как строку "YYYY-MM-DD HH:MM" для простоты
    status = Column(String, default="pending")
    
    user = relationship("User", back_populates="appointments")
    master = relationship("Master", back_populates="appointments")
    service = relationship("Service", back_populates="appointments")

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"))
    rating = Column(Integer)
    comment = Column(String)
    