from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import secrets
from database.session import Base

# -----------------------------
# Helper Functions
# -----------------------------
def generate_uuid():
    return str(uuid.uuid4())

def generate_hmac_secret():
    return secrets.token_hex(64)

def generate_api_key():
    return f"wp_{secrets.token_hex(24)}"

# -----------------------------
# TENANT MODEL
# -----------------------------
class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    api_key = Column(String(100), unique=True, nullable=False, default=generate_api_key)
    hmac_secret = Column(String(128), nullable=False, default=generate_hmac_secret)
    webhook_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    
    # Enterprise controls
    monthly_message_limit = Column(Integer, default=1000)
    current_month_count = Column(Integer, default=0)
    rate_limit_per_minute = Column(Integer, default=60)
    timezone = Column(String(50), default="UTC")
    custom_metadata = Column(JSON)
    
    # Security & Billing
    billing_tier = Column(String(20), default="starter")  # starter, growth, enterprise
    is_verified = Column(Boolean, default=False)
    max_whatsapp_accounts = Column(Integer, default=1)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    whatsapp_accounts = relationship("WhatsAppAccount", back_populates="tenant")
    messages = relationship("Message", back_populates="tenant")
    api_logs = relationship("APILog", back_populates="tenant")
    rate_limit_logs = relationship("RateLimitLog", back_populates="tenant")
    webhook_delivery_logs = relationship("WebhookDeliveryLog", back_populates="tenant")

# -----------------------------
# WHATSAPP ACCOUNT MODEL
# -----------------------------
class WhatsAppAccount(Base):
    __tablename__ = "whatsapp_accounts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    phone_number_id = Column(String(100), nullable=False)
    access_token = Column(String(500), nullable=False)
    
    # Enterprise columns
    phone_number = Column(String(20))
    business_account_id = Column(String(100))
    webhook_verify_token = Column(String(100))
    quality_rating = Column(String(20))
    is_verified = Column(Boolean, default=False)
    message_volume = Column(Integer, default=0)
    health_status = Column(String(20), default="active")
    
    # Security
    token_encrypted = Column(Boolean, default=False)
    last_token_rotation = Column(DateTime)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="whatsapp_accounts")
    messages = relationship("Message", back_populates="whatsapp_account")

# -----------------------------
# MESSAGE MODEL
# -----------------------------
class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    whatsapp_account_id = Column(String, ForeignKey("whatsapp_accounts.id"))
    
    # Message content
    wamid = Column(String(100))
    from_number = Column(String(20), nullable=False)
    to_number = Column(String(20), nullable=False)
    content = Column(Text)
    message_type = Column(String(50), default="text")
    direction = Column(String(10))
    status = Column(String(20), default="pending")
    
    # Enterprise columns
    status_timestamp = Column(DateTime)
    error_code = Column(String(50))
    error_message = Column(Text)
    template_name = Column(String(100))
    media_url = Column(String(500))
    custom_metadata = Column(JSON)
    
    # Billing & Analytics
    cost_units = Column(Integer, default=1)
    delivery_attempts = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="messages")
    whatsapp_account = relationship("WhatsAppAccount", back_populates="messages")

# -----------------------------
# API LOG MODEL
# -----------------------------
class APILog(Base):
    __tablename__ = "api_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time = Column(Integer, nullable=False)
    user_agent = Column(String(500))
    ip_address = Column(String(45))
    request_id = Column(String(100))
    client_version = Column(String(50))
    error_message = Column(Text)
    stack_trace = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    tenant = relationship("Tenant", back_populates="api_logs")

# -----------------------------
# RATE LIMIT LOG MODEL
# -----------------------------
class RateLimitLog(Base):
    __tablename__ = "rate_limit_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    request_count = Column(Integer, default=0)
    limit_type = Column(String(50), nullable=False)  # minute, hour, month
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tenant = relationship("Tenant", back_populates="rate_limit_logs")

# In database/models.py
class MessageTemplate(Base):
    __tablename__ = "message_templates"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String)  # order_confirmation
    category = Column(String)  # UTILITY, MARKETING, etc.
    language = Column(String, default="en")
    header = Column(Text)
    body = Column(Text)
    footer = Column(Text)
    buttons = Column(JSON)  # Store button config
    status = Column(String)  # PENDING, APPROVED, REJECTED
    meta_template_id = Column(String)  # Meta's template ID
    created_at = Column(DateTime, default=datetime.utcnow)


class ScheduledMessage(Base):
    __tablename__ = "scheduled_messages"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    whatsapp_account_id = Column(String, ForeignKey("whatsapp_accounts.id"))
    
    # Message details
    to_number = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")
    
    # Scheduling
    scheduled_at = Column(DateTime, nullable=False)  # When to send
    timezone = Column(String(50), default="UTC")
    
    # Status tracking
    status = Column(String(20), default="scheduled")  # scheduled, processing, sent, failed, cancelled
    sent_at = Column(DateTime)  # When actually sent
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    
    # Error handling
    error_message = Column(Text)
    last_attempt_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant")
    whatsapp_account = relationship("WhatsAppAccount")

# -----------------------------
# WEBHOOK DELIVERY LOG MODEL
# -----------------------------
class WebhookDeliveryLog(Base):
    __tablename__ = "webhook_delivery_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    message_id = Column(String, ForeignKey("messages.id"))
    
    webhook_url = Column(String(500), nullable=False)
    payload = Column(Text)
    response_status = Column(Integer)
    response_body = Column(Text)
    delivery_attempt = Column(Integer, default=1)
    
    initiated_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    
    error_message = Column(Text)
    retryable = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tenant = relationship("Tenant", back_populates="webhook_delivery_logs")
    message = relationship("Message")
