from fastapi import APIRouter, Request, HTTPException
import requests
from loguru import logger
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter()

@router.get("/webhook")
async def verify_webhook(request: Request):
    """Verify webhook for WhatsApp"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    # Your verify token - use the same one you had or change it
    verify_token = "numota_secret_2025"  # ⚠️ Keep your existing token or change it
    
    logger.info(f"🔐 Webhook verification DETAILS:")
    logger.info(f"   Mode: {mode}")
    logger.info(f"   Token received: {token}")
    logger.info(f"   Token expected: {verify_token}")
    logger.info(f"   Challenge: {challenge}")
    logger.info(f"   Tokens match: {token == verify_token}")
    
    if mode == "subscribe" and token == verify_token:
        logger.success("✅ Webhook verified successfully!")
        return int(challenge)
    else:
        logger.error("❌ Webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/webhook")
async def receive_webhook(request: Request):
    """Receive incoming WhatsApp messages"""
    try:
        body = await request.json()
        logger.info(f"📨 Incoming WhatsApp webhook received")
        
        # Process the incoming message
        await process_incoming_message(body)
        
        return {"status": "ok", "message": "Message processed successfully"}
    except Exception as e:
        logger.error(f"❌ Error in webhook: {e}")
        return {"status": "error", "message": str(e)}

async def process_incoming_message(message_data: dict):
    """Process incoming WhatsApp messages"""
    try:
        # Extract message details from webhook payload
        entries = message_data.get('entry', [])
        
        for entry in entries:
            changes = entry.get('changes', [])
            
            for change in changes:
                value = change.get('value', {})
                messages = value.get('messages', [])
                
                for message in messages:
                    from_number = message.get('from')  # User's phone number
                    
                    # Handle different message types
                    if 'text' in message:
                        message_text = message.get('text', {}).get('body')
                        logger.info(f"💬 Received text from {from_number}: {message_text}")
                        
                        # Auto-reply example
                        if message_text:
                            auto_reply = f"Thanks for your message! You said: '{message_text}'. This is an auto-reply from our WhatsApp bot. 🚀"
                            await send_whatsapp_message(from_number, auto_reply)
                    
                    elif 'image' in message:
                        image_id = message.get('image', {}).get('id')
                        logger.info(f"🖼️ Received image from {from_number}: {image_id}")
                        await send_whatsapp_message(from_number, "Thanks for the image! 📸")
                    
                    elif 'audio' in message:
                        audio_id = message.get('audio', {}).get('id')
                        logger.info(f"🎵 Received audio from {from_number}: {audio_id}")
                        await send_whatsapp_message(from_number, "Thanks for the audio message! 🎤")
                    
                    else:
                        logger.info(f"📱 Received message from {from_number}")
                        await send_whatsapp_message(from_number, "Thanks for your message! 👍")
                        
    except Exception as e:
        logger.error(f"❌ Error processing incoming message: {e}")

async def send_whatsapp_message(to_number: str, message: str):
    """Send WhatsApp message to user"""
    try:
        # Get credentials from environment or use hardcoded
        phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID', '902614526258424')
        access_token = os.getenv('WHATSAPP_ACCESS_TOKEN', 'EAAORRjYfA6oBP5ZBH2gnvHUDd1RGZAoqAFoNQAzMsMSu5654OJEyEkVle1fTtJ7MSJFyZBCT1CeRzNVpyJhJ0rEsZAr59QTs1HCuMVUNpZCQbV9OvHvzaRxCbbNpXUeAdL3yAxMwT0bGWoeZCoWZA3ZBwDO4fcZCZAB2ZC4ApZA1K0IX2v4ja6NzuHZAdYAg2UzjRlwZDZD')
        
        if not access_token or access_token == 'EAAORRjYfA6oBP5ZBH2gnvHUDd1RGZAoqAFoNQAzMsMSu5654OJEyEkVle1fTtJ7MSJFyZBCT1CeRzNVpyJhJ0rEsZAr59QTs1HCuMVUNpZCQbV9OvHvzaRxCbbNpXUeAdL3yAxMwT0bGWoeZCoWZA3ZBwDO4fcZCZAB2ZC4ApZA1K0IX2v4ja6NzuHZAdYAg2UzjRlwZDZD':
            logger.error("❌ WhatsApp access token not configured")
            return
        
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "text": {"body": message}
        }
        
        logger.info(f"📤 Sending auto-reply to {to_number}")
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            logger.success(f"✅ Auto-reply sent successfully to {to_number}")
        else:
            logger.error(f"❌ Failed to send auto-reply: {response.status_code} - {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Error sending WhatsApp message: {e}")