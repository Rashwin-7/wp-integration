import pika
import json
import time
from typing import Dict, Any
from loguru import logger

class RabbitMQService:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.is_connected = False
        self.max_retries = 3
        self.retry_delay = 5
        
        # ✅ ENABLE AUTO-CONNECT NOW THAT RABBITMQ IS RUNNING
        self.connect()
    
    def connect(self, retry_count=0):
        """Connect to RabbitMQ with retry logic"""
        try:
            logger.info("🔗 Connecting to RabbitMQ...")
            
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host='localhost',
                    port=5672,
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
            )
            
            self.channel = self.connection.channel()
            
            # Create queues
            self.channel.queue_declare(queue='outgoing_messages', durable=True)
            self.channel.queue_declare(queue='incoming_messages', durable=True)
            self.channel.queue_declare(queue='webhook_notifications', durable=True)
            
            self.is_connected = True
            logger.success("✅ Connected to RabbitMQ successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ (attempt {retry_count + 1}/{self.max_retries}): {e}")
            
            if retry_count < self.max_retries:
                logger.info(f"🔄 Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
                self.connect(retry_count + 1)
            else:
                logger.error("🚨 Max retries reached. RabbitMQ connection failed.")
                self.is_connected = False

    def ensure_connection(self):
        """Ensure we have a connection"""
        if not self.is_connected or self.connection is None or self.connection.is_closed:
            self.connect()

    def send_message(self, queue_name: str, message_data: Dict[str, Any]):
        """Send message to queue with error handling"""
        try:
            self.ensure_connection()
            
            self.channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=json.dumps(message_data),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            logger.debug(f"📨 Message sent to '{queue_name}': {message_data}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send message to '{queue_name}': {e}")
            self.is_connected = False
            return False

    # ✅ ADD THIS MISSING METHOD
    def close(self):
        """Close connection gracefully"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                self.is_connected = False
                logger.info("🔌 RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing RabbitMQ connection: {e}")

# Global instance
rabbitmq_service = RabbitMQService()