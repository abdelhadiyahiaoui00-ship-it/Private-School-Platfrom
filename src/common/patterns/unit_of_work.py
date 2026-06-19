from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import sessionmanager


class UnitOfWork:
    def __init__(self) -> None:
        self._session: AsyncSession | None = None
        self._repositories: dict = {}

    async def __aenter__(self) -> "UnitOfWork":
        self._session_ctx = sessionmanager.session()
        self._session = await self._session_ctx.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            await self._session.rollback()
        else:
            await self._session.commit()
        await self._session.close()
        self._session = None
        self._repositories.clear()

    @property
    def session(self) -> AsyncSession:
        return self._session

    def _get_repo(self, repo_cls, key: str):
        if key not in self._repositories:
            self._repositories[key] = repo_cls(self._session)
        return self._repositories[key]

    @property
    def users(self):
        from src.modules.users.repository import UserRepository
        return self._get_repo(UserRepository, "users")

    @property
    def auth(self):
        from src.modules.auth.repository import AuthRepository
        return self._get_repo(AuthRepository, "auth")

    @property
    def teachers(self):
        from src.modules.teachers.repository import TeacherRepository
        return self._get_repo(TeacherRepository, "teachers")

    @property
    def students(self):
        from src.modules.students.repository import StudentRepository
        return self._get_repo(StudentRepository, "students")

    @property
    def academic_years(self):
        from src.modules.academic_years.repository import AcademicYearRepository
        return self._get_repo(AcademicYearRepository, "academic_years")

    @property
    def projects(self):
        from src.modules.projects.repository import ProjectRepository
        return self._get_repo(ProjectRepository, "projects")

    @property
    def teams(self):
        from src.modules.teams.repository import TeamRepository
        return self._get_repo(TeamRepository, "teams")

    @property
    def preferences(self):
        from src.modules.preferences.repository import PreferenceRepository
        return self._get_repo(PreferenceRepository, "preferences")

    @property
    def assignments(self):
        from src.modules.assignments.repository import AssignmentRepository
        return self._get_repo(AssignmentRepository, "assignments")

    @property
    def deliverables(self):
        from src.modules.deliverables.repository import DeliverableRepository
        return self._get_repo(DeliverableRepository, "deliverables")

    @property
    def evaluations(self):
        from src.modules.evaluations.repository import EvaluationRepository
        return self._get_repo(EvaluationRepository, "evaluations")

    @property
    def authorizations(self):
        from src.modules.authorizations.repository import AuthorizationRepository
        return self._get_repo(AuthorizationRepository, "authorizations")

    @property
    def defenses(self):
        from src.modules.defenses.repository import DefenseRepository
        return self._get_repo(DefenseRepository, "defenses")

    @property
    def grades(self):
        from src.modules.grades.repository import GradeRepository
        return self._get_repo(GradeRepository, "grades")

    @property
    def chat(self):
        from src.modules.chat.repository import ChatRepository
        return self._get_repo(ChatRepository, "chat")

    @property
    def audit(self):
        from src.modules.audit.repository import AuditRepository
        return self._get_repo(AuditRepository, "audit")

    @property
    def notifications(self):
        from src.modules.notifications.repository import NotificationRepository
        return self._get_repo(NotificationRepository, "notifications")
