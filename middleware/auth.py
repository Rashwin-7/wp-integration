import hmac
import hashlib
import time
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from database.session import SessionLocal
from database.models import Tenant, APILog
import logging

logger = logging.getLogger(__name__)

class HMACAuth(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth for public routes
        public_paths = [
            '/docs', '/redoc', '/openapi.json', 
            '/webhook', '/api/v1/tenants/register', 
            '/health', '/', '/test-db',
            '/tenants/', 
            '/api/v1/me' 
        ]
        
        if any(request.url.path == path or request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)
        
        return await self.verify_hmac(request, call_next)
    
    async def verify_hmac(self, request: Request, call_next):
        start_time = time.time()
        db = SessionLocal()
        
        try:
            # Get headers
            client_id = request.headers.get('X-Client-ID')
            signature = request.headers.get('X-Signature')
            timestamp = request.headers.get('X-Timestamp')
            
            if not all([client_id, signature, timestamp]):
                await self.log_api_call(db, None, request, 401, start_time, "Missing headers")
                raise HTTPException(status_code=401, detail="Missing authentication headers")
            
            # Validate timestamp (prevent replay attacks)
            if abs(int(time.time()) - int(timestamp)) > 300:  # 5 minutes
                await self.log_api_call(db, None, request, 401, start_time, "Invalid timestamp")
                raise HTTPException(status_code=401, detail="Invalid timestamp")
            
            # Get tenant
            tenant = db.query(Tenant).filter(
                Tenant.api_key == client_id,
                Tenant.is_active == True
            ).first()
            
            if not tenant:
                await self.log_api_call(db, None, request, 401, start_time, "Invalid client ID")
                raise HTTPException(status_code=401, detail="Invalid client ID")
            
            # ✅ FIX: Store the body bytes for signature verification
            body_bytes = await request.body()
            
            # ✅ CRITICAL FIX: Re-create the request with the body for downstream use
            async def receive():
                return {'type': 'http.request', 'body': body_bytes, 'more_body': False}
            
            # Verify HMAC signature
            body_str = body_bytes.decode() if body_bytes else ""
            message = f"{timestamp}.{body_str}"
            expected_signature = hmac.new(
                key=tenant.hmac_secret.encode('utf-8'),
                msg=message.encode('utf-8'),
                digestmod=hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(expected_signature, signature):
                await self.log_api_call(db, tenant.id, request, 401, start_time, "Invalid signature")
                raise HTTPException(status_code=401, detail="Invalid signature")
            
            # Add tenant to request state
            request.state.tenant = tenant
            
            # Log successful auth
            response_time = int((time.time() - start_time) * 1000)
            await self.log_api_call(db, tenant.id, request, 200, response_time)
            
            # ✅ FIX: Create a new request with the original body
            from starlette.requests import Request
            new_request = Request(request.scope, receive)
            
            # Continue to the next middleware/route with the restored request
            response = await call_next(new_request)
            return response
            
        except HTTPException as e:
            return Response(
                content={"detail": e.detail},
                status_code=e.status_code,
                media_type="application/json"
            )
        except Exception as e:
            logger.error(f"Auth error: {e}")
            await self.log_api_call(db, None, request, 500, start_time, str(e))
            return Response(
                content={"detail": "Authentication error"},
                status_code=500,
                media_type="application/json"
            )
        finally:
            db.close()
    
    async def log_api_call(self, db, tenant_id, request, status_code, start_time, error_msg=None):
        try:
            response_time = int((time.time() - start_time) * 1000)
            
            api_log = APILog(
                tenant_id=tenant_id,
                endpoint=request.url.path,
                method=request.method,
                status_code=status_code,
                response_time=response_time,
                user_agent=request.headers.get('user-agent'),
                ip_address=request.client.host if request.client else None,
                error_message=error_msg
            )
            
            db.add(api_log)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to log API call: {e}")