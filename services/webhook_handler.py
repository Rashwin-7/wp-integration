import json
from typing import Dict, Any
from loguru import logger

class WebhookHandler:
    """
    Service to handle incoming WhatsApp webhooks
    """
    
    @staticmethod
    async def process_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming webhook from WhatsApp
        """
        logger.info("📥 Processing webhook payload")
        
        try:
            for entry in payload.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages':
                        value = change.get('value', {})
                        
                        # Process messages
                        messages = value.get('messages', [])
                        for message in messages:
                            await WebhookHandler._process_message(message)
                        
                        # Process status updates
                        statuses = value.get('statuses', [])
                        for status in statuses:
                            await WebhookHandler._process_status(status)
            
            return {"status": "processed", "message": "Webhook handled successfully"}
            
        except Exception as e:
            logger.error(f"❌ Error processing webhook: {e}")
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    async def _process_message(message_data: Dict[str, Any]):
        """Process individual message"""
        try:
            message_type = message_data.get('type')
            from_number = message_data.get('from')
            message_id = message_data.get('id')
            
            logger.info(f"💬 Received {message_type} message from {from_number}")
            
            # Extract message content based on type
            if message_type == 'text':
                content = message_data.get('text', {}).get('body', '')
                logger.info(f"📝 Message content: {content}")
            
            # Here you would save to database and notify the business
            # For now, just log it
            
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
    
    @staticmethod
    async def _process_status(status_data: Dict[str, Any]):
        """Process message status updates"""
        try:
            message_id = status_data.get('id')
            status = status_data.get('status')
            
            logger.info(f"📊 Message {message_id} status: {status}")
            
            # Here you would update message status in database
            
        except Exception as e:
            logger.error(f"❌ Error processing status: {e}")

# Global instance
webhook_handler = WebhookHandler()