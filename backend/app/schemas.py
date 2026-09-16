"""Pydantic request/response models with strict input validation.

Rows use one-based bell numbers on the wire (1 .. bells); the verifier works
with zero-based positions, so conversion happens only at the boundary.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    model_validator,
)
from pydantic_core import InitErrorDetails

MIN_BELLS = 4
MAX_BELLS = 12
MIN_BLOCK_SIZE = 1
MAX_BLOCK_SIZE = 5000
MIN_REPEATS = 1
MAX_REPEATS = 1_000_000_000_000

Bells = Annotated[int, Field(strict=True, ge=MIN_BELLS, le=MAX_BELLS)]
Repeats = Annotated[int, Field(strict=True, ge=MIN_REPEATS, le=MAX_REPEATS)]


class VerifyRequest(BaseModel):
    bells: Bells
    repeats: Repeats
    block: list[list[int]] = Field(
        min_length=MIN_BLOCK_SIZE, max_length=MAX_BLOCK_SIZE
    )

    @model_validator(mode="before")
    @classmethod
    def _reject_non_integer_bells(cls, data: object) -> object:
        """Inspect raw JSON before int coercion.

        Pydantic's plain ``int`` accepts numeric strings and floats; change
        rows must be exact JSON integers.  ``type(x) is int`` also rejects
        booleans (which are an ``int`` subclass in Python).  Errors point at
        the first offending row, block[i].
        """
        if not isinstance(data, dict):
            return data
        bells = data.get("bells")
        block = data.get("block")
        # Only run when bells itself is a genuine integer; otherwise the
        # scalar field error takes precedence.
        if type(bells) is not int or not isinstance(block, list):
            return data
        errors: list[InitErrorDetails] = []
        for index, row in enumerate(block):
            if not isinstance(row, list):
                errors.append(
                    InitErrorDetails(
                        type="value_error",
                        loc=("block", index),
                        ctx={
                            "error": ValueError(
                                f"block[{index}] must be a list of integers"
                            )
                        },
                    )
                )
                break
            for value in row:
                if type(value) is not int:
                    errors.append(
                        InitErrorDetails(
                            type="value_error",
                            loc=("block", index),
                            ctx={
                                "error": ValueError(
                                    f"block[{index}] must contain only JSON "
                                    f"integers, found {value!r}"
                                )
                            },
                        )
                    )
                    break
            if errors:
                break
        if errors:
            raise ValidationError.from_exception_data(
                cls.__name__, errors
            )
        return data

    @model_validator(mode="after")
    def _validate_block_rows(self) -> "VerifyRequest":
        required = set(range(1, self.bells + 1))
        errors: list[InitErrorDetails] = []
        for index, row in enumerate(self.block):
            if len(row) != self.bells:
                errors.append(
                    InitErrorDetails(
                        type="value_error",
                        loc=("block", index),
                        ctx={
                            "error": ValueError(
                                f"block[{index}] has length {len(row)}, "
                                f"expected {self.bells}"
                            )
                        },
                    )
                )
            elif set(row) != required:
                errors.append(
                    InitErrorDetails(
                        type="value_error",
                        loc=("block", index),
                        ctx={
                            "error": ValueError(
                                f"block[{index}] must be a permutation of "
                                f"1..{self.bells}, got {row}"
                            )
                        },
                    )
                )
        if errors:
            raise ValidationError.from_exception_data(
                self.__class__.__name__, errors
            )
        return self


class WitnessPayload(BaseModel):
    first_step: int = Field(ge=0)
    second_step: int = Field(ge=1)
    row: list[int]


class VerifyResponse(BaseModel):
    status: str  # "pass" | "fail"
    outcome: str | None  # "collision" | "not_home" | null
    bells: int
    block_size: int
    repeats: int
    total_steps: int
    block_order: int
    witness: WitnessPayload | None
    final_row: list[int] | None
