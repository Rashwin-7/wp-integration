import hmac
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from database.session import get_db
from database.models import Tenant, RateLimit
from core.config import settings

class SecurityManager:
    """Enterprise security manager for authentication and authorization"""
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate cryptographically secure API key"""
        return f"wp_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def generate_hmac_signature(payload: str) -> str:
        """Generate HMAC signature for webhook verification"""
        signature = hmac.new(
            settings.HMAC_SECRET.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    @staticmethod
    def verify_hmac_signature(payload: str, signature: str) -> bool:
        """Verify HMAC signature for webhooks"""
        expected_signature = SecurityManager.generate_hmac_signature(payload)
        return hmac.compare_digest(expected_signature, signature)
    
    @staticmethod
    def verify_api_key(api_key: str, db: Session) -> Optional[Tenant]:
        """Verify API key and return tenant with enhanced security"""
        if not api_key or not api_key.startswith("wp_"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key format"
            )
        
        tenant = db.query(Tenant).filter(
            Tenant.api_key == api_key, 
            Tenant.is_active == True
        ).first()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key or tenant inactive"
            )
        
        return tenant
    
    @staticmethod
    def check_rate_limit(tenant_id: str, db: Session) -> bool:
        """Check if tenant has exceeded rate limit"""
        if not settings.ENABLE_RATE_LIMITING:
            return True
            
        current_window = datetime.utcnow().replace(second=0, microsecond=0)
        
        # Check minute-based rate limiting
        rate_limit = db.query(RateLimit).filter(
            RateLimit.tenant_id == tenant_id,
            RateLimit.window_start == current_window,
            RateLimit.window_size == "minute"
        ).first()
        
        if not rate_limit:
            # Create new rate limit window
            rate_limit = RateLimit(
                tenant_id=tenant_id,
                window_start=current_window,
                window_size="minute",
                request_count=1
            )
            db.add(rate_limit)
        else:
            if rate_limit.request_count >= settings.RATE_LIMIT_PER_MINUTE:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. {settings.RATE_LIMIT_PER_MINUTE} requests per minute allowed."
                )
            rate_limit.request_count += 1
        
        db.commit()
        return True
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT token for admin operations"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
        return encoded_jwt
    
    @staticmethod
    def verify_access_token(token: str):
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

# ==================== FASTAPI DEPENDENCIES ====================

async def get_current_tenant(
    request: Request,
    api_key: str = Header(..., alias=settings.API_KEY_HEADER),
    db: Session = Depends(get_db)
) -> Tenant:
    """
    Dependency to get current tenant with rate limiting
    """
    # Verify API key
    tenant = SecurityManager.verify_api_key(api_key, db)
    
    # Check rate limit
    SecurityManager.check_rate_limit(tenant.id, db)
    
    # Log the request (optional)
    request.state.tenant = tenant
    
    return tenant

async def verify_webhook_signature(request: Request):
    """
    Dependency to verify webhook HMAC signature
    """
    if not settings.ENABLE_WEBHOOK_VERIFICATION:
        return True
        
    signature = request.headers.get("X-Hub-Signature-256", "").replace("sha256=", "")
    
    body = await request.body()
    payload = body.decode('utf-8')
    
    if not SecurityManager.verify_hmac_signature(payload, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    return True

class RateLimiter:
    """Custom rate limiter for specific endpoints"""
    
    def __init__(self, times: int, seconds: int):
        self.times = times
        self.seconds = seconds
    
    async def __call__(self, request: Request):
        # Implementation for custom rate limiting
        # You can integrate with Redis for distributed rate limiting
        pass