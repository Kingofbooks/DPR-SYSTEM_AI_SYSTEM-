from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


@dataclass
class Section:
    title: str
    start_page: int
    end_page: int
    content: str = ""


@dataclass
class DocumentStructure:
    metadata: Dict[str, Any] = field(default_factory=dict)
    sections: List[Section] = field(default_factory=list)

    def to_dict(self):
        return {
            "metadata": self.metadata,
            "sections": [asdict(section) for section in self.sections],
        }