"""Understanding the differences between dataclasses and TypedDicts in Python for protcol."""

from dataclasses import dataclass
from pprint import pprint
from typing import NotRequired, Optional, TypedDict
from pydantic import BaseModel

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

class ModelConfigP(BaseModel):
    """Pydantic model for model configuration."""

    name: str
    temperature: float
    some_optional_field: Optional[str]
    
if __name__ == "__main__":
    # checking the dataclass and TypedDict fields
    print(f"Model dataclass fields:{type(Model.__dataclass_fields__)}\n\n")
    pprint(Model.__dataclass_fields__, indent=2)

    print(f"{ModelConfig.__required_keys__} and its type is {type(ModelConfig.__required_keys__)}")
    print(f"{ModelConfig.__optional_keys__} and its type is {type(ModelConfig.__optional_keys__)}")
    
    model_config = ModelConfigP(name="gpt-3.5-turbo", temperature=0.7, some_optional_field="optional value")
    print("===="*8) 
    copy_model_config = model_config.model_copy(deep=True)
    print(f"Original model config: {model_config is copy_model_config} and {model_config == copy_model_config}")
    model_config.some_optional_field = "changed value"
    print(f"After modification, original model config: {model_config} and copy model config: {copy_model_config}")
    