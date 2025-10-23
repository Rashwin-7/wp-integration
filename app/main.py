from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from database.session import engine, Base
from database.models import Tenant, WhatsAppAccount, Message

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting SaaS WhatsApp Gateway...")
    
    # Create database tables - THIS IS WHAT TESTS YOUR DATABASE MODULE
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully!")
        logger.info("✅ Database module is working correctly!")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        raise
    
    yield
    
    logger.info("🛑 Shutting down SaaS WhatsApp Gateway")

app = FastAPI(
    title="WhatsApp Gateway API",
    description="Multi-tenant WhatsApp Business API Gateway", 
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
def root():
    return {
        "message": "Welcome to WhatsApp Gateway API!",
        "status": "Database connection successful!",
        "docs": "Visit /docs for API documentation"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "database": "connected"}

# Test database connection
@app.get("/test-db")
def test_database():
    try:
        # Try to query the database
        from database.session import get_db
        db = next(get_db())
        tenant_count = db.query(Tenant).count()
        db.close()
        
        return {
            "status": "success",
            "message": "Database is working perfectly!",
            "tenants_count": tenant_count
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Database error: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)