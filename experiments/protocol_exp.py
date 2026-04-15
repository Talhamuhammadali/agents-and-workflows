"""Understanding the differences between dataclasses and TypedDicts in Python for protcol."""

from dataclasses import dataclass
from pprint import pprint
from typing import NotRequired, TypedDict


@dataclass
class Model:
    """Model configuration for the subagent pattern."""

    name: str
    temperature: float


class ModelConfig(TypedDict):
    """TypedDict for model configuration."""

    name: str
    temperature: float
    some_optional_field: NotRequired[str]


if __name__ == "__main__":
    # checking the dataclass and TypedDict fields
    print(f"Model dataclass fields:{type(Model.__dataclass_fields__)}\n\n")
    pprint(Model.__dataclass_fields__, indent=2)

    print(f"{ModelConfig.__required_keys__} and its type is {type(ModelConfig.__required_keys__)}")
    print(f"{ModelConfig.__optional_keys__} and its type is {type(ModelConfig.__optional_keys__)}")
