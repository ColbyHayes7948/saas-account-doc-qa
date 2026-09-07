from dataclasses import asdict, dataclass
from enum import StrEnum


def _require_length(name: str, value: str, minimum: int, maximum: int | None = None) -> None:
    if len(value) < minimum or maximum is not None and len(value) > maximum:
        limit = f" between {minimum} and {maximum}" if maximum else f" at least {minimum}"
        raise ValueError(f"{name} must contain{limit} characters")


class AccountState(StrEnum):
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class DocumentKind(StrEnum):
    ONBOARDING = "onboarding"
    LIFECYCLE = "lifecycle"
    ADMIN_RUNBOOK = "admin_runbook"


@dataclass
class TeamDocument:
    document_id: str
    tenant_id: str
    kind: DocumentKind
    title: str
    text: str

    def __post_init__(self) -> None:
        self.kind = DocumentKind(self.kind)
        for name in ("document_id", "tenant_id", "title", "text"):
            _require_length(name, getattr(self, name), 1)

    def model_dump(self, mode: str = "python") -> dict[str, object]:
        data = asdict(self)
        if mode == "json":
            data["kind"] = self.kind.value
        return data


@dataclass
class IndexDocumentsRequest:
    documents: list[TeamDocument]

    def __post_init__(self) -> None:
        if not self.documents:
            raise ValueError("documents must contain at least one item")


@dataclass
class QuestionRequest:
    tenant_id: str
    account_state: AccountState
    question: str

    def __post_init__(self) -> None:
        self.account_state = AccountState(self.account_state)
        _require_length("tenant_id", self.tenant_id, 1)
        _require_length("question", self.question, 3, 800)


@dataclass
class AnswerSource:
    document_id: str
    title: str
    kind: DocumentKind

    def __post_init__(self) -> None:
        self.kind = DocumentKind(self.kind)


@dataclass
class QuestionAnswer:
    decision: str
    answer: str
    source: AnswerSource | None = None
