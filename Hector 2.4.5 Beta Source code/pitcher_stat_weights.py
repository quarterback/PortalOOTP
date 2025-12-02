# Pitcher Stats Weights Configuration
# These weights are used when "Use Stats-Based Scoring" is enabled
# Stats are from the HTML export and are used to calculate player value
# based on actual performance rather than ratings

# Minimum sample size requirements
# Players with less than this threshold will use ratings-only scoring
MIN_INNINGS_PITCHED = 20  # Minimum IP for pitchers

stat_weights = {
    # High Priority - Primary value metrics
    "WAR (Pitcher)": {
        "weight": 0.30,
        "description": "Wins Above Replacement - overall value",
        "baseline": 0,
        "higher_is_better": True
    },
    "ERA+": {
        "weight": 0.30,
        "description": "ERA Plus - park-adjusted ERA (100 is average, higher is better)",
        "baseline": 100,
        "higher_is_better": True
    },
    
    # Medium Priority - Peripheral metrics
    "rWAR": {
        "weight": 0.15,
        "description": "Replacement-level WAR",
        "baseline": 0,
        "higher_is_better": True
    },
    
    # Context - Reliever specific
    "HLD": {
        "weight": 0.05,
        "description": "Holds - reliever value indicator",
        "baseline": 0,
        "higher_is_better": True,
        "applies_to": ["RP", "CL"]  # Only for relievers
    },
    
    # Volume indicator
    "IP": {
        "weight": 0.05,
        "description": "Innings Pitched - workload indicator",
        "baseline": 0,
        "higher_is_better": True,
        "scale_factor": 0.01  # Scale down contribution
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
    "WAR (Pitcher)": {
        "min": -2.0,
        "max": 8.0,
        "scale_to": 100
    },
    "ERA+": {
        "min": 50,   # Very poor
        "max": 200,  # Elite
        "scale_to": 100
    },
    "rWAR": {
        "min": -2.0,
        "max": 6.0,
        "scale_to": 50
    },
    "HLD": {
        "min": 0,
        "max": 30,
        "scale_to": 20
    },
    "IP": {
        "min": 0,
        "max": 220,  # Full season starter
        "scale_to": 10
    }
}
