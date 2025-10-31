import asyncio
import logging
from datetime import datetime, timedelta
from database.session import SessionLocal
from database.models import ScheduledMessage, Tenant, WhatsAppAccount
from services.message_queue import rabbitmq_service
from sqlalchemy import and_

logger = logging.getLogger(__name__)

class MessageScheduler:
    def __init__(self, check_interval=60):  # Check every 60 seconds
        self.check_interval = check_interval
        self.is_running = False
    
    async def start(self):
        """Start the scheduler in background"""
        self.is_running = True
        logger.info("🚀 Starting message scheduler...")
        
        while self.is_running:
            try:
                await self.process_due_messages()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(30)  # Wait before retry
    
    async def stop(self):
        """Stop the scheduler"""
        self.is_running = False
        logger.info("🛑 Stopping message scheduler...")
    
    async def process_due_messages(self):
        """Process messages that are due to be sent"""
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            
            # Find due messages (scheduled time has passed, not yet sent/failed)
            due_messages = db.query(ScheduledMessage).filter(
                and_(
                    ScheduledMessage.scheduled_at <= now,
                    ScheduledMessage.status.in_(["scheduled", "failed"]),
                    ScheduledMessage.attempts < ScheduledMessage.max_attempts
                )
            ).all()
            
            if due_messages:
                logger.info(f"📅 Processing {len(due_messages)} due scheduled messages")
            
            for message in due_messages:
                await self.process_single_message(db, message, now)
                
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing scheduled messages: {e}")
        finally:
            db.close()
    
    async def process_single_message(self, db, message, current_time):
        """Process a single scheduled message"""
        try:
            # Update status to processing
            message.status = "processing"
            message.attempts += 1
            message.last_attempt_at = current_time
            db.commit()
            
            # Get tenant's WhatsApp account
            whatsapp_account = db.query(WhatsAppAccount).filter(
                WhatsAppAccount.tenant_id == message.tenant_id,
                WhatsAppAccount.is_active == True
            ).first()
            
            if not whatsapp_account:
                raise Exception("No active WhatsApp account found")
            
            # Queue message for sending
            queue_data = {
                "message_id": message.id,
                "tenant_id": message.tenant_id,
                "whatsapp_account_id": whatsapp_account.id,
                "to_number": message.to_number,
                "content": message.message,
                "message_type": message.message_type,
                "is_scheduled": True
            }
            
            rabbitmq_service.send_message('outgoing_messages', queue_data)
            
            # Update status to sent
            message.status = "sent"
            message.sent_at = current_time
            logger.info(f"✅ Scheduled message sent: {message.id}")
            
        except Exception as e:
            error_msg = str(e)
            message.status = "failed"
            message.error_message = error_msg
            logger.error(f"❌ Failed scheduled message {message.id}: {error_msg}")
            
            # If max attempts reached, mark as permanently failed
            if message.attempts >= message.max_attempts:
                message.status = "permanently_failed"
                logger.error(f"🚫 Scheduled message permanently failed: {message.id}")

# Global scheduler instance
message_scheduler = MessageScheduler()