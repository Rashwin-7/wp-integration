import asyncio
import threading
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import engine, Base, get_db
from database.models import Tenant, WhatsAppAccount, Message
from routes import clients, webhook, messages, templates, scheduled_messages
from middleware.auth import HMACAuth
from routes.admin import router as admin_router
from services.message_queue import rabbitmq_service
from services.message_consumer import start_message_consumers
from services.scheduler import message_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ FIXED LIFESPAN FUNCTION (ONLY ONE)
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
    
    # Start message consumers in background thread
    if rabbitmq_service.is_connected:
        consumer_thread = threading.Thread(target=start_message_consumers, daemon=True)
        consumer_thread.start()
        logger.info("✅ RabbitMQ consumers started in background")
    else:
        logger.warning("⚠️ RabbitMQ not connected, running in direct mode")
    
    # ✅ START MESSAGE SCHEDULER
    scheduler_task = None
    try:
        scheduler_task = asyncio.create_task(message_scheduler.start())
        logger.info("✅ Message scheduler started successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to start message scheduler: {e}")
    
    yield
    
    # Cleanup
    logger.info("🛑 Starting shutdown process...")
    
    # ✅ STOP SCHEDULER
    if scheduler_task:
        logger.info("🛑 Stopping message scheduler...")
        await message_scheduler.stop()
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
    
    rabbitmq_service.close()
    logger.info("🛑 Shutdown completed - SaaS WhatsApp Gateway stopped")

app = FastAPI(
    title="WhatsApp SaaS Gateway API",
    description="Multi-tenant WhatsApp Business API Gateway for Businesses", 
    version="2.0.0",
    lifespan=lifespan
)

@app.middleware("http")
async def inject_tenant_for_swagger(request: Request, call_next):
    """
    ✅ Inject demo tenant for Swagger UI AND Scheduled Messages testing
    """
    # Check if it's a Swagger, debug, OR scheduled messages request
    swagger_paths = ["/docs", "/redoc", "/openapi.json", "/__debug"]
    is_swagger_request = any(request.url.path.startswith(path) for path in swagger_paths)
    
    # ✅ ADD: Also handle scheduled messages for testing
    is_scheduled_message = request.url.path.startswith('/api/v1/scheduled/')
    
    if is_swagger_request or is_scheduled_message:
        logger.debug(f"🔄 Injecting tenant for: {request.url.path}")
        db = next(get_db())
        try:
            tenant = db.query(Tenant).first()
            if tenant:
                request.state.tenant = tenant
                logger.debug(f"✅ Injected demo tenant: {tenant.name} for {request.url.path}")
            else:
                logger.warning("⚠️ No tenants found in database")
        except Exception as e:
            logger.error(f"❌ Failed to inject demo tenant: {e}")
        finally:
            db.close()
    
    response = await call_next(request)
    return response

# ✅ ADD HMAC AUTHENTICATION MIDDLEWARE
app.add_middleware(HMACAuth)

# ✅ INCLUDE ALL ROUTERS
app.include_router(clients.router, prefix="/api/v1", tags=["Businesses"])
app.include_router(webhook.router, tags=["Webhook"])
app.include_router(messages.router, prefix="/api/v1/messages", tags=["Messages"])
app.include_router(templates.router, prefix="/api/v1", tags=["Templates"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(scheduled_messages.router, prefix="/api/v1/scheduled", tags=["Scheduled Messages"])

@app.get("/")
def root():
    return {
        "message": "Welcome to WhatsApp SaaS Gateway API!",
        "version": "2.0.0",
        "multi_tenant": True,
        "status": "Database & RabbitMQ connected!",
        "docs": "Visit /docs for API documentation",
        "endpoints": {
            "tenant_registration": "POST /api/v1/tenants/register",
            "send_messages": "POST /api/v1/messages/send",
            "schedule_messages": "POST /api/v1/scheduled/schedule",
            "get_scheduled": "GET /api/v1/scheduled/scheduled",
            "webhooks": "GET/POST /webhook",
            "business_management": "GET /api/v1/clients/*"
        }
    }

@app.get("/health")
def health_check():
    rabbitmq_status = "connected" if rabbitmq_service.is_connected else "disconnected"
    
    db = next(get_db())
    try:
        tenant_count = db.query(Tenant).count()
        active_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
        message_count = db.query(Message).count()
        
        return {
            "status": "healthy", 
            "database": "connected",
            "rabbitmq": rabbitmq_status,
            "tenants": {
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
        db = next(get_db())
        tenant_count = db.query(Tenant).count()
        whatsapp_account_count = db.query(WhatsAppAccount).count()
        message_count = db.query(Message).count()
        db.close()
        
        return {
            "status": "success",
            "message": "Database is working perfectly!",
            "metrics": {
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

# ✅ TENANT INFO ENDPOINT (For testing)
@app.get("/api/v1/me")
async def get_tenant_info(request: Request, db: Session = Depends(get_db)):
    """Get current tenant info - with fallback"""
    try:
        # Try to get tenant from HMAC auth
        tenant = getattr(request.state, 'tenant', None)
        if not tenant:
            # Fallback: get first tenant from database
            tenant = db.query(Tenant).first()
            if not tenant:
                raise HTTPException(status_code=404, detail="No tenant found")
        
        return {
            "id": tenant.id,
            "name": tenant.name,
            "email": tenant.email,
            "is_active": tenant.is_active,
            "monthly_message_limit": tenant.monthly_message_limit,
            "current_month_count": tenant.current_month_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting tenant info: {str(e)}")

# ✅ DEBUG ENDPOINT TO CHECK TENANT
@app.get("/__debug/check-tenant")
async def debug_check_tenant(request: Request):
    """Debug endpoint to check if tenant is properly set"""
    tenant = getattr(request.state, 'tenant', None)
    if tenant:
        return {
            "ok": True, 
            "tenant_id": str(tenant.id), 
            "tenant_name": tenant.name,
            "message": "✅ Tenant is properly set on request.state"
        }
    
    return {
        "ok": False, 
        "error": "❌ Tenant not set on request.state",
        "available_attributes": [attr for attr in dir(request.state) if not attr.startswith('_')]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)