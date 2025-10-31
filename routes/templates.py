# routes/templates.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import MessageTemplate, Tenant

router = APIRouter()

@router.post("/templates/")
def create_template(
    name: str,
    category: str,
    body: str,
    header: str = None,
    footer: str = None,
    db: Session = Depends(get_db)
):
    """Create a new message template"""
    try:
        # QUICK FIX: Get first tenant from database
        tenant = db.query(Tenant).first()
        if not tenant:
            raise HTTPException(status_code=400, detail="No tenant found")
        
        template = MessageTemplate(
            tenant_id=tenant.id,
            name=name,
            category=category,
            header=header,
            body=body,
            footer=footer,
            status="PENDING"
        )
        
        db.add(template)
        db.commit()
        db.refresh(template)
        
        return {"message": "Template created", "template_id": template.id}
        
    except Exception as e:
        db.rollback()
        # This will show us the actual error
        print(f"❌ Template creation error: {e}")
        raise HTTPException(status_code=400, detail=f"Template creation failed: {str(e)}")

@router.get("/templates/")
def list_templates(db: Session = Depends(get_db)):
    """List all templates"""
    tenant = db.query(Tenant).first()
    if not tenant:
        return []
    
    return db.query(MessageTemplate).filter(MessageTemplate.tenant_id == tenant.id).all()