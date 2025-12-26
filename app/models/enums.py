from enum import StrEnum

class CircleFrequency(StrEnum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"

class CircleStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"

class PayoutPreference(StrEnum):
    FIXED = "fixed"
    RANDOM = "random"

class CircleRole(StrEnum):
    HOST = "host"
    MEMBER = "member"

class ContributionStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    MISSED = "missed"
    OVERDUE = "overdue"

class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"

class NotificationType(StrEnum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ACTION_REQUIRED = "action_required"

class NotificationPriority(StrEnum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

class TransactionType(StrEnum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    CONTRIBUTION = "contribution"
    PAYOUT = "payout"

class TransactionStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
