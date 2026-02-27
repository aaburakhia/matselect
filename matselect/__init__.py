"""
MatSelect AI - Intelligent Materials Decision Assistant

Stop wasting hours on materials selection. Make data-driven decisions in minutes.
"""

__version__ = "0.1.0"
__author__ = "Ahmed Awad"

from .core.recommender import MatSelectAI, RecommendationResults, TradeOffAnalysis
from .sources.materials_project import MaterialsProjectSource

__all__ = [
    'MatSelectAI',
    'RecommendationResults', 
    'TradeOffAnalysis',
    'MaterialsProjectSource'
]
