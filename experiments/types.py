"""Shared types for agentic patterns."""

from dataclasses import Field
from typing import Any, ClassVar, Protocol

from pydantic import BaseModel


class DataClassObjs(Protocol):
    """Protocol for dataclasses."""

    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


class TypedictObjs(Protocol):
    """Protocol for Pydantic models."""

    __required_keys__: frozenset[str]
    __optional_keys__: frozenset[str]


type AgentConfiguration = DataClassObjs | TypedictObjs | BaseModel
