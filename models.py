from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class Message(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    text: str = Field(min_length=1, max_length=1000)
    clip: str = Field(min_length=1, max_length=650000)
    permission: Literal[True]
