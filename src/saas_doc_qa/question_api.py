from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .account_answer_service import AccountAnswerService
from .infrai_client import InfraiClient, InfraiError
from .models import QuestionAnswer, QuestionRequest

service = FastAPI(title="SaaS account document answers")
answer_service = AccountAnswerService(InfraiClient())


@service.exception_handler(InfraiError)
async def infrai_error_response(_: Request, error: InfraiError) -> JSONResponse:
    status = error.status_code if 400 <= error.status_code < 500 else 502
    return JSONResponse(
        status_code=status,
        content={"detail": error.detail, "code": error.code},
    )


@service.post("/questions", response_model=QuestionAnswer)
def answer_question(request: QuestionRequest) -> QuestionAnswer:
    return answer_service.answer(request)
