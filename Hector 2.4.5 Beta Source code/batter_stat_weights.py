# Batter Stats Weights Configuration
# These weights are used when "Use Stats-Based Scoring" is enabled
# Stats are from the HTML export and are used to calculate player value
# based on actual performance rather than ratings

# Minimum sample size requirements
# Players with less than this threshold will use ratings-only scoring
MIN_PLATE_APPEARANCES = 50  # Minimum games (G) for batters - proxy for plate appearances

stat_weights = {
    # High Priority - Primary value metrics
    "wRC+": {
        "weight": 0.30,
        "description": "Weighted Runs Created Plus - primary offensive value metric",
        "baseline": 100,  # League average
        "higher_is_better": True
    },
    "WAR (Batter)": {
        "weight": 0.30,
        "description": "Wins Above Replacement - overall value",
        "baseline": 0,
        "higher_is_better": True
    },
    
    # Medium Priority - Supporting metrics
    "OPS+": {
        "weight": 0.15,
        "description": "OPS Plus - park-adjusted OPS",
        "baseline": 100,
        "higher_is_better": True
    },
    
    # Lower Priority - Additional context
    "G": {
        "weight": 0.05,
        "description": "Games played - sample size indicator",
        "baseline": 0,
        "higher_is_better": True,
        "scale_factor": 0.01  # Scale down to reasonable contribution
    },
    
    # Age adjustments for trade value
    "age_adjustment": {
        "veteran_bonus": 0.0,  # No bonus for veterans in pure stat scoring
        "prospect_bonus": 0.0,  # No bonus for prospects in pure stat scoring
        "description": "Age adjustments are handled separately in Trade Finder"
    }
}

# Normalization settings
normalization = {
    "wRC+": {
        "min": 50,   # Below this is replacement level
        "max": 180,  # Elite level
        "scale_to": 100  # Scale contribution to this max value
    },
    "WAR (Batter)": {
        "min": -2.0,
        "max": 8.0,
        "scale_to": 100
    },
    "OPS+": {
        "min": 50,
        "max": 180,
        "scale_to": 100
    },
    "G": {
        "min": 0,
        "max": 162,
        "scale_to": 10  # Small contribution
    }
}
