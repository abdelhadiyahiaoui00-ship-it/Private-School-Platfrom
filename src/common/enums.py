import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    supervisor = "supervisor"
    external = "external"
    student = "student"


class UserStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class ProjectStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    AUTHORIZATION_SUBMITTED = "AUTHORIZATION_SUBMITTED"
    DEFENSE_SCHEDULED = "DEFENSE_SCHEDULED"
    DEFENDED = "DEFENDED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ProjectType(str, enum.Enum):
    NORMAL = "NORMAL"
    STARTUP = "STARTUP"


class TeamStatus(str, enum.Enum):
    forming = "forming"
    validated = "validated"
    assigned = "assigned"
    defense = "defense"


class JoinRequestStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class ConflictRule(str, enum.Enum):
    gpa = "gpa"
    submission_order = "submission_order"
    manual = "manual"


class DeliverableStatus(str, enum.Enum):
    pending = "pending"
    submitted = "submitted"
    reviewed = "reviewed"
    revision_requested = "revision_requested"


class AuthorizationStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class DefenseStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    POSTPONED = "POSTPONED"


class MentionGrade(str, enum.Enum):
    VERY_GOOD = "VERY_GOOD"
    GOOD = "GOOD"
    PASS = "PASS"
    FAIL = "FAIL"


class JuryRole(str, enum.Enum):
    PRESIDENT = "PRESIDENT"
    EXAMINER = "EXAMINER"
    SUPERVISOR = "SUPERVISOR"


class NotificationType(str, enum.Enum):
    PROJECT_ACCEPTED = "PROJECT_ACCEPTED"
    PROJECT_REJECTED = "PROJECT_REJECTED"
    PROJECT_SUBMITTED = "PROJECT_SUBMITTED"
    PROJECT_NEEDS_REVISION = "PROJECT_NEEDS_REVISION"
    TEAM_VALIDATED = "TEAM_VALIDATED"
    PROJECT_ASSIGNED = "PROJECT_ASSIGNED"
    DELIVERABLE_SUBMITTED = "DELIVERABLE_SUBMITTED"
    DELIVERABLE_FEEDBACK = "DELIVERABLE_FEEDBACK"
    DELIVERABLE_DEADLINE_REMINDER = "DELIVERABLE_DEADLINE_REMINDER"
    AUTHORIZATION_APPROVED = "AUTHORIZATION_APPROVED"
    AUTHORIZATION_REJECTED = "AUTHORIZATION_REJECTED"
    AUTHORIZATION_SUBMITTED = "AUTHORIZATION_SUBMITTED"
    AUTHORIZATION_ACCEPTED = "AUTHORIZATION_ACCEPTED"
    DEFENSE_SCHEDULED = "DEFENSE_SCHEDULED"
    DEFENSE_PV_SUBMITTED = "DEFENSE_PV_SUBMITTED"
    JURY_DECISION_SUBMITTED = "JURY_DECISION_SUBMITTED"
    DEADLINE_REMINDER = "DEADLINE_REMINDER"
    CHAT_MESSAGE = "CHAT_MESSAGE"
    ACCOUNT_CREATED = "ACCOUNT_CREATED"
    PHASE_ADVANCED = "PHASE_ADVANCED"
    # Sprint 4 — Teams
    JOIN_REQUEST_RECEIVED = "JOIN_REQUEST_RECEIVED"
    JOIN_REQUEST_ACCEPTED = "JOIN_REQUEST_ACCEPTED"
    JOIN_REQUEST_REJECTED = "JOIN_REQUEST_REJECTED"
    TEAM_INVITE_RECEIVED = "TEAM_INVITE_RECEIVED"
    TEAM_INVITE_ACCEPTED = "TEAM_INVITE_ACCEPTED"
    REMOVED_FROM_TEAM = "REMOVED_FROM_TEAM"
    MEMBER_LEFT_TEAM = "MEMBER_LEFT_TEAM"
    ADDED_TO_TEAM_BY_ADMIN = "ADDED_TO_TEAM_BY_ADMIN"
    BECAME_TEAM_LEADER = "BECAME_TEAM_LEADER"
    # Sprint 5 — Preferences & Assignment
    PREFERENCE_SUBMITTED = "PREFERENCE_SUBMITTED"
    ASSIGNMENT_CONFIRMED = "ASSIGNMENT_CONFIRMED"
    PROJECT_ASSIGNED_SUPERVISOR = "PROJECT_ASSIGNED_SUPERVISOR"


class AuditAction(str, enum.Enum):
    ACCOUNT_CREATED = "ACCOUNT_CREATED"
    ACCOUNT_DEACTIVATED = "ACCOUNT_DEACTIVATED"
    JOIN_REQUEST_SENT = "JOIN_REQUEST_SENT"
    JOIN_REQUEST_APPROVED = "JOIN_REQUEST_APPROVED"
    JOIN_REQUEST_REJECTED = "JOIN_REQUEST_REJECTED"
    PREFERENCE_SUBMITTED = "PREFERENCE_SUBMITTED"
    PREFERENCE_UPDATED = "PREFERENCE_UPDATED"
    ASSIGNMENT_TRIGGERED = "ASSIGNMENT_TRIGGERED"
    PROJECT_PROPOSED = "PROJECT_PROPOSED"
    PROJECT_ACCEPTED = "PROJECT_ACCEPTED"
    PROJECT_REJECTED = "PROJECT_REJECTED"
    PROJECT_RESUBMITTED = "PROJECT_RESUBMITTED"
    PROJECT_ASSIGNED = "PROJECT_ASSIGNED"
    PROJECT_NEEDS_REVISION = "PROJECT_NEEDS_REVISION"
    PROJECT_DELETED = "PROJECT_DELETED"
    PROJECT_FILE_UPLOADED = "PROJECT_FILE_UPLOADED"
    PROJECT_FILE_DELETED = "PROJECT_FILE_DELETED"
    DELIVERABLE_UPLOADED = "DELIVERABLE_UPLOADED"
    FEEDBACK_SUBMITTED = "FEEDBACK_SUBMITTED"
    CHAT_MESSAGE_SENT = "CHAT_MESSAGE_SENT"
    AUTHORIZATION_SUBMITTED = "AUTHORIZATION_SUBMITTED"
    AUTHORIZATION_APPROVED = "AUTHORIZATION_APPROVED"
    AUTHORIZATION_REJECTED = "AUTHORIZATION_REJECTED"
    AUTHORIZATION_REVIEWED = "AUTHORIZATION_REVIEWED"
    DEFENSE_SCHEDULED = "DEFENSE_SCHEDULED"
    DEFENSE_UPDATED = "DEFENSE_UPDATED"
    DEFENSE_DELETED = "DEFENSE_DELETED"
    DEFENSE_CONFIRMED = "DEFENSE_CONFIRMED"
    DEFENSE_PV_SUBMITTED = "DEFENSE_PV_SUBMITTED"
    DEFENSE_COMPLETED = "DEFENSE_COMPLETED"
    GRADE_ENTERED = "GRADE_ENTERED"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGOUT = "LOGOUT"
    LOGOUT_ALL_DEVICES = "LOGOUT_ALL_DEVICES"
    YEAR_CREATED = "YEAR_CREATED"
    YEAR_UPDATED = "YEAR_UPDATED"
    ACADEMIC_YEAR_LABEL_UPDATED = "ACADEMIC_YEAR_LABEL_UPDATED"
    YEAR_SET_CURRENT = "YEAR_SET_CURRENT"
    YEAR_ACTIVATED = "YEAR_ACTIVATED"
    YEAR_CLOSED = "YEAR_CLOSED"
    YEAR_DELETED = "YEAR_DELETED"
    CONFIG_UPDATED = "CONFIG_UPDATED"
    PHASE_ADVANCED = "PHASE_ADVANCED"
    PHASE_RETREATED = "PHASE_RETREATED"
    # Sprint 4 — Teams
    TEAM_CREATED = "TEAM_CREATED"
    TEAM_CREATED_BY_ADMIN = "TEAM_CREATED_BY_ADMIN"
    TEAM_UPDATED = "TEAM_UPDATED"
    TEAM_DELETED = "TEAM_DELETED"
    TEAM_VALIDATED = "TEAM_VALIDATED"
    TEAM_INVALIDATED = "TEAM_INVALIDATED"
    TEAM_INVITE_SENT = "TEAM_INVITE_SENT"
    MEMBER_REMOVED = "MEMBER_REMOVED"
    MEMBER_LEFT = "MEMBER_LEFT"
    LEADERSHIP_TRANSFERRED = "LEADERSHIP_TRANSFERRED"
    # Sprint 5 — Preferences & Assignment
    PREFERENCE_SAVED = "PREFERENCE_SAVED"
    ASSIGNMENT_PREVIEW_RUN = "ASSIGNMENT_PREVIEW_RUN"
    ASSIGNMENT_RUN = "ASSIGNMENT_RUN"
    ASSIGNMENT_OVERRIDDEN = "ASSIGNMENT_OVERRIDDEN"
    ASSIGNMENT_REMOVED = "ASSIGNMENT_REMOVED"
    ASSIGNMENT_CONFIRMED = "ASSIGNMENT_CONFIRMED"
    DELIVERABLE_SUBMITTED = "DELIVERABLE_SUBMITTED"
    DELIVERABLE_RESUBMITTED = "DELIVERABLE_RESUBMITTED"
    DELIVERABLE_REVIEWED = "DELIVERABLE_REVIEWED"
    DELIVERABLE_REVISION_REQUESTED = "DELIVERABLE_REVISION_REQUESTED"
    CHAT_MESSAGE_EDITED = "CHAT_MESSAGE_EDITED"
    CHAT_MESSAGE_DELETED = "CHAT_MESSAGE_DELETED"
    WORKSPACE_ACCESSED = "WORKSPACE_ACCESSED"
    JURY_EVALUATION_UPDATED = "JURY_EVALUATION_UPDATED"
    JURY_DECISION_SUBMITTED = "JURY_DECISION_SUBMITTED"


class AcademicYearStatus(str, enum.Enum):
    active = "active"
    closed = "closed"


class SystemPhase(str, enum.Enum):
    setup = "setup"
    proposals = "proposals"
    teams = "teams"
    voeux = "voeux"
    assignment = "assignment"
    development = "development"
    authorization = "authorization"
    defense = "defense"
    grades = "grades"
    closed = "closed"


# ── Sprint 3 — Projects Module enums ────────────────────────────────────────

class Sprint3ProjectStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    needs_revision = "needs_revision"
    rejected = "rejected"
    assigned = "assigned"


class Sprint3ProjectType(str, enum.Enum):
    normal = "normal"
    startup = "startup"


class ProjectDomain(str, enum.Enum):
    AI_ML = "AI/ML"
    Web = "Web"
    Mobile = "Mobile"
    Networks = "Networks"
    Security = "Security"
    Data_Science = "Data Science"
    Systems = "Systems"
    IoT = "IoT"
    Blockchain = "Blockchain"
    Other = "Other"


class ProjectFileType(str, enum.Enum):
    image = "image"
    pdf = "pdf"
    docx = "docx"
    xlsx = "xlsx"
    other = "other"


class CloudinaryResourceType(str, enum.Enum):
    image = "image"
    raw = "raw"
