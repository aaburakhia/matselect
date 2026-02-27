"""
Materials Project API Integration

This module handles all interactions with the Materials Project database.
"""

import os
from typing import List, Dict, Optional, Any
import pandas as pd
from mp_api.client import MPRester


class MaterialsProjectSource:
    """
    Interface to the Materials Project database via their API.
    
    Provides methods to search, retrieve, and analyze materials data
    from the Materials Project's 150,000+ material database.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Materials Project client.
        
        Args:
            api_key: Materials Project API key. If None, reads from 
                    MP_API_KEY environment variable.
        """
        self.api_key = api_key or os.getenv('MP_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Materials Project API key required. Either pass api_key parameter "
                "or set MP_API_KEY environment variable. Get your key at: "
                "https://materialsproject.org/dashboard"
            )
    
    def search_by_properties(self,
                            elements: Optional[List[str]] = None,
                            min_band_gap: Optional[float] = None,
                            max_band_gap: Optional[float] = None,
                            min_energy_above_hull: Optional[float] = None,
                            max_energy_above_hull: Optional[float] = 0.05,
                            crystal_systems: Optional[List[str]] = None,
                            limit: int = 100) -> pd.DataFrame:
        """
        Search for materials by property constraints.
        
        Args:
            elements: List of elements to include (e.g., ['Fe', 'O'])
            min_band_gap: Minimum band gap in eV
            max_band_gap: Maximum band gap in eV
            min_energy_above_hull: Min energy above hull (stability metric)
            max_energy_above_hull: Max energy above hull (default 0.05 eV/atom)
            crystal_systems: Filter by crystal system
            limit: Maximum number of results
            
        Returns:
            DataFrame with material properties
        """
        with MPRester(self.api_key) as mpr:
            # Build search criteria
            # Always filter for stable or near-stable materials
            if max_energy_above_hull is None:
                max_energy_above_hull = 0.1  # Default: only stable/near-stable materials
            
            # Search with proper parameter format
            search_params = {
                'energy_above_hull': (0, max_energy_above_hull),
            }
            
            if elements:
                search_params['elements'] = elements
            
            if min_band_gap is not None or max_band_gap is not None:
                bg_min = min_band_gap if min_band_gap is not None else 0
                bg_max = max_band_gap if max_band_gap is not None else 15
                search_params['band_gap'] = (bg_min, bg_max)
            
            # Search
            docs = mpr.materials.summary.search(
                **search_params,
                fields=[
                    'material_id', 'formula_pretty', 'composition',
                    'energy_above_hull', 'band_gap', 'density',
                    'formation_energy_per_atom', 'symmetry',
                    'theoretical', 'is_stable'
                ]
            )
            
            # Convert to DataFrame
            data = []
            for doc in docs[:limit]:
                data.append({
                    'mp_id': str(doc.material_id),
                    'formula': doc.formula_pretty,
                    'composition': str(doc.composition),
                    'energy_above_hull': doc.energy_above_hull,
                    'band_gap': doc.band_gap,
                    'density': doc.density,
                    'formation_energy': doc.formation_energy_per_atom,
                    'crystal_system': doc.symmetry.crystal_system.value if doc.symmetry else None,
                    'is_stable': doc.is_stable,
                    'is_theoretical': doc.theoretical
                })
            
            return pd.DataFrame(data)
    
    def get_material_by_id(self, material_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific material.
        
        Args:
            material_id: Materials Project ID (e.g., 'mp-149')
            
        Returns:
            Dictionary with comprehensive material data
        """
        with MPRester(self.api_key) as mpr:
            docs = mpr.materials.summary.search(
                material_ids=[material_id],
                fields=[
                    'material_id', 'formula_pretty', 'composition',
                    'energy_above_hull', 'band_gap', 'density',
                    'formation_energy_per_atom', 'symmetry',
                    'theoretical', 'is_stable', 'volume',
                    'elastic', 'piezoelectric', 'dielectric'
                ]
            )
            
            if not docs:
                raise ValueError(f"Material {material_id} not found")
            
            doc = docs[0]
            
            # Build comprehensive response
            result = {
                'mp_id': str(doc.material_id),
                'formula': doc.formula_pretty,
                'composition': str(doc.composition),
                'energy_above_hull': doc.energy_above_hull,
                'band_gap': doc.band_gap,
                'density': doc.density,
                'formation_energy': doc.formation_energy_per_atom,
                'volume': doc.volume,
                'crystal_system': doc.symmetry.crystal_system.value if doc.symmetry else None,
                'space_group': doc.symmetry.symbol if doc.symmetry else None,
                'is_stable': doc.is_stable,
                'is_theoretical': doc.theoretical
            }
            
            # Add elastic properties if available
            if doc.elastic:
                result['bulk_modulus'] = doc.elastic.k_vrh
                result['shear_modulus'] = doc.elastic.g_vrh
                result['youngs_modulus'] = doc.elastic.universal_anisotropy
            
            return result
    
    def search_by_formula(self, formula: str) -> pd.DataFrame:
        """
        Search for materials by chemical formula.
        
        Args:
            formula: Chemical formula (e.g., 'Fe2O3', 'SiO2')
            
        Returns:
            DataFrame with matching materials
        """
        with MPRester(self.api_key) as mpr:
            docs = mpr.materials.summary.search(
                formula=formula,
                fields=[
                    'material_id', 'formula_pretty', 'energy_above_hull',
                    'band_gap', 'density', 'is_stable'
                ]
            )
            
            data = []
            for doc in docs:
                data.append({
                    'mp_id': str(doc.material_id),
                    'formula': doc.formula_pretty,
                    'energy_above_hull': doc.energy_above_hull,
                    'band_gap': doc.band_gap,
                    'density': doc.density,
                    'is_stable': doc.is_stable
                })
            
            return pd.DataFrame(data)
    
    def get_similar_materials(self, 
                             material_id: str,
                             similarity_type: str = 'structure',
                             limit: int = 10) -> pd.DataFrame:
        """
        Find materials similar to a reference material.
        
        Args:
            material_id: Reference material MP ID
            similarity_type: Type of similarity ('structure', 'composition')
            limit: Maximum number of similar materials to return
            
        Returns:
            DataFrame with similar materials
        """
        # Get reference material
        reference = self.get_material_by_id(material_id)
        
        if similarity_type == 'composition':
            # Find materials with similar composition
            elements = reference['composition'].split()
            return self.search_by_properties(
                elements=elements,
                limit=limit
            )
        
        # TODO: Implement structure-based similarity
        # This would require comparing crystal structures
        raise NotImplementedError("Structure-based similarity coming soon")
    
    def get_property_range(self, property_name: str) -> tuple:
        """
        Get the range of values for a property across all materials.
        
        Args:
            property_name: Name of the property (e.g., 'band_gap', 'density')
            
        Returns:
            Tuple of (min_value, max_value)
        """
        # This would require a full database scan - expensive
        # For now, return reasonable ranges
        ranges = {
            'band_gap': (0, 15),
            'density': (0.5, 25),
            'formation_energy': (-10, 2)
        }
        
        return ranges.get(property_name, (None, None))
    
    def check_api_status(self) -> bool:
        """
        Check if the API key is valid and API is accessible.
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            with MPRester(self.api_key) as mpr:
                # Try a simple query
                docs = mpr.materials.summary.search(
                    material_ids=['mp-149'],
                    fields=['material_id']
                )
                return len(docs) > 0
        except Exception as e:
            print(f"API check failed: {e}")
            return False


# Utility functions

def format_formula(formula: str) -> str:
    """Format chemical formula with subscripts for display."""
    import re
    return re.sub(r'(\d+)', r'₀₁₂₃₄₅₆₇₈₉'[int(r'\1')], formula)


def get_element_list(formula: str) -> List[str]:
    """Extract list of elements from chemical formula."""
    import re
    return re.findall(r'[A-Z][a-z]?', formula)
