from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import MessageRole
from app.models.orm import Message


def previous_user_question(db: Session, assistant: Message) -> str:
    previous = db.scalar(
        select(Message)
        .where(
            Message.conversation_id == assistant.conversation_id,
            Message.id < assistant.id,
            Message.role == MessageRole.USER,
        )
        .order_by(Message.id.desc())
        .limit(1)
    )
    return previous.content.strip() if previous is not None else ""
