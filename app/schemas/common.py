from typing import Any
from pydantic import BaseModel, Field, model_validator


class Point(BaseModel):
    x: float
    y: float


class Polygon(BaseModel):
    points: list[Point] = Field(min_length=3)


class BBox(BaseModel):
    """Pixel-space XYXY bounding box."""

    x1: float = Field(ge=0)
    y1: float = Field(ge=0)
    x2: float = Field(ge=0)
    y2: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_order(self) -> "BBox":
        if self.x2 < self.x1 or self.y2 < self.y1:
            raise ValueError("bbox must satisfy x2 >= x1 and y2 >= y1")
        return self

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


JsonDict = dict[str, Any]
