import json
import os
import sys
from pathlib import Path

from saas_doc_qa.account_answer_service import AccountAnswerService
from saas_doc_qa.infrai_client import InfraiClient
from saas_doc_qa.models import IndexDocumentsRequest


def main() -> None:
    source = Path(sys.argv[1])
    request = IndexDocumentsRequest.model_validate_json(source.read_text())
    indexed = AccountAnswerService(
        InfraiClient(api_key=os.environ["INFRAI_API_KEY"])
    ).index(request)
    print(json.dumps({"indexed": indexed, "collection": "saas-team-documents"}))


if __name__ == "__main__":
    main()
