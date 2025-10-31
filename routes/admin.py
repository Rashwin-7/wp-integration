from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.session import get_db
from database.models import Tenant, Message
from datetime import datetime, timedelta, date
from loguru import logger

router = APIRouter()

@router.get("/analytics/daily-growth")
def daily_growth_analytics(db: Session = Depends(get_db)):
    """Daily business growth metrics"""
    try:
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        # Message growth analysis
        messages_today = db.query(Message).filter(
            Message.created_at >= today
        ).count()
        
        messages_week_ago = db.query(Message).filter(
            Message.created_at >= week_ago,
            Message.created_at < week_ago + timedelta(days=1)
        ).count()
        
        # Weekly growth rate
        weekly_growth = 0
        if messages_week_ago > 0:
            weekly_growth = ((messages_today - messages_week_ago) / messages_week_ago) * 100
        
        # Active tenants trend
        active_today = db.query(Tenant).filter(Tenant.is_active == True).count()
        
        return {
            "date": today.isoformat(),
            "daily_metrics": {
                "messages_today": messages_today,
                "active_tenants": active_today,
                "avg_messages_per_tenant": round(messages_today / active_today, 2) if active_today > 0 else 0
            },
            "growth_metrics": {
                "weekly_growth_percentage": round(weekly_growth, 1),
                "message_velocity": "increasing" if weekly_growth > 0 else "decreasing",
                "trend": "positive" if weekly_growth > 10 else "stable" if weekly_growth > 0 else "negative"
            }
        }
        
    except Exception as e:
        logger.error(f"Growth analytics error: {e}")
        raise HTTPException(500, "Failed to generate growth analytics")

@router.get("/tenants/engagement")
def tenant_engagement_metrics(db: Session = Depends(get_db)):
    """Measure how engaged your tenants are"""
    try:
        # Get tenants with their message activity
        tenants = db.query(
            Tenant.name,
            Tenant.created_at,
            func.count(Message.id).label('total_messages'),
            func.max(Message.created_at).label('last_activity')
        ).outerjoin(Message).group_by(Tenant.id, Tenant.name).all()
        
        engagement_data = []
        for tenant in tenants:
            # Calculate engagement score
            days_since_join = (datetime.now().date() - tenant.created_at.date()).days
            messages_per_day = tenant.total_messages / max(days_since_join, 1)
            
            # Engagement tiers
            if messages_per_day > 10:
                engagement = "high"
            elif messages_per_day > 3:
                engagement = "medium" 
            else:
                engagement = "low"
            
            engagement_data.append({
                "name": tenant.name,
                "joined_days_ago": days_since_join,
                "total_messages": tenant.total_messages,
                "messages_per_day": round(messages_per_day, 2),
                "last_activity": tenant.last_activity.isoformat() if tenant.last_activity else "Never",
                "engagement_tier": engagement
            })
        
        return sorted(engagement_data, key=lambda x: x['messages_per_day'], reverse=True)
        
    except Exception as e:
        logger.error(f"Engagement metrics error: {e}")
        raise HTTPException(500, "Failed to get engagement data")

# @router.get("/revenue/forecast")
# def revenue_forecast(db: Session = Depends(get_db)):
#     """Predict revenue based on current usage patterns"""
#     try:
#         # Simple revenue model (you can customize pricing)
#         PRICE_PER_MESSAGE = 0.01  # $0.01 per message
#         BASE_FEE = 29  # $29 monthly base fee
        
#         # Current month projection
#         today = datetime.now()
#         days_in_month = 30
#         days_passed = today.day
        
#         messages_this_month = db.query(Message).filter(
#             Message.created_at >= datetime(today.year, today.month, 1)
#         ).count()
        
        # Project monthly total

    #     projected_messages = (messages_this_month / days_passed) * days_in_month
    #     projected_revenue = (projected_messages * PRICE_PER_MESSAGE) + BASE_FEE
        
    #     return {
    #         "current_month": {
    #             "messages_so_far": messages_this_month,
    #             "days_passed": days_passed,
    #             "daily_average": round(messages_this_month / days_passed, 2)
    #         },
    #         "projection": {
    #             "estimated_monthly_messages": round(projected_messages),
    #             "estimated_revenue": f"${round(projected_revenue, 2)}",
    #             "confidence": "high" if days_passed > 7 else "medium"
    #         },
    #         "pricing_model": {
    #             "base_fee": BASE_FEE,
    #             "per_message": PRICE_PER_MESSAGE
    #         }
    #     }
        
    # except Exception as e:
    #     logger.error(f"Revenue forecast error: {e}")
    #     raise HTTPException(500, "Failed to generate revenue forecast")

@router.get("/performance/message-success")
def message_success_rates(db: Session = Depends(get_db)):
    """Analyze message delivery success rates"""
    try:
        # Get message status distribution
        status_counts = db.query(
            Message.status,
            func.count(Message.id).label('count')
        ).group_by(Message.status).all()
        
        total_messages = sum(count for status, count in status_counts)
        
        success_rates = {}
        for status, count in status_counts:
            success_rates[status] = {
                "count": count,
                "percentage": round((count / total_messages) * 100, 2) if total_messages > 0 else 0
            }
        
        # Overall success rate (considering 'sent' as success)
        success_rate = success_rates.get('sent', {}).get('percentage', 0)
        
        return {
            "total_messages_analyzed": total_messages,
            "success_rate_percentage": success_rate,
            "status_breakdown": success_rates,
            "health_indicator": "excellent" if success_rate > 95 else "good" if success_rate > 85 else "needs_attention"
        }
        
    except Exception as e:
        logger.error(f"Success rates error: {e}")
        raise HTTPException(500, "Failed to analyze success rates")