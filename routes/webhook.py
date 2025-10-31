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
    """Process incoming WhatsApp messages with smart replies"""
    try:
        entries = message_data.get('entry', [])
        
        for entry in entries:
            changes = entry.get('changes', [])
            
            for change in changes:
                value = change.get('value', {})
                messages = value.get('messages', [])
                
                for message in messages:
                    from_number = message.get('from')
                    
                    # Handle different message types
                    if 'text' in message:
                        message_text = message.get('text', {}).get('body', '').lower()
                        logger.info(f"💬 Received from {from_number}: {message_text}")
                        
                        # SMART AUTO-REPLY BASED ON CONTENT
                        auto_reply = generate_smart_reply(message_text)
                        await send_whatsapp_message(from_number, auto_reply)
                    
                    elif 'image' in message:
                        image_id = message.get('image', {}).get('id')
                        logger.info(f"🖼️ Received image from {from_number}")
                        await send_whatsapp_message(from_number, "Thanks for the image! 📸 I'll share it with our team.")
                    
                    elif 'audio' in message:
                        audio_id = message.get('audio', {}).get('id')
                        logger.info(f"🎵 Received audio from {from_number}")
                        await send_whatsapp_message(from_number, "Got your voice message! 🎤 Our team will listen and respond shortly.")
                    
                    elif 'document' in message:
                        doc_id = message.get('document', {}).get('id')
                        logger.info(f"📄 Received document from {from_number}")
                        await send_whatsapp_message(from_number, "Thanks for the document! 📁 We've received it.")
                    
                    elif 'video' in message:
                        video_id = message.get('video', {}).get('id')
                        logger.info(f"🎥 Received video from {from_number}")
                        await send_whatsapp_message(from_number, "Thanks for the video! 🎬 We'll review it.")
                    
                    else:
                        logger.info(f"📱 Received message from {from_number}")
                        await send_whatsapp_message(from_number, "Thanks for your message! Our team will respond shortly. 👍")
                        
    except Exception as e:
        logger.error(f"❌ Error processing incoming message: {e}")

def generate_smart_reply(message_text: str) -> str:
    """Generate intelligent replies based on message content"""
    message_text = message_text.lower()
    
    # ========================
    # GREETINGS & BASIC
    # ========================
    if any(word in message_text for word in ['hi', 'hello', 'hey', 'hola', 'namaste','hlo']):
        return "Hello! 👋 Thanks for reaching out. How can I help you today?"
    
    elif any(word in message_text for word in ['good morning', 'gm','gud mrng']):
        return "Good morning! ☀️ How can I assist you today?"
    
    elif any(word in message_text for word in ['good afternoon']):
        return "Good afternoon! 🌞 What can I help you with?"
    
    elif any(word in message_text for word in ['good evening', 'good night','gn']):
        return "Good evening! 🌙 How can I help you?"
    
    # ========================
    # ORDERS & DELIVERY
    # ========================
    elif any(word in message_text for word in ['status', 'track', 'where is', 'when', 'delivery']):
        return "To check your order status, please share your order number. I'll look it up for you! 📦"
    
    elif any(word in message_text for word in ['order', 'booking', 'reservation']):
        return "For order assistance, please share your order number or booking details. I'll check it right away! 📋"
    
    elif any(word in message_text for word in ['cancel', 'cancellation']):
        return "I can help with cancellations! Please share your order number and we'll process it. ❌"
    
    elif any(word in message_text for word in ['return', 'refund']):
        return "For returns/refunds, please share your order details. We'll guide you through the process! 🔄"
    
    elif any(word in message_text for word in ['late', 'delay', 'not received']):
        return "I'm sorry for the delay! 🕒 Please share your order number so I can check the status immediately."
    
    # ========================
    # PRICING & PAYMENTS
    # ========================
    elif any(word in message_text for word in ['price', 'cost', 'how much', 'rate', 'charges']):
        return "I'd be happy to help with pricing! 💰 Could you let me know which product or service you're interested in?"
    
    elif any(word in message_text for word in ['discount', 'offer', 'coupon', 'promo']):
        return "We have various offers available! 🎁 Please visit our website or let me know what you're looking for."
    
    elif any(word in message_text for word in ['payment', 'pay', 'bill', 'invoice']):
        return "For payment assistance, please share your order number. I'll check your invoice! 💳"
    
    # ========================
    # SUPPORT & HELP
    # ========================
    elif any(word in message_text for word in ['help', 'support', 'problem', 'issue']):
        return "I'm here to help! 🛠️ Please describe your issue and I'll connect you with our support team."
    
    elif any(word in message_text for word in ['complaint', 'wrong', 'bad', 'not working', 'broken']):
        return "I'm sorry you're having issues! 😔 Please share details and we'll resolve it immediately."
    
    elif any(word in message_text for word in ['urgent', 'emergency', 'asap', 'important']):
        return "I understand this is urgent! ⚡ Please share details and we'll prioritize your request."
    
    # ========================
    # BUSINESS INFO
    # ========================
    elif any(word in message_text for word in ['time', 'hour', 'open', 'close', 'timing']):
        return "We're open Monday-Friday 9AM-6PM and Saturday 10AM-4PM. 🕘 How can we assist you?"
    
    elif any(word in message_text for word in ['where', 'location', 'address', 'place']):
        return "We're located at 123 Business Street, City. 🗺️ Would you like directions or more location details?"
    
    elif any(word in message_text for word in ['contact', 'phone', 'number', 'call']):
        return "You can reach us at +1-234-567-8900 📞 or email support@business.com. How can we help?"
    
    elif any(word in message_text for word in ['website', 'online', 'portal']):
        return "Visit our website at www.business.com 🌐 for more information. How else can I assist?"
    
    # ========================
    # PRODUCTS & SERVICES
    # ========================
    elif any(word in message_text for word in ['product', 'item', 'menu', 'catalog', 'service']):
        return "I can help you browse our products/services! 🛍️ What are you looking for specifically?"
    
    elif any(word in message_text for word in ['available', 'stock', 'in stock']):
        return "I can check availability for you! Please let me know which product you're interested in. 📊"
    
    elif any(word in message_text for word in ['feature', 'specification', 'detail']):
        return "I'd be happy to share product details! Please specify which product you're asking about. 📝"
    
    # ========================
    # POSITIVE FEEDBACK
    # ========================
    elif any(word in message_text for word in ['thank', 'thanks', 'appreciate']):
        return "You're welcome! 😊 Is there anything else I can help you with?"
    
    elif any(word in message_text for word in ['good', 'great', 'awesome', 'love', 'amazing', 'excellent']):
        return "Thank you for the kind words! 😊 We're happy to serve you!"
    
    elif any(word in message_text for word in ['perfect', 'nice', 'wonderful']):
        return "Glad to hear that! 😄 Thanks for your feedback!"
    
    # ========================
    # TECHNICAL
    # ========================
    elif any(word in message_text for word in ['app', 'application', 'login', 'password']):
        return "For app/login issues, please contact our tech support at tech@business.com or call +1-234-567-8901. 💻"
    
    elif any(word in message_text for word in ['update', 'upgrade']):
        return "For updates or upgrades, please visit our website or contact sales@business.com. 🔄"
    
    # ========================
    # GENERAL INQUIRIES
    # ========================
    elif any(word in message_text for word in ['what', 'how', 'why', 'when', 'where']):
        return "I'd be happy to answer your question! 🤔 Could you please provide more details?"
    
    elif any(word in message_text for word in ['information', 'info', 'detail']):
        return "I can provide information! Please let me know what specific details you need. 📚"
    
    # ========================
    # DEFAULT REPLY
    # ========================
    else:
        return "Thanks for your message! I understand you're saying: '" + message_text + "'. Our team will respond with more specific help shortly. 💬"

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