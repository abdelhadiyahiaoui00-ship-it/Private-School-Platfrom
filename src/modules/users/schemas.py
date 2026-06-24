"""
Users Pydantic schemas — Sprint 1.
All response schemas use alias_generator=to_camel + by_alias=True as per spec.
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


# ─── Shared sub-schemas ───────────────────────────────────────────────────────

class BranchBasic(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: int
    name: str


class PermissionsSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    manage_users: bool = False
    manage_classes: bool = False
    manage_sessions: bool = False
    manage_enrollments: bool = False
    manage_subscriptions: bool = False
    view_logs: bool = False


class ParentLinkBasic(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: int
    parent_id: int
    student_id: int
    relationship: str
    created_at: datetime


# ─── User response schemas ────────────────────────────────────────────────────

class UserResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: int
    email: Optional[str]
    phone: Optional[str]
    first_name: str
    last_name: str
    role: str
    status: str
    avatar_url: Optional[str]
    date_of_birth: Optional[date]
    gender: Optional[str]
    language: str
    must_change_password: bool
    notifications_enabled: bool
    default_commission_percent: Optional[float]
    permissions: Optional[PermissionsSchema]
    assigned_branches: list[BranchBasic]
    linked_students: list[ParentLinkBasic]
    linked_parents: list[ParentLinkBasic]
    children_count: int
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]


class UserDetailResponse(UserResponse):
    """Single-user view — adds deactivation info and nested children/parents."""
    deactivated_at: Optional[datetime] = None
    deactivated_by: Optional[int] = None
    children: list[UserResponse] = []
    parents: list[UserResponse] = []


class UserWithPasswordResponse(UserDetailResponse):
    """Returned ONCE on account creation — includes plain temporary password."""
    temporary_password: str


# ─── List + pagination response ───────────────────────────────────────────────

class UserStats(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    total: int
    active: int
    inactive: int
    by_role: dict[str, int]


class PaginationMeta(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next_page: bool
    has_prev_page: bool


class UserListResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    items: list[UserResponse]
    pagination: PaginationMeta
    stats: UserStats


# ─── Request bodies ───────────────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    language: str = "ar"
    branch_ids: list[int] = []
    permissions: Optional[dict] = None
    default_commission_percent: Optional[float] = None
    linked_student_ids: list[int] = []
    relationships: dict[str, str] = {}


class UpdateUserRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    language: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar_url: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    password: Optional[str] = None
    # Admin-only fields (ignored if caller lacks permission):
    role: Optional[str] = None
    status: Optional[str] = None
    branch_ids: Optional[list[int]] = None
    permissions: Optional[dict] = None
    default_commission_percent: Optional[float] = None


class SetStatusRequest(BaseModel):
    status: str  # 'active' | 'inactive'


class BulkActionRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    action: str  # 'activate' | 'deactivate' | 'delete' | 'reset-passwords'
    user_ids: list[int]


class BulkActionResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    processed: int
    skipped: int
    results: Optional[list[dict]] = None


# ─── Parent link ──────────────────────────────────────────────────────────────

class ParentLinkResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: int
    parent_id: int
    student_id: int
    relationship: str
    created_by: Optional[int]
    created_at: datetime


class CreateParentLinkRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    parent_id: int
    student_id: int
    relationship: str = "parent"


# ─── Print info ───────────────────────────────────────────────────────────────

class PrintInfoResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: int
    full_name: str
    role: str
    email: Optional[str]
    phone: Optional[str]
    assigned_branches: list[BranchBasic]
    temporary_password: Optional[str]
    school_name: str
    printed_at: datetime
