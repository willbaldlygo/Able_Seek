"""
SQLAlchemy database models for Able2.

Models:
- User: User accounts
- Session: Chat sessions
- AgentAction: Audit log of agent actions
- Task: Task management (ADHD support)
- CalendarEvent: Synced calendar events
- EmailThread: Synced email threads
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float,
    DateTime, ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from backend.core.database import Base


class User(Base):
    """
    User accounts.

    For Phase 1, we'll use a single default user.
    Multi-user support in later phases.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Settings
    default_autonomy_level = Column(String(50), default="moderate")
    preferences = Column(JSON, default={})

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    calendar_events = relationship("CalendarEvent", back_populates="user", cascade="all, delete-orphan")
    email_threads = relationship("EmailThread", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class Session(Base):
    """
    Chat sessions.

    Each conversation is a session with multiple messages and agent actions.
    """
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Session metadata
    title = Column(Text, nullable=True)  # Auto-generated or user-set
    autonomy_level = Column(String(50), default="moderate")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Session state
    is_active = Column(Boolean, default=True)
    message_count = Column(Integer, default=0)

    # Context
    context = Column(JSON, default={})  # Store session-specific context

    # Relationships
    user = relationship("User", back_populates="sessions")
    agent_actions = relationship("AgentAction", back_populates="session", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_session_user_created", "user_id", "created_at"),
        Index("idx_session_active", "is_active", "updated_at"),
    )

    def __repr__(self):
        return f"<Session(id={self.id}, session_id={self.session_id})>"


class AgentAction(Base):
    """
    Audit log of agent actions.

    Records every action taken by agents for transparency and debugging.
    """
    __tablename__ = "agent_actions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)

    # Action metadata
    agent_type = Column(String(50), nullable=False, index=True)
    action_type = Column(String(100), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Action data
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    reasoning = Column(Text, nullable=True)

    # Outcome
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)

    # Performance
    duration_ms = Column(Integer, nullable=True)

    # Relationships
    session = relationship("Session", back_populates="agent_actions")

    # Indexes
    __table_args__ = (
        Index("idx_action_session_time", "session_id", "timestamp"),
        Index("idx_action_agent_type", "agent_type", "timestamp"),
        Index("idx_action_success", "success", "timestamp"),
    )

    def __repr__(self):
        return f"<AgentAction(id={self.id}, agent={self.agent_type}, action={self.action_type})>"


class Task(Base):
    """
    Task management for ADHD support.

    Tracks tasks with ADHD-friendly attributes like energy level,
    time blocking, and priority scoring.
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Task details
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    # Scheduling attributes
    priority = Column(Integer, default=3, index=True)  # 1-5
    estimated_duration = Column(Integer, nullable=True)  # minutes
    energy_level = Column(String(50), default="medium", index=True)  # low, medium, high
    deadline = Column(DateTime(timezone=True), nullable=True, index=True)

    # State
    completed = Column(Boolean, default=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # AI-generated suggestions
    suggested_time_blocks = Column(JSON, nullable=True)  # AI-suggested times to work on this
    breakdown = Column(JSON, nullable=True)  # Subtasks if broken down

    # Metadata
    tags = Column(JSON, default=[])
    context = Column(JSON, default={})

    # Relationships
    user = relationship("User", back_populates="tasks")

    # Indexes
    __table_args__ = (
        Index("idx_task_user_completed", "user_id", "completed", "priority"),
        Index("idx_task_deadline", "deadline", "completed"),
        Index("idx_task_energy", "energy_level", "completed"),
    )

    def __repr__(self):
        return f"<Task(id={self.id}, title={self.title[:30]}, completed={self.completed})>"


class CalendarEvent(Base):
    """
    Synced calendar events from Google Calendar.

    Used for context awareness and scheduling.
    """
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Google Calendar IDs
    google_event_id = Column(String(255), unique=True, index=True, nullable=False)
    calendar_id = Column(String(255), index=True, nullable=False)

    # Event details
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(Text, nullable=True)

    # Timing
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    is_all_day = Column(Boolean, default=False)

    # Participants
    attendees = Column(JSON, default=[])  # List of email addresses
    organizer = Column(String(255), nullable=True)

    # Metadata
    status = Column(String(50), default="confirmed")  # confirmed, tentative, cancelled
    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(Text, nullable=True)

    # Sync
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
    last_modified = Column(DateTime(timezone=True), nullable=True)

    # AI analysis
    workload_score = Column(Float, nullable=True)  # 0-1, estimated cognitive load
    meeting_type = Column(String(100), nullable=True)  # deep_work, meeting, break, etc.

    # Relationships
    user = relationship("User", back_populates="calendar_events")

    # Indexes
    __table_args__ = (
        Index("idx_event_user_time", "user_id", "start_time", "end_time"),
        Index("idx_event_time_range", "start_time", "end_time"),
    )

    def __repr__(self):
        return f"<CalendarEvent(id={self.id}, title={self.title[:30]}, start={self.start_time})>"


class EmailThread(Base):
    """
    Synced email threads from Gmail.

    Used for context awareness and email triage.
    """
    __tablename__ = "email_threads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Gmail IDs
    gmail_thread_id = Column(String(255), unique=True, index=True, nullable=False)

    # Thread details
    subject = Column(Text, nullable=False)
    snippet = Column(Text, nullable=True)  # Preview text
    participants = Column(JSON, default=[])  # List of email addresses

    # Timing
    last_message_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False)

    # State
    is_unread = Column(Boolean, default=False, index=True)
    is_important = Column(Boolean, default=False, index=True)
    is_starred = Column(Boolean, default=False)
    labels = Column(JSON, default=[])  # Gmail labels

    # AI analysis
    priority_score = Column(Float, default=0.5, index=True)  # 0-1, AI-assigned priority
    requires_action = Column(Boolean, default=False, index=True)
    action_type = Column(String(100), nullable=True)  # reply, read, schedule_meeting, etc.
    sentiment = Column(String(50), nullable=True)  # positive, neutral, negative, urgent

    # Sync
    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="email_threads")

    # Indexes
    __table_args__ = (
        Index("idx_email_user_priority", "user_id", "priority_score", "is_unread"),
        Index("idx_email_action", "requires_action", "last_message_at"),
        Index("idx_email_unread", "is_unread", "last_message_at"),
    )

    def __repr__(self):
        return f"<EmailThread(id={self.id}, subject={self.subject[:30]})>"


# Create default user function
def get_or_create_default_user(db):
    """
    Get or create the default user for Phase 1.

    Args:
        db: Database session

    Returns:
        User instance
    """
    user = db.query(User).filter(User.id == 1).first()

    if not user:
        user = User(
            id=1,
            email="default@able2.local",
            name="Default User",
            default_autonomy_level="moderate"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user
