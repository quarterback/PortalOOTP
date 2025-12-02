# Philosophy Profiles for Roster Building
# Configurable weight distributions for different team-building approaches

"""
Philosophy profiles define how players are evaluated when auto-generating rosters.
Each profile has weights for different evaluation axes and optional constraints.

Weight axes:
- current_stats: wRC+, WAR, OPS+ for batters; ERA+, FIP, WAR for pitchers
- current_ratings: OVR rating normalized to 0-100
- potential: POT rating and upside gap (POT - OVR)
- value_efficiency: WAR/$ ratio
- age_curve: Score based on age relative to philosophy preferences
- positional_scarcity: Bonus for premium positions (C, SS, CF for batters; SP for pitchers)
"""

# Weight validation tolerance (weights should sum to ~1.0 within this tolerance)
WEIGHT_TOLERANCE = 0.01

# Default weight values for balanced evaluation
DEFAULT_WEIGHTS = {
    "current_stats": 0.25,
    "current_ratings": 0.25,
    "potential": 0.20,
    "value_efficiency": 0.15,
    "age_curve": 0.10,
    "positional_scarcity": 0.05,
}

# Philosophy profile definitions
PHILOSOPHY_PROFILES = {
    "win_now": {
        "name": "Win Now",
        "description": "Maximize current production, ignore cost/future",
        "weights": {
            "current_stats": 0.45,
            "current_ratings": 0.30,
            "potential": 0.05,
            "value_efficiency": 0.05,
            "age_curve": 0.10,
            "positional_scarcity": 0.05,
        },
        "constraints": {
            "max_age": 35,
        },
        "age_preferences": {
            "ideal_min": 26,
            "ideal_max": 30,
            "acceptable_min": 24,
            "acceptable_max": 33,
        },
    },
    "sabermetric_value": {
        "name": "Sabermetric Value",
        "description": "Maximize WAR/$ and advanced metrics",
        "weights": {
            "current_stats": 0.40,
            "current_ratings": 0.15,
            "potential": 0.15,
            "value_efficiency": 0.25,
            "age_curve": 0.05,
            "positional_scarcity": 0.00,
        },
        "constraints": {},
        "age_preferences": {
            "ideal_min": 24,
            "ideal_max": 30,
            "acceptable_min": 22,
            "acceptable_max": 34,
        },
    },
    "long_term_upside": {
        "name": "Long-Term Upside",
        "description": "Build for 3-5 years out, prioritize potential",
        "weights": {
            "current_stats": 0.15,
            "current_ratings": 0.15,
            "potential": 0.40,
            "value_efficiency": 0.15,
            "age_curve": 0.15,
            "positional_scarcity": 0.00,
        },
        "constraints": {
            "max_age": 27,
            "prefer_pre_arb": True,
        },
        "age_preferences": {
            "ideal_min": 20,
            "ideal_max": 24,
            "acceptable_min": 18,
            "acceptable_max": 27,
        },
    },
    "balanced": {
        "name": "Balanced",
        "description": "Mix of win-now and future, avoid extremes",
        "weights": {
            "current_stats": 0.25,
            "current_ratings": 0.25,
            "potential": 0.20,
            "value_efficiency": 0.15,
            "age_curve": 0.10,
            "positional_scarcity": 0.05,
        },
        "constraints": {},
        "age_preferences": {
            "ideal_min": 25,
            "ideal_max": 29,
            "acceptable_min": 22,
            "acceptable_max": 33,
        },
    },
    "budget_conscious": {
        "name": "Budget Conscious",
        "description": "Maximize value per dollar, cheap contracts",
        "weights": {
            "current_stats": 0.20,
            "current_ratings": 0.15,
            "potential": 0.15,
            "value_efficiency": 0.40,
            "age_curve": 0.05,
            "positional_scarcity": 0.05,
        },
        "constraints": {
            "max_salary_per_player": 15.0,
            "prefer_pre_arb": True,
        },
        "age_preferences": {
            "ideal_min": 23,
            "ideal_max": 27,
            "acceptable_min": 21,
            "acceptable_max": 30,
        },
    },
    "stars_and_scrubs": {
        "name": "Stars and Scrubs",
        "description": "Elite talent at key positions, minimum spend elsewhere",
        "weights": {
            "current_stats": 0.35,
            "current_ratings": 0.35,
            "potential": 0.10,
            "value_efficiency": 0.10,
            "age_curve": 0.05,
            "positional_scarcity": 0.05,
        },
        "constraints": {},
        "age_preferences": {
            "ideal_min": 26,
            "ideal_max": 31,
            "acceptable_min": 24,
            "acceptable_max": 34,
        },
    },
}

# Premium positions that receive scarcity bonuses
PREMIUM_BATTER_POSITIONS = {"C", "SS", "CF"}
PREMIUM_PITCHER_POSITIONS = {"SP"}

# Position scarcity multipliers (used for scoring)
POSITION_SCARCITY_SCORES = {
    # Batters
    "C": 1.15,
    "SS": 1.12,
    "CF": 1.10,
    "2B": 1.05,
    "3B": 1.03,
    "RF": 1.00,
    "LF": 0.98,
    "1B": 0.95,
    "DH": 0.90,
    # Pitchers
    "SP": 1.10,
    "RP": 0.95,
    "CL": 1.00,
}

# Age curve parameters for different philosophies
# Prime years are when players typically perform best
PRIME_YEARS_MIN = 26
PRIME_YEARS_MAX = 30


def get_philosophy_profile(name):
    """
    Retrieve a philosophy profile by name with fallback to balanced.
    
    Args:
        name: Philosophy profile name (string) or custom weights dict
    
    Returns:
        Philosophy profile dict with weights and constraints
    """
    if isinstance(name, dict):
        # Custom weights dict provided - validate and merge with defaults
        profile = {
            "name": "Custom",
            "description": "Custom philosophy profile",
            "weights": DEFAULT_WEIGHTS.copy(),
            "constraints": {},
            "age_preferences": {
                "ideal_min": 25,
                "ideal_max": 29,
                "acceptable_min": 22,
                "acceptable_max": 33,
            },
        }
        # Override with provided weights
        if "weights" in name:
            profile["weights"].update(name["weights"])
        if "constraints" in name:
            profile["constraints"].update(name["constraints"])
        if "age_preferences" in name:
            profile["age_preferences"].update(name["age_preferences"])
        return profile
    
    # Look up by name
    if name in PHILOSOPHY_PROFILES:
        return PHILOSOPHY_PROFILES[name]
    
    # Try case-insensitive lookup
    name_lower = str(name).lower().replace(" ", "_").replace("-", "_")
    for key, profile in PHILOSOPHY_PROFILES.items():
        if key.lower() == name_lower:
            return profile
    
    # Fallback to balanced
    return PHILOSOPHY_PROFILES["balanced"]


def get_position_scarcity_score(position):
    """
    Get the scarcity score multiplier for a position.
    
    Args:
        position: Position string (C, 1B, 2B, SS, SP, RP, etc.)
    
    Returns:
        Scarcity multiplier (float)
    """
    return POSITION_SCARCITY_SCORES.get(position, 1.0)


def is_premium_position(position, player_type="batter"):
    """
    Check if a position is considered premium.
    
    Args:
        position: Position string
        player_type: "batter" or "pitcher"
    
    Returns:
        Boolean indicating if position is premium
    """
    if player_type == "pitcher":
        return position in PREMIUM_PITCHER_POSITIONS
    return position in PREMIUM_BATTER_POSITIONS


def validate_weights(weights):
    """
    Validate that weight values sum to approximately 1.0.
    
    Args:
        weights: Dict of weight name -> weight value
    
    Returns:
        Tuple of (is_valid, normalized_weights)
    """
    total = sum(weights.values())
    if total == 0:
        return False, weights
    
    # Allow for small floating point differences
    is_valid = abs(total - 1.0) < WEIGHT_TOLERANCE
    
    # Normalize if needed
    if not is_valid:
        normalized = {k: v / total for k, v in weights.items()}
        return True, normalized
    
    return True, weights


def list_philosophy_profiles():
    """
    Get a list of all available philosophy profiles.
    
    Returns:
        List of dicts with profile info (key, name, description)
    """
    profiles = []
    for key, profile in PHILOSOPHY_PROFILES.items():
        profiles.append({
            "key": key,
            "name": profile["name"],
            "description": profile["description"],
        })
    return profiles
