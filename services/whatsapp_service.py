import requests
import json
import asyncio
from typing import Dict, Any, Optional
from loguru import logger

class WhatsAppService:
    """
    Service to handle all WhatsApp Business API operations
    """
    
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v18.0"
        logger.info("WhatsApp Service initialized")
    
    async def send_message(
        self, 
        to: str,
        message: str,
        message_type: str = "text",
        phone_number_id: str = None,
        access_token: str = None
    ) -> bool:
        """
        Send a message via WhatsApp Business API
        This is the method called by the scheduled message worker
        """
        logger.info(f"📤 Sending {message_type} message to {to}")
        
        # Format phone number (remove any spaces/special characters)
        to_number = ''.join(filter(str.isdigit, to))
        
        # For scheduled messages, you might need to get phone_number_id and access_token from database
        # For now, using parameters or environment variables
        if not phone_number_id or not access_token:
            # Try to get from environment or database
            # You might want to modify this based on your setup
            from database.session import SessionLocal
            from database.models import WhatsAppAccount
            
            db = SessionLocal()
            try:
                # Get the first active WhatsApp account
                # In production, you might want to get tenant-specific account
                whatsapp_account = db.query(WhatsAppAccount).filter(
                    WhatsAppAccount.is_active == True
                ).first()
                
                if whatsapp_account:
                    phone_number_id = whatsapp_account.phone_number_id
                    access_token = whatsapp_account.access_token
                else:
                    logger.error("❌ No active WhatsApp account found")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Failed to get WhatsApp account: {e}")
                return False
            finally:
                db.close()
        
        if message_type == "text":
            return await self.send_text_message(phone_number_id, access_token, to_number, message)
        else:
            # For other message types, use text as fallback
            logger.warning(f"⚠️ Message type '{message_type}' not fully implemented, using text")
            return await self.send_text_message(phone_number_id, access_token, to_number, message)
    
    async def send_text_message(
        self, 
        phone_number_id: str,
        access_token: str,
        to_number: str, 
        message: str
    ) -> bool:
        """
        Send a text message via WhatsApp Business API
        Returns: bool (success status)
        """
        logger.info(f"💬 Sending text message to {to_number}")
        
        # Prepare the message payload
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {
                "body": message
            }
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/{phone_number_id}/messages"
        
        try:
            logger.info(f"🔗 Calling WhatsApp API: {url}")
            
            # Use async HTTP client in production (aiohttp)
            # For now using requests with async wrapper
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(url, json=payload, headers=headers, timeout=30)
            )
            
            if response.status_code == 200:
                result = response.json()
                message_id = result.get("messages", [{}])[0].get("id")
                logger.success(f"✅ Message sent successfully! ID: {message_id}")
                return True
            else:
                error_msg = f"WhatsApp API error: {response.status_code} - {response.text}"
                logger.error(f"❌ {error_msg}")
                return False
                
        except Exception as e:
            error_msg = f"Failed to send message: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False
    
    async def send_template_message(
        self,
        phone_number_id: str,
        access_token: str,
        to_number: str,
        template_name: str,
        language_code: str = "en"
    ) -> bool:
        """
        Send a template message (for approved templates)
        Returns: bool (success status)
        """
        logger.info(f"📤 Sending template '{template_name}' to {to_number}")
        
        to_number = ''.join(filter(str.isdigit, to_number))
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/{phone_number_id}/messages"
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(url, json=payload, headers=headers, timeout=30)
            )
            response.raise_for_status()
            
            result = response.json()
            message_id = result.get("messages", [{}])[0].get("id")
            logger.success(f"✅ Template message sent! ID: {message_id}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to send template: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False
    
    async def mark_message_as_read(
        self,
        phone_number_id: str,
        access_token: str,
        message_id: str
    ) -> bool:
        """
        Mark a message as read
        """
        try:
            payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url}/{phone_number_id}/messages"
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(url, json=payload, headers=headers, timeout=10)
            )
            response.raise_for_status()
            
            logger.info(f"✅ Message {message_id} marked as read")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to mark message as read: {e}")
            return False

# Create a global instance
whatsapp_service = WhatsAppService()