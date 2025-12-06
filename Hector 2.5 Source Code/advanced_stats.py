# Advanced Stats Calculator Module
# Ports key formulas from SimBaseballCalc's StatcastHittingTool.js
# Provides expected stats, contact metrics, power metrics, plate discipline,
# and composite scores for player evaluation

from trade_value import parse_number, parse_salary
from player_utils import (
    parse_star_rating, get_age, get_war, normalize_to_100, 
    get_games_played, get_innings_pitched
)

# Minimum sample size thresholds
MIN_PLATE_APPEARANCES_FOR_ADVANCED = 50  # Minimum PA for reliable advanced stats
MIN_INNINGS_FOR_ADVANCED = 20  # Minimum IP for reliable pitcher advanced stats

# Baseline values for normalization
LEAGUE_AVG_BABIP = 0.300
LEAGUE_AVG_ISO = 0.160
LEAGUE_AVG_OBP = 0.320
LEAGUE_AVG_SLG = 0.420
LEAGUE_AVG_WOBA = 0.320
LEAGUE_AVG_ERA = 4.20

# Stat ranges for normalization
STAT_RANGES = {
    "xBA": {"min": 0.180, "max": 0.340},
    "xSLG": {"min": 0.280, "max": 0.600},
    "xWOBA": {"min": 0.250, "max": 0.450},
    "xOPS+": {"min": 60, "max": 180},
    "Contact+": {"min": 50, "max": 150},
    "BIP%": {"min": 50, "max": 90},
    "True_ISO": {"min": 0.050, "max": 0.350},
    "Barrel%": {"min": 0, "max": 20},
    "xHR%": {"min": 0, "max": 8},
    "Chase%": {"min": 10, "max": 50},
    "Plate_Skills": {"min": 0.200, "max": 0.500},
    "Offensive_Rating": {"min": 60, "max": 200},
    "True_wOBA": {"min": 0.250, "max": 0.500},
    "RPE": {"min": 0.5, "max": 2.0},
    "Power_Speed": {"min": 0, "max": 30},
    "Clutch_Index": {"min": 0, "max": 150},
    "Stuff+": {"min": 60, "max": 140},
    "K_BB_Ratio": {"min": 0.5, "max": 5.0},
    "Pitcher_Score": {"min": 0, "max": 100},
}

# Indicator thresholds
BABIP_LUCKY_THRESHOLD = 0.340  # BABIP above this suggests regression
BABIP_UNLUCKY_THRESHOLD = 0.260  # BABIP below this suggests positive regression

# Age thresholds for breakout detection
BREAKOUT_MAX_AGE = 27
BREAKOUT_MIN_UPSIDE_GAP = 5  # POT - OVR gap for breakout candidates (20-80 scale)
BREAKOUT_MIN_UPSIDE_GAP_STAR_SCALE = 0.5  # POT - OVR gap for breakout candidates (star scale)

# Star scale conversion constants
# For ratings on 1-5 star scale, convert to 20-80 equivalent
# 3 stars = 50 (average), 1 star = 30, 5 stars = 70
STAR_SCALE_BASE = 20
STAR_SCALE_MULTIPLIER = 10

# Power/HR rate scaling constants
POWER_TO_HR_RATE_BASE = 30  # Subtract from power rating before scaling
POWER_TO_HR_RATE_DIVISOR = 10  # Divide by this to get expected HR rate
STAR_POWER_TO_HR_DIVISOR = 1.5  # For star scale power to HR rate


def calculate_expected_batting_average(player):
    """
    Calculate expected batting average (xBA).
    Formula: (BABIP * 0.85) + (AVG * 0.15)
    
    Args:
        player: Player dict with batting stats
    
    Returns:
        xBA as float (0.000 to 1.000 scale)
    """
    babip = parse_number(player.get("BABIP", 0))
    avg = parse_number(player.get("AVG", 0))
    
    if babip <= 0 and avg <= 0:
        return 0.0
    
    # If BABIP is 0 but AVG exists, use AVG as proxy
    if babip <= 0:
        babip = avg
    
    xba = (babip * 0.85) + (avg * 0.15)
    return round(xba, 3)


def calculate_expected_slugging(player):
    """
    Calculate expected slugging percentage (xSLG).
    Formula: (SLG * 0.9) + (ISO * 0.1)
    
    Args:
        player: Player dict with batting stats
    
    Returns:
        xSLG as float
    """
    slg = parse_number(player.get("SLG", 0))
    
    # Calculate ISO if not directly available
    iso = calculate_isolated_power(player)
    
    if slg <= 0:
        return 0.0
    
    xslg = (slg * 0.9) + (iso * 0.1)
    return round(xslg, 3)


def calculate_expected_woba(player):
    """
    Calculate expected weighted on-base average (xWOBA).
    Formula: (OBP * 0.6) + (SLG * 0.3) + ((HR / PA) * 0.1)
    
    Args:
        player: Player dict with batting stats
    
    Returns:
        xWOBA as float
    """
    obp = parse_number(player.get("OBP", 0))
    slg = parse_number(player.get("SLG", 0))
    hr = parse_number(player.get("HR", 0))
    pa = parse_number(player.get("PA", 0))
    
    if obp <= 0 and slg <= 0:
        return 0.0
    
    hr_per_pa = (hr / pa) if pa > 0 else 0
    
    xwoba = (obp * 0.6) + (slg * 0.3) + (hr_per_pa * 0.1)
    return round(xwoba, 3)


def calculate_expected_ops_plus(player):
    """
    Calculate expected OPS+ (xOPS+) based on expected stats.
    Uses xOBP and xSLG to project an expected OPS+.
    
    Args:
        player: Player dict with batting stats
    
    Returns:
        xOPS+ as float (100 is league average)
    """
    ops_plus = parse_number(player.get("OPS+", 0))
    xwoba = calculate_expected_woba(player)
    
    if ops_plus <= 0:
        # Estimate from xWOBA if OPS+ not available
        # Scale xWOBA (typically 0.250-0.450) to OPS+ (typically 60-160)
        if xwoba > 0:
            return round(100 + ((xwoba - LEAGUE_AVG_WOBA) * 500), 1)
        return 100.0
    
    # Blend actual OPS+ with expected component
    xops_plus = (ops_plus * 0.7) + ((100 + ((xwoba - LEAGUE_AVG_WOBA) * 500)) * 0.3)
    return round(xops_plus, 1)


def calculate_contact_plus(player):
    """
    Calculate Contact+ rating.
    Formula: ((CONTACT - 50) * 1.5) + ((100 - SO_PCT) * 0.75)
    
    CONTACT is the player's contact rating (CON).
    SO_PCT is strikeout percentage.
    
    Args:
        player: Player dict
    
    Returns:
        Contact+ as float (100 is average)
    """
    contact = parse_number(player.get("CON", 0))
    
    # Calculate strikeout percentage
    so = parse_number(player.get("SO", player.get("K", 0)))
    pa = parse_number(player.get("PA", 0))
    ab = parse_number(player.get("AB", 0))
    
    # Use PA if available, otherwise AB
    denominator = pa if pa > 0 else ab
    so_pct = (so / denominator * 100) if denominator > 0 else 20  # Default 20% K rate
    
    # Normalize contact to 50-based scale
    if contact > 10:
        # On 20-80 scale, use as-is (50 is average)
        contact_normalized = contact
    else:
        # Star scale: convert to 20-80 equivalent
        # 3 stars = 50 (average), 1 star = 30, 5 stars = 70
        contact_normalized = STAR_SCALE_BASE + (contact * STAR_SCALE_MULTIPLIER)
    
    contact_plus = 100 + ((contact_normalized - 50) * 1.5) + ((100 - so_pct) * 0.75)
    return round(max(0, contact_plus), 1)


def calculate_balls_in_play_pct(player):
    """
    Calculate Balls in Play Percentage (BIP%).
    Formula: (AB - SO - HR) / AB * 100
    
    Args:
        player: Player dict
    
    Returns:
        BIP% as float (0-100)
    """
    ab = parse_number(player.get("AB", 0))
    so = parse_number(player.get("SO", player.get("K", 0)))
    hr = parse_number(player.get("HR", 0))
    
    if ab <= 0:
        return 0.0
    
    balls_in_play = ab - so - hr
    bip_pct = (balls_in_play / ab) * 100
    return round(max(0, bip_pct), 1)


def calculate_isolated_power(player):
    """
    Calculate Isolated Power (ISO).
    Formula: SLG - AVG
    
    Args:
        player: Player dict
    
    Returns:
        ISO as float
    """
    slg = parse_number(player.get("SLG", 0))
    avg = parse_number(player.get("AVG", 0))
    
    iso = slg - avg
    return round(max(0, iso), 3)


def calculate_true_iso(player):
    """
    Calculate True ISO with power rating blend.
    Formula: (ISO * 0.8) + (POWER / 100 * 0.2)
    
    Args:
        player: Player dict
    
    Returns:
        True ISO as float
    """
    iso = calculate_isolated_power(player)
    power = parse_number(player.get("POW", 0))
    
    # Normalize power rating
    if power > 10:
        power_normalized = power / 100  # Already on 20-80 scale
    else:
        power_normalized = power / 5  # Star scale (1-5)
    
    true_iso = (iso * 0.8) + (power_normalized * 0.2)
    return round(true_iso, 3)


def calculate_barrel_pct(player):
    """
    Calculate Barrel Percentage.
    Formula: ((HR + (Doubles + Triples) * 0.5) / PA) * 100
    
    Args:
        player: Player dict
    
    Returns:
        Barrel% as float
    """
    hr = parse_number(player.get("HR", 0))
    doubles = parse_number(player.get("2B", 0))
    triples = parse_number(player.get("3B", 0))
    pa = parse_number(player.get("PA", 0))
    
    if pa <= 0:
        return 0.0
    
    barrel_events = hr + (doubles + triples) * 0.5
    barrel_pct = (barrel_events / pa) * 100
    return round(barrel_pct, 2)


def calculate_expected_hr_pct(player):
    """
    Calculate Expected HR Percentage (xHR%).
    Based on power rating and actual HR rate blend.
    
    Args:
        player: Player dict
    
    Returns:
        xHR% as float
    """
    hr = parse_number(player.get("HR", 0))
    pa = parse_number(player.get("PA", 0))
    power = parse_number(player.get("POW", 0))
    
    # Actual HR rate
    hr_pct = (hr / pa * 100) if pa > 0 else 0
    
    # Expected HR rate from power rating
    if power > 10:
        # Scale 20-80 to ~0-5%: (power - 30) / 10
        expected_from_power = (power - POWER_TO_HR_RATE_BASE) / POWER_TO_HR_RATE_DIVISOR
    else:
        # Star scale to percentage
        expected_from_power = power / STAR_POWER_TO_HR_DIVISOR
    
    # Blend actual and expected
    xhr_pct = (hr_pct * 0.7) + (max(0, expected_from_power) * 0.3)
    return round(xhr_pct, 2)


def calculate_chase_pct(player):
    """
    Calculate Chase Rate (estimated).
    Formula: Inverse of (EYE * 0.4) - (SO_PCT * 0.6)
    Lower is better (less chasing).
    
    Args:
        player: Player dict
    
    Returns:
        Chase% as float (0-100, lower is better)
    """
    eye = parse_number(player.get("EYE", 0))
    
    so = parse_number(player.get("SO", player.get("K", 0)))
    pa = parse_number(player.get("PA", 0))
    ab = parse_number(player.get("AB", 0))
    
    denominator = pa if pa > 0 else ab
    so_pct = (so / denominator * 100) if denominator > 0 else 20
    
    # Normalize eye rating
    if eye > 10:
        eye_normalized = eye
    else:
        eye_normalized = eye * 12  # Star scale to 20-80 equivalent
    
    # Calculate chase tendency (inverted - high eye, low K = low chase)
    # Range approximately 10-50%
    chase_raw = 50 - (eye_normalized * 0.4) + (so_pct * 0.6)
    chase_pct = max(10, min(50, chase_raw))
    return round(chase_pct, 1)


def calculate_plate_skills(player):
    """
    Calculate Plate Skills composite.
    Formula: (OBP * 0.4) + (EYE / 100 * 0.3) + ((100 - SO_PCT) / 100 * 0.3)
    
    Args:
        player: Player dict
    
    Returns:
        Plate Skills as float (0-1 scale, like OBP)
    """
    obp = parse_number(player.get("OBP", 0))
    eye = parse_number(player.get("EYE", 0))
    
    so = parse_number(player.get("SO", player.get("K", 0)))
    pa = parse_number(player.get("PA", 0))
    ab = parse_number(player.get("AB", 0))
    
    denominator = pa if pa > 0 else ab
    so_pct = (so / denominator * 100) if denominator > 0 else 20
    
    # Normalize eye
    if eye > 10:
        eye_normalized = eye / 100
    else:
        eye_normalized = eye / 5  # Star scale
    
    plate_skills = (obp * 0.4) + (eye_normalized * 0.3) + ((100 - so_pct) / 100 * 0.3)
    return round(plate_skills, 3)


def calculate_offensive_rating(player):
    """
    Calculate Offensive Rating composite.
    Formula: ((OBP * 0.4) + (SLG * 0.6)) * 100 + (CONTACT - 50) + (POWER - 50) + (EYE - 50)
    
    Args:
        player: Player dict
    
    Returns:
        Offensive Rating as float (typically 60-200)
    """
    obp = parse_number(player.get("OBP", 0))
    slg = parse_number(player.get("SLG", 0))
    contact = parse_number(player.get("CON", 0))
    power = parse_number(player.get("POW", 0))
    eye = parse_number(player.get("EYE", 0))
    
    # Normalize ratings to 50-based scale
    if contact > 10:
        contact_adj = contact - 50
        power_adj = power - 50
        eye_adj = eye - 50
    else:
        # Star scale: 3 stars = neutral (0 adjustment)
        contact_adj = (contact - 3) * 10
        power_adj = (power - 3) * 10
        eye_adj = (eye - 3) * 10
    
    base_rating = ((obp * 0.4) + (slg * 0.6)) * 100
    rating_adjustments = contact_adj + power_adj + eye_adj
    
    offensive_rating = base_rating + rating_adjustments
    return round(offensive_rating, 1)


def calculate_true_woba(player):
    """
    Calculate True wOBA using linear weights.
    Formula: (0.7 * BB + 0.9 * HBP + 0.88 * Singles + 1.25 * Doubles + 1.6 * Triples + 2.1 * HR) / (AB + BB + SF + HBP)
    
    Args:
        player: Player dict
    
    Returns:
        True wOBA as float
    """
    bb = parse_number(player.get("BB", 0))
    hbp = parse_number(player.get("HBP", 0))
    hr = parse_number(player.get("HR", 0))
    doubles = parse_number(player.get("2B", 0))
    triples = parse_number(player.get("3B", 0))
    h = parse_number(player.get("H", 0))
    ab = parse_number(player.get("AB", 0))
    sf = parse_number(player.get("SF", 0))
    
    # Calculate singles
    singles = h - doubles - triples - hr
    singles = max(0, singles)  # Ensure non-negative
    
    # Calculate denominator
    denominator = ab + bb + sf + hbp
    if denominator <= 0:
        return 0.0
    
    # Calculate numerator with linear weights
    numerator = (0.7 * bb) + (0.9 * hbp) + (0.88 * singles) + (1.25 * doubles) + (1.6 * triples) + (2.1 * hr)
    
    true_woba = numerator / denominator
    return round(true_woba, 3)


def calculate_run_production_efficiency(player):
    """
    Calculate Run Production Efficiency (RPE).
    Measures runs produced relative to opportunities.
    Formula: (R + RBI - HR) / (H + BB)
    
    Args:
        player: Player dict
    
    Returns:
        RPE as float (1.0 is average)
    """
    r = parse_number(player.get("R", 0))
    rbi = parse_number(player.get("RBI", 0))
    hr = parse_number(player.get("HR", 0))
    h = parse_number(player.get("H", 0))
    bb = parse_number(player.get("BB", 0))
    
    opportunities = h + bb
    if opportunities <= 0:
        return 0.0
    
    # Subtract HR from runs produced to avoid double-counting
    runs_produced = r + rbi - hr
    rpe = runs_produced / opportunities
    return round(rpe, 2)


def calculate_power_speed_number(player):
    """
    Calculate Power-Speed Number.
    Formula: (2 * HR * SB) / (HR + SB)
    Harmonic mean of HR and SB.
    
    Args:
        player: Player dict
    
    Returns:
        Power-Speed Number as float
    """
    hr = parse_number(player.get("HR", 0))
    sb = parse_number(player.get("SB", 0))
    
    if hr + sb <= 0:
        return 0.0
    
    power_speed = (2 * hr * sb) / (hr + sb)
    return round(power_speed, 1)


def calculate_clutch_index(player):
    """
    Calculate Clutch Index based on RBI efficiency.
    Uses RBI relative to opportunities (runners on base situations).
    Higher is better.
    
    Args:
        player: Player dict
    
    Returns:
        Clutch Index as float (100 is average)
    """
    rbi = parse_number(player.get("RBI", 0))
    h = parse_number(player.get("H", 0))
    hr = parse_number(player.get("HR", 0))
    ab = parse_number(player.get("AB", 0))
    
    if ab <= 0:
        return 100.0
    
    # Expected RBI based on hits and HR
    # Rough approximation: each hit produces ~0.35 RBI, each HR produces ~1.4 RBI
    expected_rbi = (h - hr) * 0.35 + hr * 1.4
    
    if expected_rbi <= 0:
        return 100.0
    
    clutch_index = (rbi / expected_rbi) * 100
    return round(min(200, max(0, clutch_index)), 1)


# ============================================================
# Pitching Metrics
# ============================================================

def calculate_stuff_plus(player):
    """
    Calculate Stuff+ normalization.
    Uses STU (Stuff) rating normalized to 100-scale.
    
    Args:
        player: Player dict
    
    Returns:
        Stuff+ as float (100 is average)
    """
    stu = parse_number(player.get("STU", 0))
    
    if stu <= 0:
        return 100.0
    
    # Normalize STU rating
    if stu > 10:
        # On 20-80 scale, 50 is average
        stuff_plus = 100 + (stu - 50) * 2
    else:
        # Star scale, 3 is average
        stuff_plus = 100 + (stu - 3) * 20
    
    return round(max(60, min(140, stuff_plus)), 1)


def calculate_k_bb_ratio(player):
    """
    Calculate K/BB ratio from K/9 and BB/9.
    
    Args:
        player: Player dict
    
    Returns:
        K/BB ratio as float
    """
    k9 = parse_number(player.get("K/9", 0))
    bb9 = parse_number(player.get("BB/9", 0))
    
    if bb9 <= 0:
        if k9 > 0:
            return 10.0  # Excellent ratio
        return 2.0  # Default average
    
    k_bb = k9 / bb9
    return round(k_bb, 2)


def calculate_expected_era_indicator(player):
    """
    Calculate Expected ERA Indicator based on peripherals.
    Uses FIP, K/9, BB/9, and HR/9 to project expected ERA.
    
    Args:
        player: Player dict
    
    Returns:
        Expected ERA as float
    """
    fip = parse_number(player.get("FIP", 0))
    era = parse_number(player.get("ERA", 0))
    k9 = parse_number(player.get("K/9", 0))
    bb9 = parse_number(player.get("BB/9", 0))
    hr9 = parse_number(player.get("HR/9", 0))
    
    # If FIP is available, weight it heavily
    if fip > 0:
        # Blend FIP and ERA
        expected_era = (fip * 0.6) + (era * 0.4) if era > 0 else fip
    elif era > 0:
        # Adjust ERA based on K-BB differential
        k_bb_adjustment = (k9 - bb9 - 5) * -0.1  # 5 K-BB diff is neutral
        hr_adjustment = (hr9 - 1.0) * 0.3  # 1.0 HR/9 is neutral
        expected_era = era + k_bb_adjustment + hr_adjustment
    else:
        return LEAGUE_AVG_ERA
    
    return round(max(1.0, expected_era), 2)


def calculate_pitcher_composite_score(player):
    """
    Calculate composite pitching score (0-100).
    Combines ratings and stats.
    
    Args:
        player: Player dict
    
    Returns:
        Composite score as float (0-100)
    """
    # Ratings components
    stu = parse_number(player.get("STU", 0))
    mov = parse_number(player.get("MOV", 0))
    con = parse_number(player.get("CON", 0))  # Control
    
    # Stats components
    era_plus = parse_number(player.get("ERA+", 0))
    war = get_war(player, "pitcher")
    k_bb = calculate_k_bb_ratio(player)
    
    # Normalize ratings
    if stu > 10:
        ratings_avg = (stu + mov + con) / 3
        ratings_score = normalize_to_100(ratings_avg, 30, 70)
    else:
        ratings_avg = (stu + mov + con) / 3
        ratings_score = normalize_to_100(ratings_avg, 1, 5) 
    
    # Normalize stats
    era_score = normalize_to_100(era_plus, 80, 150) if era_plus > 0 else 50
    war_score = normalize_to_100(war, -1, 6)
    k_bb_score = normalize_to_100(k_bb, 1.0, 4.0)
    
    # Weighted composite
    composite = (
        ratings_score * 0.35 +
        era_score * 0.25 +
        war_score * 0.25 +
        k_bb_score * 0.15
    )
    
    return round(min(100, max(0, composite)), 1)


# ============================================================
# Player Indicators and Categories
# ============================================================

def get_babip_luck_indicator(player):
    """
    Determine if a player's BABIP suggests luck or regression.
    
    Args:
        player: Player dict
    
    Returns:
        Dict with luck status, color, and description
    """
    babip = parse_number(player.get("BABIP", 0))
    
    if babip <= 0:
        return {"status": "unknown", "color": "#888888", "description": "BABIP not available"}
    
    if babip > BABIP_LUCKY_THRESHOLD:
        return {
            "status": "lucky",
            "color": "#ff6b6b",
            "description": f"High BABIP ({babip:.3f}) - regression likely",
            "regression_direction": "down"
        }
    elif babip < BABIP_UNLUCKY_THRESHOLD:
        return {
            "status": "unlucky",
            "color": "#51cf66",
            "description": f"Low BABIP ({babip:.3f}) - positive regression expected",
            "regression_direction": "up"
        }
    else:
        return {
            "status": "neutral",
            "color": "#ffd43b",
            "description": f"Normal BABIP ({babip:.3f})",
            "regression_direction": "none"
        }


def is_undervalued_player(player, player_type="batter"):
    """
    Determine if a player is undervalued based on advanced stats vs OVR.
    Undervalued = good advanced stats but low OVR rating.
    
    Args:
        player: Player dict
        player_type: "batter" or "pitcher"
    
    Returns:
        Dict with undervalued status and reason
    """
    ovr = parse_star_rating(player.get("OVR", "0"))
    
    # Normalize OVR to 0-100 scale
    if ovr > 10:
        ovr_normalized = normalize_to_100(ovr, 30, 70)
    else:
        ovr_normalized = normalize_to_100(ovr, 1, 5)
    
    if player_type == "batter":
        # Check batting metrics
        wrc_plus = parse_number(player.get("wRC+", 0))
        ops_plus = parse_number(player.get("OPS+", 0))
        xwoba = calculate_expected_woba(player)
        
        # Calculate expected performance level (0-100)
        stat_score = 0
        stat_count = 0
        
        if wrc_plus > 0:
            stat_score += normalize_to_100(wrc_plus, 80, 140)
            stat_count += 1
        if ops_plus > 0:
            stat_score += normalize_to_100(ops_plus, 80, 140)
            stat_count += 1
        if xwoba > 0:
            stat_score += normalize_to_100(xwoba, 0.280, 0.400)
            stat_count += 1
        
        if stat_count > 0:
            avg_stat_score = stat_score / stat_count
        else:
            return {"undervalued": False, "reason": "Insufficient stats"}
        
        # Undervalued if stats suggest 10+ points higher than OVR
        gap = avg_stat_score - ovr_normalized
        if gap >= 10:
            return {
                "undervalued": True,
                "reason": f"Stats suggest {gap:.0f} pts higher value",
                "stat_score": avg_stat_score,
                "ovr_score": ovr_normalized,
                "gap": gap
            }
    else:
        # Pitcher evaluation
        era_plus = parse_number(player.get("ERA+", 0))
        war = get_war(player, "pitcher")
        
        stat_score = 0
        stat_count = 0
        
        if era_plus > 0:
            stat_score += normalize_to_100(era_plus, 80, 140)
            stat_count += 1
        if war != 0:
            stat_score += normalize_to_100(war, -1, 5)
            stat_count += 1
        
        if stat_count > 0:
            avg_stat_score = stat_score / stat_count
        else:
            return {"undervalued": False, "reason": "Insufficient stats"}
        
        gap = avg_stat_score - ovr_normalized
        if gap >= 10:
            return {
                "undervalued": True,
                "reason": f"Stats suggest {gap:.0f} pts higher value",
                "stat_score": avg_stat_score,
                "ovr_score": ovr_normalized,
                "gap": gap
            }
    
    return {"undervalued": False, "reason": "OVR matches performance"}


def is_regression_candidate(player, player_type="batter"):
    """
    Determine if a player is likely to regress.
    Regression candidates have unsustainable peripherals.
    
    Args:
        player: Player dict
        player_type: "batter" or "pitcher"
    
    Returns:
        Dict with regression status, direction, and reasons
    """
    reasons = []
    direction = "neutral"
    
    if player_type == "batter":
        # Check BABIP luck
        babip_luck = get_babip_luck_indicator(player)
        if babip_luck["status"] == "lucky":
            reasons.append(babip_luck["description"])
            direction = "down"
        elif babip_luck["status"] == "unlucky":
            reasons.append(babip_luck["description"])
            direction = "up"
        
        # Check for unsustainable HR rate
        hr = parse_number(player.get("HR", 0))
        pa = parse_number(player.get("PA", 0))
        hr_rate = (hr / pa * 100) if pa > 0 else 0
        
        if hr_rate > 6:  # Very high HR rate
            reasons.append(f"Unsustainable HR rate ({hr_rate:.1f}%)")
            if direction != "up":
                direction = "down"
    else:
        # Pitcher regression indicators
        era = parse_number(player.get("ERA", 0))
        fip = parse_number(player.get("FIP", 0))
        
        if fip > 0 and era > 0:
            era_fip_gap = era - fip
            if era_fip_gap < -1.0:
                reasons.append(f"ERA ({era:.2f}) much lower than FIP ({fip:.2f})")
                direction = "up"  # ERA likely to rise
            elif era_fip_gap > 1.0:
                reasons.append(f"ERA ({era:.2f}) much higher than FIP ({fip:.2f})")
                direction = "down"  # ERA likely to improve
    
    is_regressing = len(reasons) > 0
    return {
        "is_regression_candidate": is_regressing,
        "direction": direction,
        "reasons": reasons,
        "color": "#ff6b6b" if direction == "down" else ("#51cf66" if direction == "up" else "#888888")
    }


def is_breakout_candidate(player, player_type="batter"):
    """
    Determine if a player is a breakout candidate.
    Breakout = strong underlying metrics with room for OVR growth.
    
    Args:
        player: Player dict
        player_type: "batter" or "pitcher"
    
    Returns:
        Dict with breakout status and indicators
    """
    age = get_age(player)
    ovr = parse_star_rating(player.get("OVR", "0"))
    pot = parse_star_rating(player.get("POT", "0"))
    
    # Check age requirement
    if age > BREAKOUT_MAX_AGE:
        return {"is_breakout": False, "reason": "Too old for breakout"}
    
    # Check upside gap
    upside_gap = pot - ovr
    
    # Normalize gap based on scale
    if ovr > 10:
        min_gap = BREAKOUT_MIN_UPSIDE_GAP
    else:
        min_gap = BREAKOUT_MIN_UPSIDE_GAP_STAR_SCALE
    
    if upside_gap < min_gap:
        return {"is_breakout": False, "reason": "Limited upside"}
    
    # Check for strong underlying metrics
    indicators = []
    
    if player_type == "batter":
        xwoba = calculate_expected_woba(player)
        contact_plus = calculate_contact_plus(player)
        barrel_pct = calculate_barrel_pct(player)
        
        if xwoba >= 0.340:
            indicators.append(f"Strong xWOBA ({xwoba:.3f})")
        if contact_plus >= 110:
            indicators.append(f"High Contact+ ({contact_plus:.0f})")
        if barrel_pct >= 8:
            indicators.append(f"Good Barrel% ({barrel_pct:.1f})")
    else:
        stuff_plus = calculate_stuff_plus(player)
        k_bb = calculate_k_bb_ratio(player)
        
        if stuff_plus >= 110:
            indicators.append(f"High Stuff+ ({stuff_plus:.0f})")
        if k_bb >= 3.0:
            indicators.append(f"Excellent K/BB ({k_bb:.2f})")
    
    is_breakout = len(indicators) >= 1 and upside_gap >= min_gap
    
    return {
        "is_breakout": is_breakout,
        "indicators": indicators,
        "upside_gap": upside_gap,
        "age": age,
        "color": "#51cf66" if is_breakout else "#888888"
    }


# ============================================================
# Main Calculation Functions
# ============================================================

def calculate_all_batter_advanced_stats(player):
    """
    Calculate all advanced batting stats for a player.
    
    Args:
        player: Player dict with batting stats
    
    Returns:
        Dict with all calculated advanced stats
    """
    pa = parse_number(player.get("PA", 0))
    has_sample = pa >= MIN_PLATE_APPEARANCES_FOR_ADVANCED
    
    return {
        # Expected stats
        "xBA": calculate_expected_batting_average(player),
        "xSLG": calculate_expected_slugging(player),
        "xWOBA": calculate_expected_woba(player),
        "xOPS+": calculate_expected_ops_plus(player),
        
        # Contact metrics
        "Contact+": calculate_contact_plus(player),
        "BIP%": calculate_balls_in_play_pct(player),
        
        # Power metrics
        "ISO": calculate_isolated_power(player),
        "True_ISO": calculate_true_iso(player),
        "Barrel%": calculate_barrel_pct(player),
        "xHR%": calculate_expected_hr_pct(player),
        
        # Plate discipline
        "Chase%": calculate_chase_pct(player),
        "Plate_Skills": calculate_plate_skills(player),
        
        # Composite scores
        "Offensive_Rating": calculate_offensive_rating(player),
        "True_wOBA": calculate_true_woba(player),
        "RPE": calculate_run_production_efficiency(player),
        "Power_Speed": calculate_power_speed_number(player),
        "Clutch_Index": calculate_clutch_index(player),
        
        # Indicators
        "BABIP_Luck": get_babip_luck_indicator(player),
        "Undervalued": is_undervalued_player(player, "batter"),
        "Regression": is_regression_candidate(player, "batter"),
        "Breakout": is_breakout_candidate(player, "batter"),
        
        # Meta
        "has_sample_size": has_sample,
        "plate_appearances": pa,
    }


def calculate_all_pitcher_advanced_stats(player):
    """
    Calculate all advanced pitching stats for a player.
    
    Args:
        player: Player dict with pitching stats
    
    Returns:
        Dict with all calculated advanced stats
    """
    ip = get_innings_pitched(player)
    has_sample = ip >= MIN_INNINGS_FOR_ADVANCED
    
    return {
        # Core metrics
        "Stuff+": calculate_stuff_plus(player),
        "K/BB": calculate_k_bb_ratio(player),
        "xERA": calculate_expected_era_indicator(player),
        "Pitcher_Score": calculate_pitcher_composite_score(player),
        
        # Indicators
        "Undervalued": is_undervalued_player(player, "pitcher"),
        "Regression": is_regression_candidate(player, "pitcher"),
        "Breakout": is_breakout_candidate(player, "pitcher"),
        
        # Meta
        "has_sample_size": has_sample,
        "innings_pitched": ip,
    }


def add_advanced_stats_to_players(players, player_type="batter"):
    """
    Add advanced stats to a list of players.
    Modifies players in place and returns the same list.
    
    Args:
        players: List of player dicts
        player_type: "batter" or "pitcher"
    
    Returns:
        Same list with advanced_stats added to each player
    """
    for player in players:
        if player_type == "batter":
            player["advanced_stats"] = calculate_all_batter_advanced_stats(player)
        else:
            player["advanced_stats"] = calculate_all_pitcher_advanced_stats(player)
    
    return players


def get_advanced_stats_score(player, player_type="batter"):
    """
    Get a single composite score from advanced stats (0-100).
    Used for integration with roster_builder scoring.
    
    Args:
        player: Player dict with advanced_stats already calculated
        player_type: "batter" or "pitcher"
    
    Returns:
        Composite score as float (0-100)
    """
    advanced = player.get("advanced_stats", {})
    
    if not advanced:
        # Calculate on the fly if not already done
        if player_type == "batter":
            advanced = calculate_all_batter_advanced_stats(player)
        else:
            advanced = calculate_all_pitcher_advanced_stats(player)
    
    if player_type == "batter":
        # Weight key metrics for composite score
        xwoba = advanced.get("xWOBA", 0)
        contact_plus = advanced.get("Contact+", 100)
        offensive_rating = advanced.get("Offensive_Rating", 100)
        
        # Normalize each component to 0-100
        xwoba_score = normalize_to_100(xwoba, 0.250, 0.420)
        contact_score = normalize_to_100(contact_plus, 70, 130)
        rating_score = normalize_to_100(offensive_rating, 80, 160)
        
        composite = (xwoba_score * 0.4) + (contact_score * 0.3) + (rating_score * 0.3)
        return round(min(100, max(0, composite)), 1)
    else:
        return advanced.get("Pitcher_Score", 50.0)
