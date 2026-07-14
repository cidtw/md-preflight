"""Application errors for the modular pipeline."""

from __future__ import annotations

from typing import final


class AppError(Exception):
    """Base application error."""


@final
class InputValidationError(AppError):
    """Raised when client parameters fail the input template."""

    message: str

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
