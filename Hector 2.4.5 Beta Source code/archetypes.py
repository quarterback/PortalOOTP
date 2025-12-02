# Franchise Archetypes
# Filter and find players that fit desired team-building philosophies

from trade_value import parse_number, parse_salary, parse_years_left


def parse_star_rating(val):
    """Convert star rating or numeric value to float"""
    if not val:
        return 0.0
    val = str(val).strip()
    if "Stars" in val:
        try:
            return float(val.split()[0])
        except (ValueError, IndexError):
            return 0.0
    try:
        return float(val)
    except ValueError:
        return 0.0


def get_age(player):
    """Get player age as integer"""
    try:
        return int(player.get("Age", 0))
    except (ValueError, TypeError):
        return 0


def get_war(player, player_type="batter"):
    """Get WAR value for a player"""
    if player_type == "pitcher":
        return parse_number(player.get("WAR (Pitcher)", player.get("WAR", 0)))
    return parse_number(player.get("WAR (Batter)", player.get("WAR", 0)))


# Archetype Definitions
ARCHETYPES = {
    "speed_defense": {
        "icon": "🏃",
        "name": "Speed & Defense",
        "description": "High speed, elite defense, contact-oriented",
        "color": "#4dabf7",
        "player_types": ["batter"],
    },
    "mashers": {
        "icon": "💪",
        "name": "Mashers",
        "description": "High power, high ISO, accept higher K%",
        "color": "#ff6b6b",
        "player_types": ["batter"],
    },
    "moneyball": {
        "icon": "👁️",
        "name": "Moneyball (OBP Focus)",
        "description": "High eye, high BB%, value OBP over AVG",
        "color": "#51cf66",
        "player_types": ["batter"],
    },
    "youth_movement": {
        "icon": "🌱",
        "name": "Youth Movement",
        "description": "Age ≤25, high potential, cheap contracts",
        "color": "#9775fa",
        "player_types": ["batter", "pitcher"],
    },
    "win_now": {
        "icon": "🏆",
        "name": "Win Now",
        "description": "High OVR, proven production, prime years",
        "color": "#ffd43b",
        "player_types": ["batter", "pitcher"],
    },
    "budget_build": {
        "icon": "💰",
        "name": "Budget Build",
        "description": "High WAR/$, cheap contracts, good value",
        "color": "#ff922b",
        "player_types": ["batter", "pitcher"],
    },
    "balanced": {
        "icon": "⚖️",
        "name": "Balanced",
        "description": "No glaring weaknesses, all ratings ≥45",
        "color": "#ced4da",
        "player_types": ["batter", "pitcher"],
    },
}


# Fit score thresholds
FIT_THRESHOLDS = {
    "perfect": {"min": 80, "max": 100, "label": "Perfect Fit", "color": "#51cf66"},
    "good": {"min": 60, "max": 79, "label": "Good Fit", "color": "#4dabf7"},
    "partial": {"min": 40, "max": 59, "label": "Partial Fit", "color": "#ffd43b"},
    "poor": {"min": 0, "max": 39, "label": "Not a Fit", "color": "#ff6b6b"},
}


def get_fit_label(score):
    """Get the fit label for a given score"""
    for key, threshold in FIT_THRESHOLDS.items():
        if threshold["min"] <= score <= threshold["max"]:
            return {
                "key": key,
                "label": threshold["label"],
                "color": threshold["color"],
            }
    return {"key": "poor", "label": "Not a Fit", "color": "#ff6b6b"}


def calculate_speed_defense_fit(player):
    """
    Speed & Defense archetype:
    - Target: High SPE (≥60), high STE (≥60), elite DEF
    - Batting: Prioritize CON over POW
    - Accept: Lower power, contact-oriented
    - Positions: Premium up the middle (C, 2B, SS, CF)
    """
    score = 0
    max_score = 100
    
    pos = player.get("POS", "")
    premium_positions = {"C", "2B", "SS", "CF"}
    
    # Speed (25 points)
    spe = parse_number(player.get("SPE", 0))
    if spe >= 70:
        score += 25
    elif spe >= 60:
        score += 20
    elif spe >= 50:
        score += 10
    
    # Stealing (15 points)
    ste = parse_number(player.get("STE", 0))
    if ste >= 70:
        score += 15
    elif ste >= 60:
        score += 12
    elif ste >= 50:
        score += 6
    
    # Defense (30 points) - check position-appropriate ratings
    if pos == "C":
        c_abi = parse_number(player.get("C ABI", 0))
        c_arm = parse_number(player.get("C ARM", 0))
        def_avg = (c_abi + c_arm) / 2
    elif pos in {"2B", "SS", "3B", "1B"}:
        if_rng = parse_number(player.get("IF RNG", 0))
        if_arm = parse_number(player.get("IF ARM", 0))
        if_err = parse_number(player.get("IF ERR", 0))
        def_avg = (if_rng + if_arm + if_err) / 3
    else:
        of_rng = parse_number(player.get("OF RNG", 0))
        of_arm = parse_number(player.get("OF ARM", 0))
        of_err = parse_number(player.get("OF ERR", 0))
        def_avg = (of_rng + of_arm + of_err) / 3
    
    if def_avg >= 65:
        score += 30
    elif def_avg >= 55:
        score += 22
    elif def_avg >= 45:
        score += 12
    
    # Contact over power (15 points)
    con = parse_number(player.get("CON", 0))
    pow_ = parse_number(player.get("POW", 0))
    if con >= 55 and con > pow_:
        score += 15
    elif con >= 50:
        score += 10
    
    # Position bonus (15 points)
    if pos in premium_positions:
        score += 15
    elif pos in {"3B", "LF", "RF"}:
        score += 5
    
    return min(score, max_score)


def calculate_mashers_fit(player):
    """
    Mashers archetype:
    - Target: High POW (≥60), high ISO (≥.180)
    - Accept: Higher K%, lower AVG
    - Positions: Corner bats (1B, 3B, LF, RF, DH)
    - Bonus: HR totals, SLG
    """
    score = 0
    max_score = 100
    
    pos = player.get("POS", "")
    corner_positions = {"1B", "3B", "LF", "RF", "DH"}
    
    # Power (35 points)
    pow_ = parse_number(player.get("POW", 0))
    if pow_ >= 70:
        score += 35
    elif pow_ >= 60:
        score += 28
    elif pow_ >= 50:
        score += 15
    
    # ISO (20 points)
    iso = parse_number(player.get("ISO", 0))
    if iso >= 0.250:
        score += 20
    elif iso >= 0.200:
        score += 16
    elif iso >= 0.180:
        score += 12
    elif iso >= 0.150:
        score += 6
    
    # SLG (15 points)
    slg = parse_number(player.get("SLG", 0))
    if slg >= 0.550:
        score += 15
    elif slg >= 0.500:
        score += 12
    elif slg >= 0.450:
        score += 8
    
    # Position bonus (15 points)
    if pos in corner_positions:
        score += 15
    elif pos in {"C", "2B"}:
        score += 8  # Some bonus for power at non-premium positions
    
    # Gap power (15 points)
    gap = parse_number(player.get("GAP", 0))
    if gap >= 60:
        score += 15
    elif gap >= 50:
        score += 10
    
    return min(score, max_score)


def calculate_moneyball_fit(player):
    """
    Moneyball (OBP Focus) archetype:
    - Target: High EYE (≥55), high BB% (≥10%), wOBA ≥.340
    - Value: OBP over AVG
    - Accept: Less speed, less power
    - Key stats: OBP, wOBA, BB%
    """
    score = 0
    max_score = 100
    
    # Eye (25 points)
    eye = parse_number(player.get("EYE", 0))
    if eye >= 70:
        score += 25
    elif eye >= 60:
        score += 20
    elif eye >= 55:
        score += 15
    elif eye >= 50:
        score += 8
    
    # BB% (25 points)
    bb_pct = parse_number(player.get("BB%", 0))
    if bb_pct >= 15:
        score += 25
    elif bb_pct >= 12:
        score += 20
    elif bb_pct >= 10:
        score += 15
    elif bb_pct >= 8:
        score += 8
    
    # OBP (25 points)
    obp = parse_number(player.get("OBP", 0))
    if obp >= 0.400:
        score += 25
    elif obp >= 0.370:
        score += 20
    elif obp >= 0.350:
        score += 15
    elif obp >= 0.330:
        score += 10
    
    # wOBA (25 points)
    woba = parse_number(player.get("wOBA", 0))
    if woba >= 0.400:
        score += 25
    elif woba >= 0.370:
        score += 20
    elif woba >= 0.340:
        score += 15
    elif woba >= 0.320:
        score += 10
    
    return min(score, max_score)


def calculate_youth_movement_fit(player, player_type="batter"):
    """
    Youth Movement archetype:
    - Target: Age ≤25
    - High POT (≥60 or 3.5+ stars)
    - POT > OVR by ≥10 (or 1.0+ stars)
    - Cheap contracts (pre-arb, arb)
    - Accept: Lower current production
    """
    score = 0
    max_score = 100
    
    age = get_age(player)
    
    # Age (30 points)
    if age <= 22:
        score += 30
    elif age <= 24:
        score += 25
    elif age <= 25:
        score += 20
    elif age <= 26:
        score += 10
    else:
        return 0  # Not a fit for youth movement
    
    # Potential (30 points)
    pot = parse_star_rating(player.get("POT", "0"))
    ovr = parse_star_rating(player.get("OVR", "0"))
    
    if pot > 10:  # 20-80 scale
        if pot >= 70:
            score += 30
        elif pot >= 60:
            score += 24
        elif pot >= 55:
            score += 18
        elif pot >= 50:
            score += 10
    else:  # Star scale
        if pot >= 4.5:
            score += 30
        elif pot >= 4.0:
            score += 24
        elif pot >= 3.5:
            score += 18
        elif pot >= 3.0:
            score += 10
    
    # Upside gap (25 points)
    gap = pot - ovr
    if pot > 10:  # 20-80 scale
        if gap >= 15:
            score += 25
        elif gap >= 10:
            score += 20
        elif gap >= 5:
            score += 12
    else:  # Star scale
        if gap >= 1.5:
            score += 25
        elif gap >= 1.0:
            score += 20
        elif gap >= 0.5:
            score += 12
    
    # Contract (15 points)
    yl_data = parse_years_left(player.get("YL", ""))
    status = yl_data.get("status", "unknown")
    
    if status == "pre_arb":
        score += 15
    elif status == "arbitration":
        score += 12
    else:
        salary = parse_salary(player.get("SLR", 0))
        if salary < 3:
            score += 8
    
    return min(score, max_score)


def calculate_win_now_fit(player, player_type="batter"):
    """
    Win Now archetype:
    - Target: High OVR (≥65 or 4.0+ stars)
    - High current stats (wRC+ ≥120, WAR ≥3)
    - Age 26-32 (prime years)
    - Ignore: Contract cost, future value
    """
    score = 0
    max_score = 100
    
    age = get_age(player)
    
    # Age - prime years (20 points)
    if 26 <= age <= 30:
        score += 20
    elif 24 <= age <= 32:
        score += 15
    elif age <= 33:
        score += 10
    elif age <= 35:
        score += 5
    
    # OVR (35 points)
    ovr = parse_star_rating(player.get("OVR", "0"))
    if ovr > 10:  # 20-80 scale
        if ovr >= 75:
            score += 35
        elif ovr >= 70:
            score += 30
        elif ovr >= 65:
            score += 25
        elif ovr >= 60:
            score += 15
    else:  # Star scale
        if ovr >= 4.5:
            score += 35
        elif ovr >= 4.0:
            score += 30
        elif ovr >= 3.5:
            score += 25
        elif ovr >= 3.0:
            score += 15
    
    # Current production (45 points)
    if player_type == "batter":
        wrc_plus = parse_number(player.get("wRC+", 0))
        war = parse_number(player.get("WAR (Batter)", player.get("WAR", 0)))
        
        if wrc_plus >= 140:
            score += 25
        elif wrc_plus >= 120:
            score += 20
        elif wrc_plus >= 110:
            score += 12
        elif wrc_plus >= 100:
            score += 6
        
        if war >= 5:
            score += 20
        elif war >= 4:
            score += 16
        elif war >= 3:
            score += 12
        elif war >= 2:
            score += 6
    else:
        era_plus = parse_number(player.get("ERA+", 0))
        war = parse_number(player.get("WAR (Pitcher)", player.get("WAR", 0)))
        
        if era_plus >= 140:
            score += 25
        elif era_plus >= 120:
            score += 20
        elif era_plus >= 110:
            score += 12
        elif era_plus >= 100:
            score += 6
        
        if war >= 4:
            score += 20
        elif war >= 3:
            score += 16
        elif war >= 2:
            score += 12
        elif war >= 1:
            score += 6
    
    return min(score, max_score)


def calculate_budget_build_fit(player, player_type="batter"):
    """
    Budget Build archetype:
    - Target: High WAR/$ ratio
    - Pre-arb or arbitration players
    - AAV < $5M with WAR ≥1.5
    - Expiring deals with production
    """
    score = 0
    max_score = 100
    
    # Get WAR and salary
    war = get_war(player, player_type)
    salary = parse_salary(player.get("SLR", 0))
    
    # WAR/$ ratio (40 points)
    if salary > 0:
        war_per_dollar = war / salary
        if war_per_dollar >= 2.0:
            score += 40
        elif war_per_dollar >= 1.5:
            score += 32
        elif war_per_dollar >= 1.0:
            score += 24
        elif war_per_dollar >= 0.5:
            score += 12
    elif war >= 1.0:
        score += 40  # Free production!
    
    # Contract status (25 points)
    yl_data = parse_years_left(player.get("YL", ""))
    status = yl_data.get("status", "unknown")
    
    if status == "pre_arb":
        score += 25
    elif status == "arbitration":
        score += 20
    else:
        years_left = yl_data.get("years", 99)
        if years_left <= 1:
            score += 15  # Expiring deal
        elif years_left <= 2:
            score += 10
    
    # Low AAV (20 points)
    if salary < 1:
        score += 20
    elif salary < 3:
        score += 16
    elif salary < 5:
        score += 12
    elif salary < 8:
        score += 6
    
    # Minimum production (15 points)
    if war >= 3:
        score += 15
    elif war >= 2:
        score += 12
    elif war >= 1.5:
        score += 9
    elif war >= 1.0:
        score += 5
    
    return min(score, max_score)


def calculate_balanced_fit(player, player_type="batter"):
    """
    Balanced archetype:
    - No glaring weaknesses
    - All ratings ≥45
    - Mix of skills
    - Average or better at everything
    """
    score = 0
    max_score = 100
    
    if player_type == "batter":
        ratings = {
            "CON": parse_number(player.get("CON", 0)),
            "GAP": parse_number(player.get("GAP", 0)),
            "POW": parse_number(player.get("POW", 0)),
            "EYE": parse_number(player.get("EYE", 0)),
            "SPE": parse_number(player.get("SPE", 0)),
        }
        
        # Count ratings at various thresholds
        above_45 = sum(1 for v in ratings.values() if v >= 45)
        above_50 = sum(1 for v in ratings.values() if v >= 50)
        above_55 = sum(1 for v in ratings.values() if v >= 55)
        
        # No weaknesses bonus (40 points)
        min_rating = min(ratings.values()) if ratings else 0
        if min_rating >= 50:
            score += 40
        elif min_rating >= 45:
            score += 30
        elif min_rating >= 40:
            score += 15
        
        # All-around ratings (40 points)
        if above_55 >= 4:
            score += 40
        elif above_50 >= 4:
            score += 32
        elif above_50 >= 3:
            score += 20
        elif above_45 >= 4:
            score += 12
        
        # Average rating bonus (20 points)
        avg_rating = sum(ratings.values()) / len(ratings) if ratings else 0
        if avg_rating >= 55:
            score += 20
        elif avg_rating >= 50:
            score += 15
        elif avg_rating >= 45:
            score += 10
    
    else:  # pitcher
        ratings = {
            "STU": parse_number(player.get("STU", 0)),
            "MOV": parse_number(player.get("MOV", 0)),
            "CON": parse_number(player.get("CON", 0)),
        }
        
        above_45 = sum(1 for v in ratings.values() if v >= 45)
        above_50 = sum(1 for v in ratings.values() if v >= 50)
        above_55 = sum(1 for v in ratings.values() if v >= 55)
        
        min_rating = min(ratings.values()) if ratings else 0
        if min_rating >= 50:
            score += 45
        elif min_rating >= 45:
            score += 35
        elif min_rating >= 40:
            score += 20
        
        if above_55 == 3:
            score += 40
        elif above_50 == 3:
            score += 32
        elif above_50 >= 2:
            score += 20
        elif above_45 == 3:
            score += 12
        
        avg_rating = sum(ratings.values()) / len(ratings) if ratings else 0
        if avg_rating >= 55:
            score += 15
        elif avg_rating >= 50:
            score += 10
        elif avg_rating >= 45:
            score += 5
    
    return min(score, max_score)


def calculate_archetype_fit(player, archetype, player_type="batter"):
    """Calculate fit score for a player against an archetype"""
    archetype_funcs = {
        "speed_defense": lambda p: calculate_speed_defense_fit(p) if player_type == "batter" else 0,
        "mashers": lambda p: calculate_mashers_fit(p) if player_type == "batter" else 0,
        "moneyball": lambda p: calculate_moneyball_fit(p) if player_type == "batter" else 0,
        "youth_movement": lambda p: calculate_youth_movement_fit(p, player_type),
        "win_now": lambda p: calculate_win_now_fit(p, player_type),
        "budget_build": lambda p: calculate_budget_build_fit(p, player_type),
        "balanced": lambda p: calculate_balanced_fit(p, player_type),
    }
    
    func = archetype_funcs.get(archetype)
    if func:
        return func(player)
    return 0


def find_players_by_archetype(players, archetype, player_type="batter", min_fit=40):
    """
    Find all players that fit a given archetype.
    Returns list of (player, fit_score, fit_label) sorted by fit score.
    """
    results = []
    
    # Check if archetype supports this player type
    archetype_info = ARCHETYPES.get(archetype, {})
    supported_types = archetype_info.get("player_types", [])
    
    if player_type not in supported_types:
        return results
    
    for player in players:
        fit_score = calculate_archetype_fit(player, archetype, player_type)
        
        if fit_score >= min_fit:
            fit_label = get_fit_label(fit_score)
            results.append({
                "player": player,
                "fit_score": fit_score,
                "fit_label": fit_label,
                "name": player.get("Name", ""),
                "team": player.get("ORG", ""),
                "pos": player.get("POS", ""),
                "age": get_age(player),
                "ovr": parse_star_rating(player.get("OVR", "0")),
                "pot": parse_star_rating(player.get("POT", "0")),
            })
    
    # Sort by fit score descending
    results.sort(key=lambda x: x["fit_score"], reverse=True)
    return results


def get_player_archetype_fits(player, player_type="batter"):
    """
    Get all archetype fits for a single player.
    Returns dict of archetype -> fit_score
    """
    results = {}
    for archetype, info in ARCHETYPES.items():
        if player_type in info.get("player_types", []):
            fit_score = calculate_archetype_fit(player, archetype, player_type)
            results[archetype] = {
                "score": fit_score,
                "label": get_fit_label(fit_score),
                "archetype_name": info["name"],
                "archetype_icon": info["icon"],
            }
    return results


def get_best_archetype(player, player_type="batter"):
    """Get the best-fitting archetype for a player"""
    fits = get_player_archetype_fits(player, player_type)
    if not fits:
        return None
    
    best = max(fits.items(), key=lambda x: x[1]["score"])
    return {
        "archetype": best[0],
        "score": best[1]["score"],
        "name": best[1]["archetype_name"],
        "icon": best[1]["archetype_icon"],
        "label": best[1]["label"],
    }
