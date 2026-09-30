from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Mapping

from style_config import StyleConfig


class ProviderError(RuntimeError):
    def __init__(self, provider: str, stage: str, error: str, suggestion: str = "") -> None:
        self.provider = provider
        self.stage = stage
        self.error = error
        self.suggestion = suggestion
        self.error_code: str | None = None
        self.http_status: int | None = None
        self.request_id: str | None = None
        super().__init__(f"[{provider}/{stage}] {error}" + (f" Suggestion: {suggestion}" if suggestion else ""))

    def to_debug(self) -> dict[str, str]:
        result = {
            "provider": self.provider,
            "stage": self.stage,
            "error": self.error,
            "suggestion": self.suggestion,
        }
        if self.error_code:
            result["errorCode"] = self.error_code
        if self.http_status is not None:
            result["httpStatus"] = str(self.http_status)
        if self.request_id:
            result["requestId"] = self.request_id
        return result


class ImageProvider(ABC):
    name: str

    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        raise NotImplementedError

    @abstractmethod
    def generate(
        self,
        request_data: Mapping[str, object],
        enhanced_prompt: str,
        negative_prompt: str,
        style_config: StyleConfig,
        image_analysis: Mapping[str, str],
        culture_card: Mapping[str, str],
        *,
        base_url: str,
    ) -> dict[str, object]:
        raise NotImplementedError
