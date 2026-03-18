from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import User, Comment
from schemas import CommentCreate, CommentOut
from auth_utils import get_current_user

router = APIRouter(prefix="/comments", tags=["comments"])


@router.get("", response_model=List[dict])
def list_comments(
    entity_type: str = Query(...),
    entity_id: int = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    comments = (
        db.query(Comment)
        .filter(Comment.entity_type == entity_type, Comment.entity_id == entity_id)
        .order_by(Comment.created_at.asc())
        .all()
    )
    return [
        {
            "id": c.id,
            "entity_type": c.entity_type,
            "entity_id": c.entity_id,
            "user_id": c.user_id,
            "user_name": c.user.name if c.user else "Unknown",
            "role": c.user.role.value if c.user else None,
            "body": c.body,
            "created_at": c.created_at,
        }
        for c in comments
    ]


@router.post("", response_model=dict, status_code=201)
def add_comment(
    body: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.entity_type not in ("company", "qs", "job"):
        raise HTTPException(status_code=400, detail="entity_type must be company, qs, or job")

    comment = Comment(
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        user_id=current_user.id,
        body=body.body,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {
        "id": comment.id,
        "entity_type": comment.entity_type,
        "entity_id": comment.entity_id,
        "user_id": comment.user_id,
        "user_name": current_user.name,
        "role": current_user.role.value,
        "body": comment.body,
        "created_at": comment.created_at,
    }


@router.delete("/{comment_id}", status_code=204)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    # Only author or admin can delete
    if comment.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not authorised to delete this comment")
    db.delete(comment)
    db.commit()
