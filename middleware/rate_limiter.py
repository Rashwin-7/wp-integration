from database.session import SessionLocal
from database.models import RateLimitLog, Tenant
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

async def check_rate_limit(tenant_id: str) -> bool:
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return False
        
        now = datetime.utcnow()
        window_start = now.replace(second=0, microsecond=0)
        window_end = window_start + timedelta(minutes=1)
        
        # Get or create rate limit log for this minute
        rate_log = db.query(RateLimitLog).filter(
            RateLimitLog.tenant_id == tenant_id,
            RateLimitLog.window_start == window_start,
            RateLimitLog.window_end == window_end,
            RateLimitLog.limit_type == 'minute'
        ).first()
        
        if not rate_log:
            rate_log = RateLimitLog(
                tenant_id=tenant_id,
                window_start=window_start,
                window_end=window_end,
                limit_type='minute',
                request_count=0
            )
            db.add(rate_log)
        
        # Check if limit exceeded
        if rate_log.request_count >= tenant.rate_limit_per_minute:
            logger.warning(f"Rate limit exceeded for tenant {tenant_id}")
            return False
        
        # Increment counter
        rate_log.request_count += 1
        db.commit()
        
        return True
        
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()