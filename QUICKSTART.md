# MatSelect AI - Quick Start Guide

Welcome! This guide will get you up and running with MatSelect AI in minutes.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Your Materials Project API Key

1. Go to https://materialsproject.org
2. Create a free account (takes 30 seconds)
3. Go to your dashboard
4. Click "Generate API Key"
5. Copy your API key

### 3. Set Your API Key

**Option A: Environment Variable (Recommended)**
```bash
export MP_API_KEY="your_api_key_here"
```

**Option B: In Python**
```python
from matselect import MatSelectAI
ms = MatSelectAI(mp_api_key="your_api_key_here")
```

## Example 1: Find Lightweight, Strong Materials

You're designing an aerospace component. You need something strong but lightweight.

```python
from matselect import MatSelectAI

# Initialize
ms = MatSelectAI()

# Define requirements
results = ms.recommend(
    requirements={
        'max_density': 3.0,      # g/cm³ - keep it light
        'min_band_gap': 0.0,     # Metallic (conductive)
        'max_band_gap': 0.5,     
    },
    optimize=['weight'],
    top_n=5
)

# View results
results.display()
```

**Expected Output:**
```
🔍 Searching Materials Project database...
✓ Found 847 candidate materials
✓ 234 materials passed all filters
✅ Returning top 5 recommendations

================================================================================
  TOP 5 MATERIAL RECOMMENDATIONS
================================================================================

#1 - Al (mp-134)
   ✓ Match Score: 85.3%
   ✓ Density: 2.70 g/cm³
   ✓ Band Gap: 0.00 eV
   ✓ Stability: 0.000 eV/atom above hull
   ✓ Crystal System: cubic

   Why Recommended: Thermodynamically stable; Lightweight; Highly stable

--------------------------------------------------------------------------------

#2 - Mg (mp-153)
   ✓ Match Score: 88.1%
   ✓ Density: 1.74 g/cm³
   ...
```

## Example 2: Semiconductor Search

Looking for semiconductors with specific band gap for solar cells.

```python
results = ms.recommend(
    requirements={
        'min_band_gap': 1.0,     # eV
        'max_band_gap': 2.0,     # Ideal for solar
        'max_density': 8.0,
    },
    optimize=['weight'],
    top_n=5
)

results.display()
```

## Example 3: Compare Specific Materials

You know some material IDs and want to compare them.

```python
comparison = ms.what_if(
    baseline_material='mp-149',      # Silicon
    alternative_materials=[
        'mp-22526',  # GaAs
        'mp-2534',   # CdTe
    ],
    show_savings=True
)

print(comparison)
```

## Example 4: Explore Trade-offs

See the Pareto frontier between competing objectives.

```python
tradeoffs = ms.explore_tradeoffs(
    requirements={
        'max_density': 5.0,
        'min_band_gap': 0.5,
    },
    optimize=['weight', 'stability']
)

# This will show you can't optimize everything at once
tradeoffs.plot_pareto_frontier()
```

## Example 5: Export Results

Save your recommendations for later.

```python
results = ms.recommend(
    requirements={'max_density': 3.0},
    top_n=10
)

# Export to CSV
results.export_to_csv('my_materials.csv')

# Or get as DataFrame for further analysis
df = results.to_dataframe()
print(df.columns)
```

## Next Steps

1. **Try different requirements** - Experiment with various constraints
2. **Optimize for different objectives** - Try optimizing for weight, cost, or performance
3. **Explore the Materials Project** - Visit materialsproject.org to learn more
4. **Check out advanced examples** - See `examples/` folder for more

## Need Help?

- **Documentation**: See README.md
- **Issues**: https://github.com/aaburakhia/matselect/issues
- **Materials Project Docs**: https://docs.materialsproject.org

## Common Issues

**"Cannot connect to Materials Project API"**
- Check your API key is correct
- Make sure you set the environment variable
- Try passing api_key directly to MatSelectAI()

**"No materials found"**
- Try relaxing some constraints
- Check that your requirements aren't contradictory
- Start with broader search, then narrow down

**Import errors**
- Make sure you installed all dependencies: `pip install -r requirements.txt`
- Check you're in the right directory
