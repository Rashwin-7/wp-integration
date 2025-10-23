from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer, JSON, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from database.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False)
    api_key = Column(String(100), unique=True, nullable=False)
    webhook_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    
    # 🆕 ENTERPRISE FIELDS
    monthly_message_limit = Column(Integer, default=1000)  # Pricing tiers
    current_month_count = Column(Integer, default=0)       # Usage tracking
    rate_limit_per_minute = Column(Integer, default=60)    # Rate limiting
    timezone = Column(String(50), default="UTC")           # Localization
    custom_metadata = Column(JSON)                                # Custom fields
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    whatsapp_accounts = relationship("WhatsAppAccount", back_populates="tenant")
    messages = relationship("Message", back_populates="tenant")
    message_templates = relationship("MessageTemplate", back_populates="tenant")
    webhook_logs = relationship("WebhookLog", back_populates="tenant")

class WhatsAppAccount(Base):
    __tablename__ = "whatsapp_accounts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    phone_number_id = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)  # 🆕 Actual phone number
    access_token = Column(String(500), nullable=False)
    business_account_id = Column(String(100))  # 🆕 Business account ID
    waba_id = Column(String(100))  # 🆕 WhatsApp Business Account ID
    
    # 🆕 ENTERPRISE FIELDS
    webhook_verify_token = Column(String(100))
    quality_rating = Column(String(20))  # Green/Yellow/Red
    is_verified = Column(Boolean, default=False)
    message_volume = Column(BigInteger, default=0)  # Total messages sent
    health_status = Column(String(20), default="active")  # active, warning, suspended
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="whatsapp_accounts")
    messages = relationship("Message", back_populates="whatsapp_account")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    whatsapp_account_id = Column(String, ForeignKey("whatsapp_accounts.id"), nullable=False)
    
    # 🆕 ENTERPRISE FIELDS
    wamid = Column(String(100))  # WhatsApp Message ID
    conversation_id = Column(String(100))  # Group messages by conversation
    
    from_number = Column(String(20), nullable=False)
    to_number = Column(String(20), nullable=False)
    content = Column(Text)
    message_type = Column(String(50), default="text")  # text, image, template, etc.
    direction = Column(String(10))  # inbound, outbound
    
    # 🆕 ENHANCED STATUS TRACKING
    status = Column(String(20), default="pending")  # pending, sent, delivered, read, failed
    status_timestamp = Column(DateTime)  # When status changed
    error_code = Column(String(50))  # Error details if failed
    error_message = Column(Text)
    
    # 🆕 MESSAGE METADATA
    template_name = Column(String(100))  # For template messages
    media_url = Column(String(500))  # For media messages
    custom_metadata = Column(JSON)  # Additional data
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="messages")
    whatsapp_account = relationship("WhatsAppAccount", back_populates="messages")
    status_history = relationship("MessageStatusHistory", back_populates="message")

# 🆕 NEW TABLES FOR ENTERPRISE FEATURES

class MessageStatusHistory(Base):
    __tablename__ = "message_status_history"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    message_id = Column(String, ForeignKey("messages.id"), nullable=False)
    status = Column(String(20), nullable=False)  # sent, delivered, read, etc.
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String(50))  # webhook, api, system
    
    # Relationships
    message = relationship("Message", back_populates="status_history")

class MessageTemplate(Base):
    __tablename__ = "message_templates"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    category = Column(String(50))  # MARKETING, UTILITY, AUTHENTICATION
    language = Column(String(10), default="en")
    status = Column(String(20), default="pending")  # pending, approved, rejected
    components = Column(JSON)  # Template structure
    waba_template_id = Column(String(100))  # ID from WhatsApp
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="message_templates")

class WebhookLog(Base):
    __tablename__ = "webhook_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # message, status, etc.
    payload = Column(JSON)  # Raw webhook data
    processed = Column(Boolean, default=False)
    error = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="webhook_logs")

class RateLimit(Base):
    __tablename__ = "rate_limits"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    window_start = Column(DateTime, nullable=False)
    request_count = Column(Integer, default=0)
    window_size = Column(String(10), default="minute")  # minute, hour, day
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant")