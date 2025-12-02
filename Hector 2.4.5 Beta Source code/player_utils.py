# Shared utility functions for player analytics
# Common functions used across percentiles, hidden_gems, archetypes, and roster_builder

from trade_value import parse_number


# Rating scale detection threshold
# Values <= this threshold are considered star scale (1-5 or 1-10)
# Values > this threshold are considered 20-80 scale
RATING_SCALE_THRESHOLD = 10

# Star to 20-80 scale conversion factor
# Star ratings (1-5 scale) are converted to approximately 20-80 scale
# by multiplying by 16 (so 5 stars ≈ 80, 1 star ≈ 16)
STAR_TO_RATING_SCALE = 16


def parse_star_rating(val):
    """
    Convert star rating or numeric value to float.
    
    Handles formats:
    - "3.5 Stars" -> 3.5
    - "3.5" -> 3.5
    - "65" -> 65.0
    - "12.5%" -> 12.5 (percentage values)
    - None, "", "-" -> 0.0
    """
    if not val:
        return 0.0
    val = str(val).strip()
    if "Stars" in val:
        try:
            return float(val.split()[0])
        except (ValueError, IndexError):
            return 0.0
    # Handle percentage values like "12.5%"
    if "%" in val:
        try:
            return float(val.replace("%", ""))
        except ValueError:
            return 0.0
    try:
        return float(val)
    except ValueError:
        return 0.0


def get_age(player):
    """
    Get player age as integer.
    
    Returns 0 if age cannot be parsed.
    """
    try:
        return int(player.get("Age", 0))
    except (ValueError, TypeError):
        return 0


def get_war(player, player_type="batter"):
    """
    Get WAR value for a player.
    
    Args:
        player: Player dict
        player_type: "batter" or "pitcher"
    
    Returns WAR as float, 0.0 if not available.
    """
    if player_type == "pitcher":
        return parse_number(player.get("WAR (Pitcher)", player.get("WAR", 0)))
    return parse_number(player.get("WAR (Batter)", player.get("WAR", 0)))


def normalize_rating(ovr):
    """
    Normalize OVR rating to 20-80 scale.
    
    If the value is <= RATING_SCALE_THRESHOLD, it's assumed to be a star rating 
    (1-5 or 1-10 scale) and is converted to approximately 20-80 scale.
    
    Args:
        ovr: OVR value (star scale or 20-80 scale)
    
    Returns:
        Rating normalized to 20-80 scale
    """
    if is_star_scale(ovr):
        return ovr * STAR_TO_RATING_SCALE
    return ovr


def is_star_scale(val):
    """
    Determine if a rating value is on star scale (1-5 or 1-10) vs 20-80 scale.
    
    Values <= RATING_SCALE_THRESHOLD are considered star scale.
    """
    return val <= RATING_SCALE_THRESHOLD
