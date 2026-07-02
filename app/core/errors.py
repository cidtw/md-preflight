from dataclasses import dataclass

from typing_extensions import override


@dataclass(frozen=True, slots=True)
class IngestError(Exception):
    message: str

    @override
    def __str__(self) -> str:
        return self.message
