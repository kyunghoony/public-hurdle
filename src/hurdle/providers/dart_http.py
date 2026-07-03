from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, TypeAlias

import requests
from typing_extensions import override

DartRow: TypeAlias = Mapping[str, str]
DartPayload: TypeAlias = Mapping[str, str | list[DartRow]]


class HttpResponse(Protocol):
    @property
    def content(self) -> bytes:
        ...

    def json(self) -> DartPayload:
        ...

    def raise_for_status(self) -> None:
        ...


class HttpSession(Protocol):
    def get(self, url: str, *, params: Mapping[str, str], timeout: float) -> HttpResponse:
        ...


class RequestsResponse(Protocol):
    @property
    def content(self) -> bytes:
        ...

    def json(self) -> DartPayload:
        ...

    def raise_for_status(self) -> None:
        ...


@dataclass(frozen=True, slots=True)
class DartTransportError(Exception):
    detail: str

    @override
    def __str__(self) -> str:
        return f"OpenDART transport error: {self.detail}"


@dataclass(frozen=True, slots=True)
class RequestsHttpResponse:
    response: RequestsResponse

    @property
    def content(self) -> bytes:
        return self.response.content

    def json(self) -> DartPayload:
        return self.response.json()

    def raise_for_status(self) -> None:
        self.response.raise_for_status()


@dataclass(frozen=True, slots=True)
class RequestsHttpSession:
    session: requests.Session = field(default_factory=requests.Session)

    def get(self, url: str, *, params: Mapping[str, str], timeout: float) -> HttpResponse:
        return RequestsHttpResponse(response=self.session.get(url, params=params, timeout=timeout))


def default_session() -> HttpSession:
    return RequestsHttpSession()
