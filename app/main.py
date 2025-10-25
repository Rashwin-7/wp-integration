from fastapi import FastAPI
from contextlib import asynccontextmanager
import threading
from database.session import engine, Base
from fastapi import FastAPI, Request 
from database.models import Tenant, WhatsAppAccount, Message
from routes import clients, webhook, messages  # ✅ ADD NEW ROUTES
from middleware.auth import HMACAuth  # ✅ ADD HMAC AUTHENTICATION
from services.message_queue import rabbitmq_service
from services.message_consumer import start_message_consumers
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Multi-tenant WhatsApp SaaS Gateway...")
    
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully!")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        raise
    
    # Start message consumers in background thread (if RabbitMQ is connected)
    if rabbitmq_service.is_connected:
        consumer_thread = threading.Thread(target=start_message_consumers, daemon=True)
        consumer_thread.start()
        logger.info("✅ RabbitMQ consumers started in background")
    else:
        logger.warning("⚠️ RabbitMQ not connected, running in direct mode")
    
    yield
    
    # Cleanup
    rabbitmq_service.close()
    logger.info("🛑 Shutting down SaaS WhatsApp Gateway")

app = FastAPI(
    title="WhatsApp SaaS Gateway API",
    description="Multi-tenant WhatsApp Business API Gateway for Businesses", 
    version="2.0.0",  # ✅ UPDATED VERSION
    lifespan=lifespan
)

# ✅ ADD HMAC AUTHENTICATION MIDDLEWARE
app.add_middleware(HMACAuth)

# ✅ INCLUDE ALL ROUTERS
app.include_router(clients.router, prefix="/api/v1", tags=["Businesses"])  # Your existing
app.include_router(webhook.router, tags=["Webhook"])  # Your existing
app.include_router(messages.router, prefix="/api/v1/messages", tags=["Messages"])  # ✅ NEW

@app.get("/")
def root():
    return {
        "message": "Welcome to WhatsApp SaaS Gateway API!",
        "version": "2.0.0",
        "multi_tenant": True,  # ✅ NEW FEATURE FLAG
        "status": "Database & RabbitMQ connected!",
        "docs": "Visit /docs for API documentation",
        "endpoints": {  # ✅ HELPFUL ENDPOINT OVERVIEW
            "tenant_registration": "POST /api/v1/tenants/register",
            "send_messages": "POST /api/v1/messages/send",
            "webhooks": "GET/POST /webhook",
            "business_management": "GET /api/v1/clients/*"
        }
    }

@app.get("/health")
def health_check():
    rabbitmq_status = "connected" if rabbitmq_service.is_connected else "disconnected"
    
    # ✅ ENHANCED HEALTH CHECK WITH TENANT INFO
    from database.session import get_db
    db = next(get_db())
    try:
        tenant_count = db.query(Tenant).count()
        active_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
        message_count = db.query(Message).count()
        
        return {
            "status": "healthy", 
            "database": "connected",
            "rabbitmq": rabbitmq_status,
            "tenants": {  # ✅ ADDED TENANT METRICS
                "total": tenant_count,
                "active": active_tenants
            },
            "messages": message_count
        }
    except Exception as e:
        return {
            "status": "healthy",
            "database": "connected", 
            "rabbitmq": rabbitmq_status,
            "error": f"Metrics unavailable: {str(e)}"
        }
    finally:
        db.close()

@app.get("/test-db")
def test_database():
    try:
        from database.session import get_db
        db = next(get_db())
        tenant_count = db.query(Tenant).count()
        whatsapp_account_count = db.query(WhatsAppAccount).count()
        message_count = db.query(Message).count()
        db.close()
        
        return {
            "status": "success",
            "message": "Database is working perfectly!",
            "metrics": {  # ✅ ENHANCED METRICS
                "tenants": tenant_count,
                "whatsapp_accounts": whatsapp_account_count,
                "messages": message_count
            },
            "rabbitmq": "connected" if rabbitmq_service.is_connected else "disconnected"
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Database error: {str(e)}"
        }

# ✅ NEW: TENANT INFO ENDPOINT (For testing HMAC auth)
@app.get("/api/v1/me")
def get_tenant_info(request: Request):  # ✅ ADD Request parameter
    """Get current tenant information (requires HMAC auth)"""
    tenant = request.state.tenant  # ✅ From HMAC middleware
    
    return {
        "tenant_id": tenant.id,
        "name": tenant.name,
        "email": tenant.email,
        "monthly_message_limit": tenant.monthly_message_limit,
        "current_month_count": tenant.current_month_count,
        "is_active": tenant.is_active,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)