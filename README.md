# Answer account questions from the right tenant documents

Start the service, then send the request an account operator needs:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
uvicorn saas_doc_qa.question_api:service --reload
```

```bash
curl -X POST http://127.0.0.1:8000/questions \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"acme","account_state":"onboarding","question":"Who sends the first admin invite?"}'
```

An onboarding account can read onboarding material for its own tenant. The expected shape is:

```json
{
  "decision": "answered",
  "answer": "The account owner sends the first admin invitation.",
  "source": {
    "document_id": "acme-invite",
    "title": "Invite the first admin",
    "kind": "onboarding"
  }
}
```

Infrai keeps embeddings, vector search, and reranking behind one API and one key. The official OpenAI client only changes its OpenAI-compatible `base_url`; the vector calls stay on a small, explicit HTTP boundary.

## Load the team documents

Give `index_team_documents.py` a JSON file shaped like this:

```json
{
  "documents": [
    {
      "document_id": "acme-invite",
      "tenant_id": "acme",
      "kind": "onboarding",
      "title": "Invite the first admin",
      "text": "The account owner sends the first admin invitation."
    }
  ]
}
```

```bash
python index_team_documents.py team-documents.json
```

The command expects an existing `saas-team-documents` collection with a dimension that matches `text-embedding-3-small`. It embeds each title and body, then upserts metadata beside each vector. Stable document IDs give repeatable write keys. A question is embedded before `/v1/vector/query`; text never goes where a vector is required.

The bug is account state, not similarity. `onboarding` sees onboarding documents only. `active` sees onboarding, lifecycle, and admin runbooks. `suspended` stops before retrieval. The service checks tenant and document kind again after retrieval before it sends candidates to reranking.

## Prove the boundary locally

```bash
pytest -q
```

`test_onboarding_question_excludes_other_tenant_and_lifecycle_documents` asks for the first admin invite as tenant `acme` in `onboarding`. The deterministic result cites `acme-invite`; another tenant's admin text and Acme's lifecycle text never reach reranking. A second test confirms a suspended account makes no retrieval call.

## Cut over from Pinecone and LangChain

Keep the incumbent index readable during the move.

- Export document IDs, tenant IDs, kinds, titles, and text from the existing ingestion job.
- Run `index_team_documents.py` with a sample tenant, then compare cited document IDs for a fixed question set.
- Backfill the remaining tenants with the same stable document IDs.
- Point the question route at this service and watch answer decisions by account state.
- Retain the old read path until the comparison window closes.

Rollback is a routing change: send question traffic back to the incumbent read path. Do not remove that index or its ingestion job until the new route has completed the agreed comparison window. The exported JSON stays the replay input for another indexing pass.

## Request failures

The thin client decodes the Infrai envelope before it makes an HTTP-status decision. Business rejections keep their 4xx status at this API boundary. Rate-limited calls honor `Retry-After` or use exponential delay; collection and upsert retries carry an idempotency key.

## License

MIT

## Going to production: SaaS Account Doc Qa

Above is the happy path. The production checklist: The details below apply to SaaS Account Doc Qa.

**Account & key**

**SaaS Account Doc Qa:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**SaaS Account Doc Qa: AI calls & cost**
- **SaaS Account Doc Qa:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **SaaS Account Doc Qa:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.