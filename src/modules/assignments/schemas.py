from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class AssignmentFileResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int
    file_url: str
    file_type: Optional[str] = None
    file_name: Optional[str] = None
    uploaded_by: Optional[int] = None
    uploaded_at: datetime


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int
    batch_id: Optional[str] = None
    groups_in_batch: int
    group_id: int
    group_name: str
    class_id: int
    class_name: str
    module_name: str
    branch_id: int
    branch_name: str
    session_id: Optional[int] = None
    session_date_label: Optional[str] = None
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    is_overdue: bool
    is_due_soon: bool
    files: list[AssignmentFileResponse]
    submissions_count: int
    total_eligible_students: int
    created_by: int
    created_by_name: str
    created_at: datetime
    updated_at: datetime


class AssignmentDetailResponse(AssignmentResponse):
    pass


class AssignmentFileInput(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    file_url: str
    file_type: Optional[str] = None
    file_name: Optional[str] = None


class CreateAssignmentRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    group_id: int
    session_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    files: list[AssignmentFileInput] = Field(default_factory=list)


class BulkCreateAssignmentRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    group_ids: list[int]
    session_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    files: list[AssignmentFileInput] = Field(default_factory=list)


class UpdateAssignmentRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    files: Optional[list[AssignmentFileInput]] = None


class BulkCreateAssignmentResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    assignments: list[AssignmentResponse]
    batch_id: str
    created_count: int


class UpdateAssignmentResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    updated: list[AssignmentResponse]


class AssignmentListResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: list[AssignmentResponse]
    pagination: dict
    stats: dict  # { total, upcoming, dueSoon, overdue }


# ─── Submissions ──────────────────────────────────────────────────────────────


class SubmissionFileInput(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    file_url: str
    file_type: Optional[str] = None
    file_name: Optional[str] = None


class SubmitAssignmentRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    student_id: Optional[int] = None  # For parent-on-behalf only
    submission_type: str  # done_only | text | file
    response_text: Optional[str] = None
    file: Optional[SubmissionFileInput] = None


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int
    assignment_id: int
    student_id: int
    student: dict  # StudentBasic
    submission_type: str
    response_text: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    submitted_at: datetime
    updated_at: datetime
    is_late: bool


class SubmissionRosterEntry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    student: dict  # StudentBasic
    is_currently_enrolled: bool
    submission: Optional[SubmissionResponse] = None


class SubmissionsSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    submitted_count: int
    not_submitted_count: int
    late_count: int
    total: int


class AssignmentSubmissionsRosterResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    assignment: AssignmentResponse
    roster: list[SubmissionRosterEntry]
    summary: SubmissionsSummary


# ─── Teacher Classes ──────────────────────────────────────────────────────────


class SubstituteBasic(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None


class TeacherGroupResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int
    name: str
    capacity: int
    is_owned_by_me: bool
    substitute: Optional[SubstituteBasic] = None


class TeacherClassResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int
    name: str
    teacher_id: int
    teacher_name: str
    module_id: int
    module_name: str
    groups: list[TeacherGroupResponse]


class ClassBasicForSubstitute(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int
    name: str
    module_name: str
    branch_name: str
    default_teacher_name: str


class SubstituteGroupResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int
    name: str
    capacity: int
    parent_class: ClassBasicForSubstitute


class TeacherClassesResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    classes: list[TeacherClassResponse]
    substitute_groups: list[SubstituteGroupResponse]
