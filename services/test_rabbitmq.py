import pika
import sys

def test_rabbitmq_connection():
    print("🧪 Testing RabbitMQ connection...")
    
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        print("✅ RabbitMQ connection successful!")
        
        channel = connection.channel()
        print("✅ RabbitMQ channel created!")
        
        # Test queue declaration
        channel.queue_declare(queue='test_queue', durable=True)
        print("✅ Queue declaration successful!")
        
        connection.close()
        print("✅ Connection closed properly!")
        
    except Exception as e:
        print(f"❌ RabbitMQ connection failed: {e}")
        print("💡 TROUBLESHOOTING:")
        print("1. Is RabbitMQ running? Try: sudo systemctl start rabbitmq-server")
        print("2. Check if port 5672 is open")
        print("3. Check RabbitMQ logs")

if __name__ == "__main__":
    test_rabbitmq_connection()