from saas_doc_qa.account_answer_service import AccountAnswerService
from saas_doc_qa.models import (
    AccountState,
    DocumentKind,
    IndexDocumentsRequest,
    QuestionRequest,
    TeamDocument,
)


class RetrievalStub:
    def __init__(self) -> None:
        self.queries: list[dict] = []
        self.rerank_candidates: list[str] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.2, 0.8] for _ in texts]

    def query(
        self,
        collection: str,
        embedding: list[float],
        top_k: int,
        tenant_id: str,
        kinds: list[str],
    ) -> dict:
        self.queries.append({"tenant_id": tenant_id, "kinds": kinds})
        return {
            "matches": [
                {
                    "metadata": {
                        "document_id": "other-admin",
                        "tenant_id": "tenant-b",
                        "kind": "admin_runbook",
                        "title": "Other tenant",
                        "text": "Rotate the other tenant owner.",
                    }
                },
                {
                    "metadata": {
                        "document_id": "acme-invite",
                        "tenant_id": "acme",
                        "kind": "onboarding",
                        "title": "Invite the first admin",
                        "text": "The account owner sends the first admin invitation.",
                    }
                },
                {
                    "metadata": {
                        "document_id": "acme-offboard",
                        "tenant_id": "acme",
                        "kind": "lifecycle",
                        "title": "Close an account",
                        "text": "Export records before closing an active account.",
                    }
                },
            ]
        }

    def rerank(self, query: str, candidates: list[str], top_k: int) -> dict:
        self.rerank_candidates = candidates
        return {"results": [{"index": 0, "score": 0.98}]}


class IndexingStub:
    def __init__(self) -> None:
        self.upserts: list[tuple[str, list[dict]]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.2, 0.8] for _ in texts]

    def upsert(self, collection: str, vectors: list[dict]) -> None:
        self.upserts.append((collection, vectors))


def test_indexing_uses_an_existing_collection() -> None:
    client = IndexingStub()
    indexed = AccountAnswerService(client).index(
        IndexDocumentsRequest(
            documents=[
                TeamDocument(
                    document_id="acme-invite",
                    tenant_id="acme",
                    kind=DocumentKind.ONBOARDING,
                    title="Invite the first admin",
                    text="The account owner sends the first admin invitation.",
                )
            ]
        )
    )

    assert indexed == 1
    assert client.upserts[0][0] == "saas-team-documents"
    assert client.upserts[0][1][0]["id"] == "acme-invite"


def test_onboarding_question_excludes_other_tenant_and_lifecycle_documents() -> None:
    client = RetrievalStub()
    answer = AccountAnswerService(client).answer(
        QuestionRequest(
            tenant_id="acme",
            account_state=AccountState.ONBOARDING,
            question="Who sends the first admin invite?",
        )
    )

    assert client.queries == [{"tenant_id": "acme", "kinds": ["onboarding"]}]
    assert client.rerank_candidates == [
        "The account owner sends the first admin invitation."
    ]
    assert answer.decision == "answered"
    assert answer.source is not None
    assert answer.source.document_id == "acme-invite"


def test_suspended_account_stops_before_retrieval() -> None:
    client = RetrievalStub()
    answer = AccountAnswerService(client).answer(
        QuestionRequest(
            tenant_id="acme",
            account_state=AccountState.SUSPENDED,
            question="How do I rotate an admin?",
        )
    )

    assert answer.decision == "account_suspended"
    assert client.queries == []
