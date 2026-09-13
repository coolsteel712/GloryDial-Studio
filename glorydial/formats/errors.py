"""Human-readable validation errors for the format layer and UI."""

from __future__ import annotations

from typing import List


class ValidationError(Exception):
    """Raised for a single, human-readable validation problem."""


class ValidationReport:
    """Collects zero or more human-readable problems so the UI can show
    them all at once instead of stopping at the first one."""

    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def ok(self) -> bool:
        return not self.errors

    def raise_if_errors(self) -> None:
        if self.errors:
            bullet_list = "\n".join(f"  - {e}" for e in self.errors)
            raise ValidationError(f"Cannot proceed - {len(self.errors)} problem(s) found:\n{bullet_list}")
