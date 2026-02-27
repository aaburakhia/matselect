"""
Main Recommendation Engine for MatSelect AI

Combines multiple data sources and ML techniques to provide
intelligent materials recommendations.
"""

from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from ..sources.materials_project import MaterialsProjectSource


class MatSelectAI:
    """
    Main interface for MatSelect AI recommendation system.
    
    Provides high-level methods for materials selection with
    multi-criteria optimization, trade-off analysis, and
    intelligent decision support.
    """
    
    def __init__(self, mp_api_key: Optional[str] = None):
        """
        Initialize MatSelect AI.
        
        Args:
            mp_api_key: Materials Project API key (or use MP_API_KEY env var)
        """
        self.mp_source = MaterialsProjectSource(api_key=mp_api_key)
        self._verify_setup()
    
    def _verify_setup(self):
        """Verify that all data sources are accessible."""
        if not self.mp_source.check_api_status():
            raise ConnectionError(
                "Cannot connect to Materials Project API. "
                "Please check your API key."
            )
        print("✓ Materials Project API connected")
    
    def recommend(self,
                  requirements: Dict[str, Any],
                  optimize: Optional[List[str]] = None,
                  show_tradeoffs: bool = False,
                  top_n: int = 5) -> 'RecommendationResults':
        """
        Get material recommendations based on requirements.
        
        Args:
            requirements: Dictionary of requirements:
                - min_strength: Minimum strength required (MPa)
                - max_density: Maximum density (g/cm³)
                - max_temp: Maximum service temperature (°C)
                - max_cost_per_kg: Maximum material cost (USD/kg)
                - min_band_gap: Minimum band gap (eV) for electronic apps
                - max_band_gap: Maximum band gap (eV)
                - corrosion_resistance: Required level
                - elements: List of required/excluded elements
            optimize: List of objectives to optimize ['cost', 'weight', 'strength']
            show_tradeoffs: Whether to show trade-off analysis
            top_n: Number of recommendations to return
            
        Returns:
            RecommendationResults object with materials and analysis
        """
        print(f"🔍 Searching Materials Project database...")
        
        # Extract Materials Project relevant criteria
        mp_criteria = {}
        
        if 'min_band_gap' in requirements:
            mp_criteria['min_band_gap'] = requirements['min_band_gap']
        if 'max_band_gap' in requirements:
            mp_criteria['max_band_gap'] = requirements['max_band_gap']
        if 'elements' in requirements:
            mp_criteria['elements'] = requirements['elements']
        
        # Search Materials Project
        candidates = self.mp_source.search_by_properties(**mp_criteria, limit=100)
        
        if len(candidates) == 0:
            print("❌ No materials found matching criteria")
            return RecommendationResults(candidates=pd.DataFrame(), requirements=requirements)
        
        print(f"✓ Found {len(candidates)} candidate materials")
        
        # Apply additional filters
        filtered = self._apply_filters(candidates, requirements)
        
        print(f"✓ {len(filtered)} materials passed all filters")
        
        # Score and rank
        scored = self._score_materials(filtered, requirements, optimize)
        
        # Get top N
        top_materials = scored.head(top_n)
        
        # Enrich with additional data
        enriched = self._enrich_materials(top_materials)
        
        print(f"✅ Returning top {len(enriched)} recommendations")
        
        return RecommendationResults(
            candidates=enriched,
            requirements=requirements,
            optimize_objectives=optimize,
            show_tradeoffs=show_tradeoffs
        )
    
    def _apply_filters(self, 
                       candidates: pd.DataFrame, 
                       requirements: Dict[str, Any]) -> pd.DataFrame:
        """
        Apply hard constraint filters to candidate materials.
        
        Args:
            candidates: DataFrame of candidate materials
            requirements: User requirements
            
        Returns:
            Filtered DataFrame
        """
        filtered = candidates.copy()
        
        # Density filter
        if 'max_density' in requirements:
            filtered = filtered[filtered['density'] <= requirements['max_density']]
        
        # Stability filter (only stable or near-stable materials)
        filtered = filtered[filtered['energy_above_hull'] <= 0.1]
        
        # TODO: Add more filters as we expand
        # - Temperature stability
        # - Corrosion resistance (need additional data source)
        # - Cost (need cost database)
        
        return filtered
    
    def _score_materials(self,
                        materials: pd.DataFrame,
                        requirements: Dict[str, Any],
                        optimize: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Score materials based on how well they match requirements.
        
        Args:
            materials: Filtered candidate materials
            requirements: User requirements
            optimize: Optimization objectives
            
        Returns:
            DataFrame with match_score column, sorted by score
        """
        scored = materials.copy()
        
        # Initialize score
        scores = np.zeros(len(scored))
        
        # Density score (lower is better for weight optimization)
        if optimize and 'weight' in optimize:
            if 'density' in scored.columns:
                density_normalized = 1 - (scored['density'] - scored['density'].min()) / \
                                    (scored['density'].max() - scored['density'].min() + 1e-10)
                scores += density_normalized * 30
        
        # Stability score (lower energy above hull is better)
        if 'energy_above_hull' in scored.columns:
            stability_score = 1 - (scored['energy_above_hull'] / 0.1)
            stability_score = stability_score.clip(0, 1)
            scores += stability_score * 40
        
        # Band gap score (closer to requirements is better)
        if 'min_band_gap' in requirements and 'band_gap' in scored.columns:
            target = requirements.get('min_band_gap', 0)
            gap_diff = abs(scored['band_gap'] - target)
            gap_score = 1 - (gap_diff / (scored['band_gap'].max() + 1))
            gap_score = gap_score.clip(0, 1)
            scores += gap_score * 30
        
        # Add baseline score for materials that passed filters
        scores += 10
        
        scored['match_score'] = scores
        
        return scored.sort_values('match_score', ascending=False)
    
    def _enrich_materials(self, materials: pd.DataFrame) -> pd.DataFrame:
        """
        Enrich materials with additional information.
        
        Args:
            materials: Top-ranked materials
            
        Returns:
            Enriched DataFrame with explanations
        """
        enriched = materials.copy()
        
        # Add recommendation reasons
        reasons = []
        for idx, row in enriched.iterrows():
            reason_parts = []
            
            if row.get('is_stable', False):
                reason_parts.append("Thermodynamically stable")
            
            if row.get('density', 10) < 5.0:
                reason_parts.append("Lightweight")
            
            if row.get('energy_above_hull', 1) < 0.02:
                reason_parts.append("Highly stable")
            
            reasons.append("; ".join(reason_parts) if reason_parts else "Meets requirements")
        
        enriched['recommendation_reason'] = reasons
        
        return enriched
    
    def explore_tradeoffs(self,
                         requirements: Dict[str, Any],
                         optimize: List[str]) -> 'TradeOffAnalysis':
        """
        Explore trade-offs between competing objectives.
        
        Args:
            requirements: Base requirements
            optimize: Objectives to trade off (e.g., ['cost', 'weight', 'strength'])
            
        Returns:
            TradeOffAnalysis object with Pareto frontier
        """
        # Get candidates
        results = self.recommend(requirements, optimize=optimize, top_n=20)
        
        return TradeOffAnalysis(
            materials=results.candidates,
            objectives=optimize
        )
    
    def what_if(self,
                baseline_material: str,
                alternative_materials: List[str],
                show_savings: bool = True) -> pd.DataFrame:
        """
        Compare baseline material with alternatives.
        
        Args:
            baseline_material: MP ID of current material
            alternative_materials: List of MP IDs to compare
            show_savings: Whether to show percentage differences
            
        Returns:
            Comparison DataFrame
        """
        materials_to_compare = [baseline_material] + alternative_materials
        
        comparison_data = []
        for mp_id in materials_to_compare:
            try:
                mat_data = self.mp_source.get_material_by_id(mp_id)
                comparison_data.append(mat_data)
            except ValueError:
                print(f"Warning: Material {mp_id} not found")
        
        df = pd.DataFrame(comparison_data)
        
        if show_savings and len(df) > 1:
            # Calculate percentage differences from baseline
            baseline = df.iloc[0]
            for col in ['density', 'band_gap', 'formation_energy']:
                if col in df.columns:
                    df[f'{col}_vs_baseline_%'] = \
                        ((df[col] - baseline[col]) / baseline[col] * 100).round(1)
        
        return df


class RecommendationResults:
    """Container for recommendation results with display methods."""
    
    def __init__(self, 
                 candidates: pd.DataFrame,
                 requirements: Dict[str, Any],
                 optimize_objectives: Optional[List[str]] = None,
                 show_tradeoffs: bool = False):
        self.candidates = candidates
        self.requirements = requirements
        self.optimize_objectives = optimize_objectives
        self.show_tradeoffs = show_tradeoffs
    
    def display(self):
        """Display recommendations in a formatted way."""
        if len(self.candidates) == 0:
            print("\n❌ No materials found matching your requirements.")
            print("\nTry:")
            print("  - Relaxing some constraints")
            print("  - Broadening the search criteria")
            return
        
        print("\n" + "="*80)
        print(f"  TOP {len(self.candidates)} MATERIAL RECOMMENDATIONS")
        print("="*80 + "\n")
        
        for idx, (_, row) in enumerate(self.candidates.iterrows(), 1):
            print(f"#{idx} - {row['formula']} ({row['mp_id']})")
            print(f"   ✓ Match Score: {row.get('match_score', 0):.1f}%")
            print(f"   ✓ Density: {row.get('density', 0):.2f} g/cm³")
            print(f"   ✓ Band Gap: {row.get('band_gap', 0):.2f} eV")
            print(f"   ✓ Stability: {row.get('energy_above_hull', 0):.3f} eV/atom above hull")
            print(f"   ✓ Crystal System: {row.get('crystal_system', 'Unknown')}")
            
            if 'recommendation_reason' in row:
                print(f"\n   Why Recommended: {row['recommendation_reason']}")
            
            print("\n" + "-"*80 + "\n")
    
    def to_dataframe(self) -> pd.DataFrame:
        """Return results as DataFrame."""
        return self.candidates
    
    def export_to_csv(self, filename: str):
        """Export results to CSV file."""
        self.candidates.to_csv(filename, index=False)
        print(f"✓ Results exported to {filename}")


class TradeOffAnalysis:
    """Container for trade-off analysis results."""
    
    def __init__(self, materials: pd.DataFrame, objectives: List[str]):
        self.materials = materials
        self.objectives = objectives
    
    def plot_pareto_frontier(self):
        """Plot Pareto frontier of trade-offs."""
        # TODO: Implement Pareto frontier visualization
        print("📊 Pareto frontier plotting coming soon!")
        print(f"Objectives: {', '.join(self.objectives)}")
        print(f"Materials on frontier: {len(self.materials)}")
