from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ReviewContext:
    review_text: str
    business_name: str
    rating: int
    tone: str = "warm"       # formal / warm / casual
    language: str = "auto"   # auto-detect from review


class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(self, context: ReviewContext) -> str:
        pass
