"""FastAPI application: exact truth verification endpoint."""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .schemas import VerifyRequest, VerifyResponse, WitnessPayload
from .verifier import (
    OUTCOME_COLLISION,
    OUTCOME_NOT_HOME,
    STATUS_FAIL,
    STATUS_PASS,
    verify,
)

app = FastAPI(
    title="Change Ringing Truth Verifier",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


def _format_location(loc: tuple) -> str:
    parts = [str(part) for part in loc if part not in ("body",)]
    if not parts:
        return "body"
    out = parts[0]
    for part in parts[1:]:
        out += f"[{part}]" if part.isdigit() else f".{part}"
    return out


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    first = errors[0] if errors else {"loc": (), "msg": "invalid request"}
    message = first.get("msg", "invalid request")
    if message.startswith("Value error, "):
        message = message[len("Value error, ") :]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "message": message,
                "field": _format_location(tuple(first.get("loc", ()))),
            }
        },
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/verify", response_model=VerifyResponse)
async def verify_endpoint(payload: VerifyRequest) -> VerifyResponse:
    block = [tuple(bell - 1 for bell in change) for change in payload.block]
    result = verify(block, payload.repeats)

    witness = None
    if result.witness is not None:
        witness = WitnessPayload(
            first_step=result.witness.first_step,
            second_step=result.witness.second_step,
            row=[bell + 1 for bell in result.witness.row],
        )
    final_row = (
        [bell + 1 for bell in result.final_row]
        if result.final_row is not None
        else None
    )
    return VerifyResponse(
        status=result.status,
        outcome=result.outcome,
        bells=result.bells,
        block_size=result.block_size,
        repeats=result.repeats,
        total_steps=result.total_steps,
        block_order=result.block_order,
        witness=witness,
        final_row=final_row,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("API_PORT", "8000")),
    )
