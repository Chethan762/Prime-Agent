from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ReviewFields:
    author: Optional[str] = None
    rating: Optional[str] = None
    review_text: Optional[str] = None
    date: Optional[str] = None


@dataclass
class SiteAnalysis:
    page_type: str
    review_section_found: bool
    review_container: Optional[str] = None
    fields: ReviewFields = field(default_factory=ReviewFields)
    confidence: float = 0.0
    reasoning: Optional[str] = None
