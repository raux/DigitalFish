"""Digital Ichthyologist: Evolutionary Code Analyst.

Treats a Git repository as a digital ecosystem, tracking the survival,
mutation, and extinction of "Digital Fish" (functions/classes) over time.
"""

from .fish import DigitalFish
from .extractor import get_functions_and_classes
from .analyzer import Analyzer
from .reporter import Reporter
from .vita import Vita

__all__ = [
    "DigitalFish",
    "get_functions_and_classes",
    "Analyzer",
    "Reporter",
    "Vita",
]
