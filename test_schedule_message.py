# test_schedule_message.py
import hmac
import hashlib
import time
import requests
import json
from datetime import datetime, timedelta

# ✅ USE REAL CREDENTIALS FROM YOUR DATABASE
CLIENT_ID = "eef44639-6fcb-463c-a9dc-4f9f900a2805"
HMAC_SECRET = "my_hmac_secret_123"

def generate_hmac_signature(body: str, secret: str) -> tuple:
    timestamp = str(int(time.time()))
    message = f"{timestamp}.{body}"
    signature = hmac.new(
        key=secret.encode('utf-8'),
        msg=message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    return timestamp, signature

# Test data with new format
test_data = {
    "to_number": "+1234567890",  # ✅ Changed from 'to' to 'to_number'
    "message": "Test scheduled message with new format",
    "scheduled_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
    "timezone": "UTC",
    "message_type": "text",
    "template_name": None  # ✅ Added template_name
}

body_str = json.dumps(test_data)
timestamp, signature = generate_hmac_signature(body_str, HMAC_SECRET)

headers = {
    'X-Client-ID': CLIENT_ID,
    'X-Signature': signature,
    'X-Timestamp': timestamp,
    'Content-Type': 'application/json'
}

url = "http://localhost:8000/api/v1/scheduled/schedule"

print("🔐 Testing Schedule Message API...")
print(f"📞 To Number: {test_data['to_number']}")
print(f"💬 Message: {test_data['message']}")
print(f"⏰ Scheduled At: {test_data['scheduled_at']}")
print(f"📝 Message Type: {test_data['message_type']}")
print(f"📋 Template Name: {test_data['template_name']}")

response = requests.post(url, headers=headers, data=body_str)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")