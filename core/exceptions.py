from fastapi import HTTPException
from typing import Any, Dict, Optional

class BusinessException(HTTPException):
    """Base exception for business logic errors"""
    
    def __init__(
        self, 
        message: str, 
        code: str, 
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "error": {
                    "message": message,
                    "code": code,
                    "type": self.__class__.__name__,
                    "details": details or {}
                }
            }
        )

# ==================== TENANT EXCEPTIONS ====================

class TenantNotFoundError(BusinessException):
    def __init__(self, tenant_id: str):
        super().__init__(
            message=f"Tenant {tenant_id} not found",
            code="TENANT_NOT_FOUND",
            status_code=404
        )

class TenantInactiveError(BusinessException):
    def __init__(self, tenant_id: str):
        super().__init__(
            message=f"Tenant {tenant_id} is inactive",
            code="TENANT_INACTIVE",
            status_code=403
        )

class TenantLimitExceededError(BusinessException):
    def __init__(self, tenant_id: str, limit_type: str):
        super().__init__(
            message=f"Tenant {tenant_id} has exceeded {limit_type} limit",
            code="TENANT_LIMIT_EXCEEDED",
            status_code=429
        )

# ==================== WHATSAPP EXCEPTIONS ====================

class WhatsAppAccountError(BusinessException):
    def __init__(self, message: str, error_code: str = None):
        super().__init__(
            message=message,
            code="WHATSAPP_ACCOUNT_ERROR",
            details={"whatsapp_error_code": error_code} if error_code else {}
        )

class WhatsAppAPIError(BusinessException):
    def __init__(self, message: str, status_code: int, error_data: Dict = None):
        super().__init__(
            message=message,
            code="WHATSAPP_API_ERROR",
            status_code=status_code,
            details=error_data
        )

class MessageSendingError(BusinessException):
    def __init__(self, message: str, message_id: str = None):
        details = {"message_id": message_id} if message_id else {}
        super().__init__(
            message=message,
            code="MESSAGE_SENDING_ERROR",
            details=details
        )

# ==================== VALIDATION EXCEPTIONS ====================

class ValidationError(BusinessException):
    def __init__(self, message: str, field: str = None):
        details = {"field": field} if field else {}
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details=details
        )

# ==================== RATE LIMITING EXCEPTIONS ====================

class RateLimitExceededError(BusinessException):
    def __init__(self, retry_after: int = None):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(
            message="Rate limit exceeded",
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details
        )