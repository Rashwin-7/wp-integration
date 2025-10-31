from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import secrets
from database.session import get_db
from database.models import Tenant, WhatsAppAccount, Message
from services.whatsapp_service import whatsapp_service
from services.message_queue import rabbitmq_service
from loguru import logger

router = APIRouter()

@router.post("/tenants/")
def create_tenant(name: str, db: Session = Depends(get_db)):
    """Create a new tenant (business)"""
    
    existing_tenant = db.query(Tenant).filter(Tenant.name == name).first()
    if existing_tenant:
        raise HTTPException(status_code=400, detail="Name already exists")
    
    api_key = f"wp_{secrets.token_urlsafe(32)}"
    
    tenant = Tenant(
        name=name, 
        email=f"{name}@example.com",
        api_key=api_key
    )
    
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    
    return {
        "id": tenant.id,
        "name": tenant.name,
        "api_key": api_key,
        "message": "Save this API key securely!"
    }

@router.get("/tenants/")
def list_tenants(db: Session = Depends(get_db)):
    """List all tenants"""
    tenants = db.query(Tenant).all()
    return tenants

@router.post("/messages/send")
async def send_message(
    to_number: str,
    message: str,
    db: Session = Depends(get_db)
):
    """Send a WhatsApp message (with RabbitMQ queueing)"""
    logger.info(f"📤 Sending message to {to_number}")
    
    # Get or create tenant
    tenant = db.query(Tenant).first()
    if not tenant:
        tenant = Tenant(
            name="Test Tenant", 
            email="test@example.com",
            api_key="test_key"
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    
    # Get or create WhatsApp account
    whatsapp_account = db.query(WhatsAppAccount).filter(
        WhatsAppAccount.tenant_id == tenant.id
    ).first()
    
    if not whatsapp_account:
        whatsapp_account = WhatsAppAccount(
            tenant_id=tenant.id,
            phone_number_id="TEST_PHONE_ID",
            access_token="TEST_ACCESS_TOKEN", 
            phone_number="1234567890"
        )
        db.add(whatsapp_account)
        db.commit()
    
    # Create message record
    message_obj = Message(
        tenant_id=tenant.id,
        whatsapp_account_id=whatsapp_account.id,
        from_number=whatsapp_account.phone_number,
        to_number=to_number,
        content=message,
        direction="outbound",
        status="queued"
    )
    db.add(message_obj)
    db.commit()
    db.refresh(message_obj)
    
    # Prepare message for RabbitMQ
    queue_message = {
        "message_id": message_obj.id,
        "to_number": to_number,
        "content": message,
        "tenant_name": tenant.name
    }
    
    # Send to RabbitMQ
    if rabbitmq_service.is_connected:
        success = rabbitmq_service.send_message('outgoing_messages', queue_message)
        if success:
            logger.success(f"✅ Message queued in RabbitMQ: {message_obj.id}")
            return {
                "message_id": message_obj.id,
                "status": "queued",
                "queue": "outgoing_messages",
                "message": "Message queued successfully",
                "rabbitmq": "connected"
            }
    
    # Fallback: Direct sending (without queue)
    logger.warning("🔄 RabbitMQ not available, sending directly")
    result = await whatsapp_service.send_text_message(
        phone_number_id=whatsapp_account.phone_number_id,
        access_token=whatsapp_account.access_token,
        to_number=to_number,
        message=message
    )
    
    # Update message status
    if result["success"]:
        message_obj.status = "sent"
    else:
        message_obj.status = "failed"
    
    db.commit()
    
    return {
        "message_id": message_obj.id,
        "status": message_obj.status,
        "queue": "direct",
        "rabbitmq": "disconnected",
        "whatsapp_response": result
    }

# ========================
# SIMPLE AUTO-ENDPOINTS
# ========================
@router.post("/auto/order-confirm")
async def auto_order_confirm(customer_phone: str, order_id: str, items: str, db: Session = Depends(get_db)):
    """Restaurants: Auto-send order confirmation"""
    # Get tenant
    tenant = db.query(Tenant).first()
    
    message = f"✅ Order #{order_id} confirmed!\n📦 Items: {items}\n⏰ Ready in 30 minutes! 🍕"
    
    # Use your existing message sending logic - CALL IT DIRECTLY
    return await send_message_handler(customer_phone, message, db)

@router.post("/auto/shipping-update") 
async def auto_shipping_update(customer_phone: str, order_id: str, tracking_url: str, db: Session = Depends(get_db)):
    """Stores: Auto-send shipping info"""
    tenant = db.query(Tenant).first()
    
    message = f"🚚 Order #{order_id} shipped!\n📮 Track here: {tracking_url}"
    return await send_message_handler(customer_phone, message, db)

@router.post("/auto/appointment-reminder")
async def auto_appointment_reminder(customer_phone: str, service: str, date_time: str, db: Session = Depends(get_db)):
    """Clinics: Auto-send appointment reminder"""
    tenant = db.query(Tenant).first()
    
    message = f"📅 Your {service} appointment is confirmed!\n🕒 Date: {date_time}\n📍 See you soon! 👨‍⚕️"
    return await send_message_handler(customer_phone, message, db)

# Helper function to call send_message logic
async def send_message_handler(to_number: str, message: str, db: Session):
    """Helper to call send_message logic directly"""
    logger.info(f"📤 Auto-sending message to {to_number}")
    
    # Get or create tenant
    tenant = db.query(Tenant).first()
    if not tenant:
        tenant = Tenant(
            name="Test Tenant", 
            email="test@example.com",
            api_key="test_key"
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    
    # Get or create WhatsApp account
    whatsapp_account = db.query(WhatsAppAccount).filter(
        WhatsAppAccount.tenant_id == tenant.id
    ).first()
    
    if not whatsapp_account:
        whatsapp_account = WhatsAppAccount(
            tenant_id=tenant.id,
            phone_number_id="TEST_PHONE_ID",
            access_token="TEST_ACCESS_TOKEN", 
            phone_number="1234567890"
        )
        db.add(whatsapp_account)
        db.commit()
    
    # Create message record
    message_obj = Message(
        tenant_id=tenant.id,
        whatsapp_account_id=whatsapp_account.id,
        from_number=whatsapp_account.phone_number,
        to_number=to_number,
        content=message,
        direction="outbound",
        status="queued"
    )
    db.add(message_obj)
    db.commit()
    db.refresh(message_obj)
    
    # Prepare message for RabbitMQ
    queue_message = {
        "message_id": message_obj.id,
        "to_number": to_number,
        "content": message,
        "tenant_name": tenant.name
    }
    
    # Send to RabbitMQ
    if rabbitmq_service.is_connected:
        success = rabbitmq_service.send_message('outgoing_messages', queue_message)
        if success:
            logger.success(f"✅ Auto-message queued in RabbitMQ: {message_obj.id}")
            return {
                "message_id": message_obj.id,
                "status": "queued",
                "queue": "outgoing_messages",
                "message": "Auto-message queued successfully",
                "rabbitmq": "connected"
            }
    
    # Fallback: Direct sending (without queue)
    logger.warning("🔄 RabbitMQ not available, sending auto-message directly")
    result = await whatsapp_service.send_text_message(
        phone_number_id=whatsapp_account.phone_number_id,
        access_token=whatsapp_account.access_token,
        to_number=to_number,
        message=message
    )
    
    # Update message status
    if result["success"]:
        message_obj.status = "sent"
    else:
        message_obj.status = "failed"
    
    db.commit()
    
    return {
        "message_id": message_obj.id,
        "status": message_obj.status,
        "queue": "direct",
        "rabbitmq": "disconnected",
        "whatsapp_response": result
    }