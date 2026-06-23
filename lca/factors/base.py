from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from ..models import EmissionFactorSet


@dataclass
class FactorCandidate:
    record_id: str
    material_name: str
    declared_unit: str
    source: str
    source_type: str
    geography: str = ""
    citation: str = ""
    preview_gwp_a1a3: float = 0.0


class FactorAdapter(ABC):
    name: str

    @abstractmethod
    def search(self, query: str, limit: int = 20) -> List[FactorCandidate]:
        raise NotImplementedError

    @abstractmethod
    def get(self, record_id: str) -> EmissionFactorSet:
        raise NotImplementedError
