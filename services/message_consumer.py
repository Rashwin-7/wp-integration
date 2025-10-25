import json
import time
import requests
import os
from dotenv import load_dotenv
from loguru import logger
from services.message_queue import rabbitmq_service

# Load environment variables from .env file
load_dotenv()

def process_outgoing_message(message_data: dict):
    """Process messages and send to WhatsApp API"""
    logger.info(f"🔄 Processing queued message: {message_data}")
    
    try:
        # Extract data
        to_number = message_data.get('to') or message_data.get('to_number')
        message_content = message_data.get('message') or message_data.get('content')
        
        logger.info(f"📞 To: {to_number}")
        logger.info(f"💬 Message: {message_content}")
        
        if not to_number or not message_content:
            logger.error("❌ Missing 'to' or 'message' in data")
            return False
        
        # Get WhatsApp credentials - TEMPORARILY HARCODED FOR TESTING
        # Replace these with your ACTUAL credentials from Facebook Developer Console
        phone_number_id = "902614526258424"  # ⚠️ REPLACE WITH YOUR REAL PHONE NUMBER ID
        access_token = "EAAORRjYfA6oBP5ZBH2gnvHUDd1RGZAoqAFoNQAzMsMSu5654OJEyEkVle1fTtJ7MSJFyZBCT1CeRzNVpyJhJ0rEsZAr59QTs1HCuMVUNpZCQbV9OvHvzaRxCbbNpXUeAdL3yAxMwT0bGWoeZCoWZA3ZBwDO4fcZCZAB2ZC4ApZA1K0IX2v4ja6NzuHZAdYAg2UzjRlwZDZD"  # ⚠️ REPLACE WITH YOUR REAL ACCESS TOKEN
        
        # Debug: Show what credentials we're using
        print(f"🔍 DEBUG: Using Phone Number ID: {phone_number_id}")
        print(f"🔍 DEBUG: Using Access Token: {access_token[:20]}..." if access_token and len(access_token) > 20 else "None")
        
        if not phone_number_id or not access_token:
            logger.error("❌ Missing WhatsApp credentials")
            return False
        
        # WhatsApp API URL
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "text": {"body": message_content}
        }
        
        logger.info(f"📤 Sending to WhatsApp API...")
        logger.info(f"🔗 URL: {url}")
        logger.info(f"📞 Sending to: {to_number}")
        logger.info(f"💬 Message content: {message_content}")
        
        # Make API call
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            logger.success(f"✅ WhatsApp message sent successfully!")
            result = response.json()
            message_id = result.get('messages', [{}])[0].get('id', 'Unknown')
            logger.info(f"📨 Message ID: {message_id}")
            return True
        else:
            logger.error(f"❌ WhatsApp API error: {response.status_code}")
            logger.error(f"📄 Error response: {response.text}")
            
            # Show specific error messages
            if response.status_code == 401:
                logger.error("🔐 Authentication failed - Check your Access Token")
            elif response.status_code == 404:
                logger.error("🔍 Phone Number ID not found - Check your Phone Number ID")
            elif response.status_code == 400:
                logger.error("📱 Bad request - Check phone number format")
            
            return False
            
    except Exception as e:
        logger.error(f"❌ Error in process_outgoing_message: {e}")
        return False

def process_consumer_message(ch, method, properties, body):
    """Process individual messages from RabbitMQ"""
    try:
        message_data = json.loads(body)
        logger.info(f"📨 Received message from RabbitMQ: {message_data}")
        
        # Process the message
        success = process_outgoing_message(message_data)
        
        if success:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"✅ Message acknowledged: {method.delivery_tag}")
        else:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            logger.error(f"❌ Message failed, not requeued: {method.delivery_tag}")
            
    except Exception as e:
        logger.error(f"❌ Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_message_consumers():
    """Start all message consumers"""
    print("🔍 DEBUG: Starting message consumers...")
    
    # Check RabbitMQ connection
    if not rabbitmq_service.is_connected:
        logger.error("❌ Cannot start consumers: RabbitMQ not connected")
        print("🔍 DEBUG: Trying to reconnect to RabbitMQ...")
        
        try:
            rabbitmq_service.connect()
            if rabbitmq_service.is_connected:
                logger.info("✅ Successfully reconnected to RabbitMQ")
            else:
                logger.error("❌ Failed to reconnect to RabbitMQ")
                return
        except Exception as e:
            logger.error(f"❌ Reconnection failed: {e}")
            return
    
    logger.info("🚀 Starting RabbitMQ message consumers...")
    
    try:
        # Ensure channel exists
        if not hasattr(rabbitmq_service, 'channel') or rabbitmq_service.channel is None:
            logger.error("❌ RabbitMQ channel not available")
            return
            
        # ✅ FIXED: Listening to correct queue
        rabbitmq_service.channel.basic_consume(
            queue='outgoing_messages',  # ✅ CORRECT QUEUE NAME
            on_message_callback=process_consumer_message,
            auto_ack=False
        )
        
        logger.info("👂 Consumer started for 'outgoing_messages'")  # ✅ UPDATED LOG
        print("✅ DEBUG: Consumer successfully registered with RabbitMQ!")
        print("✅ DEBUG: Listening to queue: outgoing_messages")
        
        # Start consuming (this will block, so it runs in background thread)
        rabbitmq_service.channel.start_consuming()
        
    except Exception as e:
        logger.error(f"❌ Failed to start consumer: {e}")
        print(f"🔴 DEBUG: Consumer start failed: {e}")