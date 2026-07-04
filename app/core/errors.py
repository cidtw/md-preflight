from dataclasses import dataclass

from typing_extensions import override


@dataclass(frozen=True, slots=True)
class IngestError(Exception):
    message: str

    @override
    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True, slots=True)
class UploadValidationError(Exception):
    message: str
    status_code: int

    @override
    def __str__(self) -> str:
        return self.message
