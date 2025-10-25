from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from database.session import SessionLocal
from database.models import Message, Tenant, WhatsAppAccount
from services.message_queue import rabbitmq_service
from middleware.rate_limiter import check_rate_limit
import time
import logging
from typing import Optional

router = APIRouter()
logger = logging.getLogger(__name__)

class SendMessageResponse(BaseModel):
    message_id: str
    status: str
    wamid: Optional[str] = None

@router.post("/send", response_model=SendMessageResponse)
async def send_message(
    request: Request,
    to_number: str = Query(..., description="Recipient phone number"),
    message: str = Query(..., description="Message content"),
    message_type: str = Query("text", description="Type of message"),
    template_name: Optional[str] = Query(None, description="Template name if using template")
):
    tenant = request.state.tenant
    
    # Check rate limits
    if not await check_rate_limit(tenant.id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    db = SessionLocal()
    try:
        # Get tenant's WhatsApp account
        whatsapp_account = db.query(WhatsAppAccount).filter(
            WhatsAppAccount.tenant_id == tenant.id,
            WhatsAppAccount.is_active == True
        ).first()
        
        if not whatsapp_account:
            raise HTTPException(status_code=400, detail="No active WhatsApp account configured")
        
        # Create message record
        message_record = Message(
            tenant_id=tenant.id,
            whatsapp_account_id=whatsapp_account.id,
            from_number=whatsapp_account.phone_number or "unknown",
            to_number=to_number,
            content=message,
            message_type=message_type,
            direction="outgoing",
            status="queued",
            template_name=template_name
        )
        
        db.add(message_record)
        db.commit()
        db.refresh(message_record)
        
        # Queue message for processing
        queue_data = {
            "message_id": message_record.id,
            "tenant_id": tenant.id,
            "whatsapp_account_id": whatsapp_account.id,
            "to_number": to_number,
            "content": message,
            "message_type": message_type
        }
        
        rabbitmq_service.send_message('outgoing_messages', queue_data)
        
        logger.info(f"📨 Message queued for tenant {tenant.name}: {message_record.id}")
        
        return SendMessageResponse(
            message_id=message_record.id,
            status="queued",
            wamid=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Message sending failed for tenant {tenant.id}: {e}")
        raise HTTPException(status_code=500, detail="Message sending failed")
    finally:
        db.close()