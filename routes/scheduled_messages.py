# routes/scheduled_messages.py
from fastapi import APIRouter, Request, HTTPException, Header, Query
from pydantic import BaseModel
from datetime import datetime
from database.session import SessionLocal
from database.models import ScheduledMessage, Tenant, WhatsAppAccount
from typing import Optional
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# ------------------ MODELS ------------------

class ScheduledMessageResponse(BaseModel):
    scheduled_message_id: str
    status: str
    scheduled_at: str

# ------------------ UTILITIES ------------------

def get_tenant_from_request(request: Request):
    """Safely get tenant from request state with proper error handling."""
    tenant = getattr(request.state, 'tenant', None)
    logger.debug(f"🔍 Checking request.state.tenant: {tenant}")

    if not tenant:
        logger.error("❌ Tenant not found in request state - authentication middleware may not be working")
        # Helpful debug info
        state_attrs = [attr for attr in dir(request.state) if not attr.startswith('_')]
        logger.debug(f"🔍 Available attributes in request.state: {state_attrs}")
        raise HTTPException(status_code=401, detail="Authentication required - tenant information missing")

    logger.debug(f"✅ Tenant retrieved from request.state: {tenant.id} - {tenant.name}")
    return tenant

# ------------------ ROUTES ------------------

@router.post("/schedule", response_model=ScheduledMessageResponse)
async def schedule_message(
    request: Request,
    # ✅ CHANGED: Using Query parameters for Swagger UI input boxes
    to: str = Query(..., description="Recipient phone number with country code (e.g., +1234567890)"),
    message: str = Query(..., description="Message content to send"),
    scheduled_at: str = Query(..., description="Scheduled time in ISO format (e.g., 2024-01-01T14:30:00)"),
    timezone: str = Query("UTC", description="Timezone for the scheduled time"),
    message_type: str = Query("text", description="Type of message (text, template, etc.)"),
    x_tenant_id: str = Header(None)  # ✅ Add header support for Swagger
):
    """Schedule a message for future delivery."""
    logger.debug(f"🚀 Schedule message endpoint called (Tenant header: {x_tenant_id})")

    tenant = get_tenant_from_request(request)
    db = SessionLocal()
    try:
        # Parse scheduled time
        try:
            scheduled_time = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO format: YYYY-MM-DDTHH:MM:SS")

        # Validate scheduled time
        if scheduled_time <= datetime.utcnow():
            raise HTTPException(status_code=400, detail="Scheduled time must be in the future")

        # Get tenant's active WhatsApp account
        whatsapp_account = db.query(WhatsAppAccount).filter(
            WhatsAppAccount.tenant_id == tenant.id,
            WhatsAppAccount.is_active == True
        ).first()

        if not whatsapp_account:
            raise HTTPException(status_code=400, detail="No active WhatsApp account configured")

        # Create scheduled message
        scheduled_message = ScheduledMessage(
            tenant_id=tenant.id,
            whatsapp_account_id=whatsapp_account.id,
            to_number=to,
            message=message,
            message_type=message_type,
            scheduled_at=scheduled_time,
            timezone=timezone,
            status="scheduled"
        )

        db.add(scheduled_message)
        db.commit()
        db.refresh(scheduled_message)

        logger.info(f"📅 Message scheduled for {scheduled_time}: {scheduled_message.id} for tenant {tenant.id}")

        return ScheduledMessageResponse(
            scheduled_message_id=str(scheduled_message.id),
            status="scheduled",
            scheduled_at=scheduled_message.scheduled_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Scheduling failed for tenant {tenant.id}: {e}")
        raise HTTPException(status_code=500, detail="Message scheduling failed")
    finally:
        db.close()

# ------------------ GET ROUTE ------------------

@router.get("/scheduled")
async def get_scheduled_messages(
    request: Request,
    x_tenant_id: str = Header(None)  # ✅ Added here too
):
    """Retrieve all scheduled messages for the current tenant."""
    tenant = get_tenant_from_request(request)
    db = SessionLocal()

    try:
        messages = db.query(ScheduledMessage).filter(
            ScheduledMessage.tenant_id == tenant.id
        ).order_by(ScheduledMessage.scheduled_at.asc()).all()

        logger.debug(f"📋 Retrieved {len(messages)} scheduled messages for tenant {tenant.id}")

        return {
            "scheduled_messages": [
                {
                    "id": str(msg.id),
                    "to_number": msg.to_number,
                    "message": msg.message,
                    "scheduled_at": msg.scheduled_at.isoformat(),
                    "status": msg.status,
                    "attempts": msg.attempts,
                    "sent_at": msg.sent_at.isoformat() if msg.sent_at else None
                }
                for msg in messages
            ]
        }

    except Exception as e:
        logger.error(f"❌ Failed to fetch scheduled messages for tenant {tenant.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch scheduled messages")
    finally:
        db.close()

# ------------------ DELETE ROUTE ------------------

@router.delete("/scheduled/{message_id}")
async def cancel_scheduled_message(
    request: Request,
    message_id: str,
    x_tenant_id: str = Header(None)  # ✅ Added here too
):
    """Cancel a scheduled message."""
    tenant = get_tenant_from_request(request)
    db = SessionLocal()

    try:
        message = db.query(ScheduledMessage).filter(
            ScheduledMessage.id == message_id,
            ScheduledMessage.tenant_id == tenant.id
        ).first()

        if not message:
            raise HTTPException(status_code=404, detail="Scheduled message not found")

        if message.status != "scheduled":
            raise HTTPException(status_code=400, detail="Only scheduled messages can be cancelled")

        message.status = "cancelled"
        db.commit()

        logger.info(f"❌ Scheduled message cancelled: {message_id} for tenant {tenant.id}")

        return {"message": "Scheduled message cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to cancel message {message_id} for tenant {tenant.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel scheduled message")
    finally:
        db.close()