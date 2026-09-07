from __future__ import annotations

from typing import Any

from .models import (
    AccountState,
    AnswerSource,
    DocumentKind,
    IndexDocumentsRequest,
    QuestionAnswer,
    QuestionRequest,
)


class AccountAnswerService:
    def __init__(self, client: Any, collection: str = "saas-team-documents") -> None:
        self.client = client
        self.collection = collection

    def index(self, request: IndexDocumentsRequest) -> int:
        texts = [f"{document.title}\n{document.text}" for document in request.documents]
        embeddings = self.client.embed(texts)
        if len(embeddings) != len(request.documents):
            raise ValueError("Embedding count must match document count")
        vectors = [
            {
                "id": document.document_id,
                "values": embedding,
                "metadata": document.model_dump(mode="json"),
            }
            for document, embedding in zip(request.documents, embeddings, strict=True)
        ]
        self.client.upsert(self.collection, vectors)
        return len(vectors)

    def answer(self, request: QuestionRequest) -> QuestionAnswer:
        allowed_kinds = self._allowed_kinds(request.account_state)
        if not allowed_kinds:
            return QuestionAnswer(
                decision="account_suspended",
                answer="Document access is paused for this account.",
            )

        embedding = self.client.embed([request.question])[0]
        found = self.client.query(
            self.collection,
            embedding,
            top_k=8,
            tenant_id=request.tenant_id,
            kinds=[kind.value for kind in allowed_kinds],
        )
        matches = [
            match
            for match in found.get("matches", [])
            if self._is_visible(match.get("metadata", {}), request, allowed_kinds)
        ]
        candidates = [match["metadata"]["text"] for match in matches]
        if not candidates:
            return QuestionAnswer(
                decision="no_matching_document",
                answer="No account document matched this question.",
            )

        ranked = self.client.rerank(request.question, candidates, top_k=1)
        best_index = int(ranked["results"][0]["index"])
        metadata = matches[best_index]["metadata"]
        return QuestionAnswer(
            decision="answered",
            answer=candidates[best_index],
            source=AnswerSource(
                document_id=metadata["document_id"],
                title=metadata["title"],
                kind=DocumentKind(metadata["kind"]),
            ),
        )

    @staticmethod
    def _allowed_kinds(state: AccountState) -> set[DocumentKind]:
        if state == AccountState.ONBOARDING:
            return {DocumentKind.ONBOARDING}
        if state == AccountState.ACTIVE:
            return set(DocumentKind)
        return set()

    @staticmethod
    def _is_visible(
        metadata: dict[str, Any],
        request: QuestionRequest,
        allowed_kinds: set[DocumentKind],
    ) -> bool:
        try:
            kind = DocumentKind(metadata.get("kind"))
        except ValueError:
            return False
        return metadata.get("tenant_id") == request.tenant_id and kind in allowed_kinds
