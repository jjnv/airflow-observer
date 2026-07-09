from pydantic import BaseModel, Field


class AlertChannelIn(BaseModel):
    kind: str = Field(default="slack", pattern="^slack$")
    name: str
    target: str
    is_enabled: bool = True
