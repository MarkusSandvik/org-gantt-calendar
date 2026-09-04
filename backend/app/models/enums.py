import enum


class UserRole(str, enum.Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"


class TeamCategory(str, enum.Enum):
    HARDWARE = "hardware"
    SOFTWARE = "software"
    ORGANIZATION = "organization"


class ActivityStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"
    BLOCKED = "blocked"


class Priority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MilestoneStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    COMPLETED = "completed"
    MISSED = "missed"


class DependencyType(str, enum.Enum):
    FINISH_TO_START = "finish_to_start"
    # Reserved for later: START_TO_START, FINISH_TO_FINISH, START_TO_FINISH


class SchedulableType(str, enum.Enum):
    """Discriminator for polymorphic references (dependencies, baselines)."""

    ACTIVITY = "activity"
    MILESTONE = "milestone"


class TaggableType(str, enum.Enum):
    ACTIVITY = "activity"
    MILESTONE = "milestone"
    CALENDAR_EVENT = "calendar_event"


class CommentableType(str, enum.Enum):
    ACTIVITY = "activity"
    MILESTONE = "milestone"


class CalendarEventType(str, enum.Enum):
    MEETING = "meeting"
    SOCIAL = "social"
    DEADLINE = "deadline"
    WORKSHOP = "workshop"
    RECRUITMENT = "recruitment"
    SPONSOR = "sponsor"
    TRAVEL = "travel"
    PRESENTATION = "presentation"
    STAND_DUTY = "stand_duty"
    OTHER = "other"
