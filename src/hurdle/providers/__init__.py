"""프로바이더 레지스트리 — OpenBB 'connect once, consume everywhere' 패턴.

엔진은 프로바이더를 모른다. 모든 소스는 models.Ticker로 변환된 뒤 진입.
"""
from . import dart, yahoo  # noqa: F401

REGISTRY = {"dart": dart, "yahoo": yahoo}
