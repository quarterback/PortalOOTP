import sys
import importlib.util
from pathlib import Path 


def parse_stat_value(val):
    """Parse a stat value from HTML export, handling various formats"""
    if val is None:
        return 0.0
    val = str(val).strip()
    if val == "-" or val == "" or val == " ":
        return 0.0
    # Remove commas from numbers like "1,234"
    val = val.replace(",", "")
    try:
        return float(val)
    except ValueError:
        return 0.0


def calculate_batter_stat_score(player, stat_weights_module):
    """
    Calculate batter score based on actual stats instead of ratings.
    Returns stat-based score and whether stats were used (has sufficient sample size).
    """
    stat_weights = stat_weights_module.stat_weights
    normalization = stat_weights_module.normalization
    min_games = getattr(stat_weights_module, 'MIN_PLATE_APPEARANCES', 50)
    
    # Check sample size - use G (games) as proxy for plate appearances
    games = parse_stat_value(player.get("G", 0))
    has_sufficient_sample = games >= min_games
    
    if not has_sufficient_sample:
        return None, False
    
    stat_score = 0.0
    
    for stat_name, config in stat_weights.items():
        if stat_name == "age_adjustment":
            continue  # Skip meta configuration
            
        weight = config.get("weight", 0)
        if weight == 0:
            continue
            
        raw_value = parse_stat_value(player.get(stat_name, 0))
        
        # Apply scale factor if present
        scale_factor = config.get("scale_factor", 1.0)
        raw_value *= scale_factor
        
        # Normalize if normalization config exists
        if stat_name in normalization:
            norm = normalization[stat_name]
            min_val = norm.get("min", 0)
            max_val = norm.get("max", 100)
            scale_to = norm.get("scale_to", 100)
            
            # Clamp and normalize
            clamped = max(min_val, min(max_val, raw_value))
            normalized = ((clamped - min_val) / (max_val - min_val)) * scale_to
            stat_score += normalized * weight
        else:
            stat_score += raw_value * weight
    
    return round(stat_score, 2), True


def calculate_batter_score(player, section_weights, use_stats=False, stat_weights_module=None):
    pos = player.get('POS', '').upper()
    def to_number(val):
        val = str(val).replace(" Stars", "").strip()
        if val == "-" or val == "":
            return 0.0
        try: return float(val)
        except ValueError: return 0.0
    batter_key_map = {
        'CON': ('overall', 'contact'),
        'GAP': ('overall', 'gap'),
        'POW': ('overall', 'power'),
        'EYE': ('overall', 'eye'),
        "K's": ('overall', 'strikeouts'),
        'CON P': ('potential', 'contact_potential'),
        'GAP P': ('potential', 'gap_potential'),
        'POW P': ('potential', 'power_potential'),
        'EYE P': ('potential', 'eye_potential'),
        'K P': ('potential', 'strikeouts_potential'),
        'C ABI': ('defense', 'catcher', 'catcher_ability'),
        'C ARM': ('defense', 'catcher', 'catcher_arm'),
        'C FRM': ('defense', 'catcher', 'catcher_framing'),
        'IF RNG': ('defense', 'infield', 'infield_range'),
        'IF ERR': ('defense', 'infield', 'infield_error'),
        'IF ARM': ('defense', 'infield', 'infield_arm'),
        'OF RNG': ('defense', 'outfield', 'outfield_range'),
        'OF ERR': ('defense', 'outfield', 'outfield_error'),
        'OF ARM': ('defense', 'outfield', 'outfield_arm'),
        'SPE': ('baserunning', 'speed'),
        'STE': ('baserunning', 'stealing'),
        'RUN': ('baserunning', 'running'),
        'SctAcc': ('scout_accuracy',)
    }
    overall_score = 0.0
    potential_score = 0.0
    defense_score = 0.0
    baserunning_score = 0.0
    scout_accuracy_score = 0.0
    meta = section_weights.get('meta', {})
    meta_overall = meta.get("overall", 1.0)
    meta_potential = meta.get("potential", 1.0)
    meta_defense = meta.get("defense", 1.0)
    meta_baserunning = meta.get("baserunning", 1.0)
    meta_scout = 1.0

    for attr, weight_path in batter_key_map.items():
        val = to_number(player.get(attr, "-"))
        if not val:
            continue
        if weight_path[0] == "overall":
            weight = section_weights['overall'].get(weight_path[1], 0)
            overall_score += val * weight
        elif weight_path[0] == "potential":
            weight = section_weights['potential'].get(weight_path[1], 0)
            potential_score += val * weight
        elif weight_path[0] == "defense":
            if len(weight_path) == 3:
                section = weight_path[1]
                key = weight_path[2]
                # Only score the main defensive section by POS (no double-scoring)
                if pos == "C" and section == "catcher":
                    weight = section_weights['defense']['catcher'].get(key,0)
                    defense_score += val * weight
                elif pos in ['1B', '2B', '3B', 'SS'] and section == "infield":
                    if key in ['infield_range', 'infield_arm']:
                        weight = section_weights['defense']['infield'][key].get(pos,0)
                    else:
                        weight = section_weights['defense']['infield'].get(key,0)
                    defense_score += val * weight
                elif pos in ['LF', 'CF', 'RF'] and section == "outfield":
                    if key == 'outfield_range':
                        weight = section_weights['defense']['outfield'][key].get(pos,0)
                    else:
                        weight = section_weights['defense']['outfield'].get(key,0)
                    defense_score += val * weight

        elif weight_path[0] == "baserunning":
            weight = section_weights['baserunning'].get(weight_path[1], 0)
            baserunning_score += val * weight
        elif weight_path[0] == "scout_accuracy":
            weight = section_weights.get('scout_accuracy', 0)
            scout_accuracy_score += val * weight
    overall_score *= meta_overall
    potential_score *= meta_potential
    defense_score *= meta_defense
    baserunning_score *= meta_baserunning
    scout_accuracy_score *= meta_scout
    total = overall_score + potential_score + defense_score + baserunning_score + scout_accuracy_score
    
    # Calculate stat-based score if enabled and module provided
    stat_score = None
    used_stats = False
    if use_stats and stat_weights_module is not None:
        stat_score, used_stats = calculate_batter_stat_score(player, stat_weights_module)
        if used_stats and stat_score is not None:
            # Use stat score as the total when stats are available
            total = stat_score
    
    return {
        "offense": round(overall_score, 2),
        "offense_potential": round(potential_score, 2),
        "defense": round(defense_score, 2),
        "baserunning": round(baserunning_score, 2),
        "scout_accuracy": round(scout_accuracy_score, 2),
        "total": round(total, 2),
        "stat_score": stat_score,  # None if not calculated or insufficient sample
        "used_stats": used_stats,  # True if stat-based scoring was used
        "overall_stars": player.get('OVR', '0 Stars'),
        "potential_stars": player.get('POT', '0 Stars')
    }
# No file loader needed anymore!


def calculate_park_adjusted_batter_score(player, team_data):
    """
    Calculate park-adjusted batting scores for a player.
    
    For batters in pitcher-friendly parks (PF < 1), their raw stats are suppressed.
    We boost their adjusted score to account for this.
    
    Formula: adjusted_score = raw_score * (1 / park_factor)
    - Lower park factor = higher adjusted score (stats suppressed by park)
    - Higher park factor = lower adjusted score (stats inflated by park)
    
    Args:
        player: Player dict with batting ratings
        team_data: Team dict with park factor data (from teams_by_abbr)
    
    Returns:
        Dict with raw and park-adjusted scores:
        {
            "power_raw": 65,
            "power_adjusted": 72.5,  # Boosted for pitcher park
            "contact_raw": 55,
            "contact_adjusted": 58.0,
            "park_adjustment_bonus": 7.5,  # Total bonus from park adjustment
            "pf_hr": 0.90,  # HR park factor used
            "pf_avg": 0.95,  # AVG park factor used
            "is_hidden_gem": True,  # Flag for extreme pitcher parks
        }
    """
    if not team_data:
        # No team data available, return neutral adjustments
        power_raw = parse_stat_value(player.get("POW", 0))
        contact_raw = parse_stat_value(player.get("CON", 0))
        gap_raw = parse_stat_value(player.get("GAP", 0))
        eye_raw = parse_stat_value(player.get("EYE", 0))
        
        return {
            "power_raw": power_raw,
            "power_adjusted": power_raw,
            "contact_raw": contact_raw,
            "contact_adjusted": contact_raw,
            "gap_raw": gap_raw,
            "gap_adjusted": gap_raw,
            "eye_raw": eye_raw,
            "eye_adjusted": eye_raw,
            "park_adjustment_bonus": 0.0,
            "pf_hr": 1.0,
            "pf_avg": 1.0,
            "is_hidden_gem": False,
        }
    
    # Get park factors
    pf_hr = team_data.get("PF HR", 1.0)
    pf_avg = team_data.get("PF AVG", 1.0)
    pf_overall = team_data.get("PF", 1.0)
    
    # Ensure valid park factors (default to 1.0 if invalid)
    if not isinstance(pf_hr, (int, float)) or pf_hr <= 0:
        pf_hr = 1.0
    if not isinstance(pf_avg, (int, float)) or pf_avg <= 0:
        pf_avg = 1.0
    if not isinstance(pf_overall, (int, float)) or pf_overall <= 0:
        pf_overall = 1.0
    
    # Get raw batting ratings
    power_raw = parse_stat_value(player.get("POW", 0))
    contact_raw = parse_stat_value(player.get("CON", 0))
    gap_raw = parse_stat_value(player.get("GAP", 0))
    eye_raw = parse_stat_value(player.get("EYE", 0))
    
    # Calculate adjusted scores using inverse of park factor
    # Lower park factor = higher adjusted score for batters
    power_adjusted = power_raw * (1 / pf_hr) if pf_hr > 0 else power_raw
    contact_adjusted = contact_raw * (1 / pf_avg) if pf_avg > 0 else contact_raw
    gap_adjusted = gap_raw * (1 / pf_avg) if pf_avg > 0 else gap_raw
    eye_adjusted = eye_raw  # Eye is not park-affected
    
    # Calculate total park adjustment bonus (sum of improvements)
    power_bonus = power_adjusted - power_raw
    contact_bonus = contact_adjusted - contact_raw
    gap_bonus = gap_adjusted - gap_raw
    park_adjustment_bonus = power_bonus + contact_bonus + gap_bonus
    
    # Determine if this is a hidden gem (extreme pitcher park suppressing stats)
    # Hidden gem criteria: PF < 0.95 or PF HR < 0.90, with good raw power/contact
    is_hidden_gem = (
        (pf_overall < 0.95 or pf_hr < 0.90) and
        (power_raw >= 50 or contact_raw >= 55)
    )
    
    return {
        "power_raw": round(power_raw, 1),
        "power_adjusted": round(power_adjusted, 1),
        "contact_raw": round(contact_raw, 1),
        "contact_adjusted": round(contact_adjusted, 1),
        "gap_raw": round(gap_raw, 1),
        "gap_adjusted": round(gap_adjusted, 1),
        "eye_raw": round(eye_raw, 1),
        "eye_adjusted": round(eye_adjusted, 1),
        "park_adjustment_bonus": round(park_adjustment_bonus, 1),
        "pf_hr": pf_hr,
        "pf_avg": pf_avg,
        "is_hidden_gem": is_hidden_gem,
    }


def get_park_impact_preview(player, current_team_data, new_team_data):
    """
    Preview the impact of a player moving to a new park.
    
    Shows projected stat changes when a batter moves between parks.
    Example: "Player X: +5 HR projection in new park (Oracle → Citizens Bank)"
    
    Args:
        player: Player dict with batting ratings
        current_team_data: Current team's park factor data
        new_team_data: New team's park factor data
    
    Returns:
        Dict with projected changes:
        {
            "hr_change": +5,
            "avg_change": +0.015,
            "description": "+5 HR projection, +.015 AVG",
            "impact_level": "significant"  # minimal, moderate, significant
        }
    """
    # Get current and new park factors
    current_pf_hr = current_team_data.get("PF HR", 1.0) if current_team_data else 1.0
    current_pf_avg = current_team_data.get("PF AVG", 1.0) if current_team_data else 1.0
    new_pf_hr = new_team_data.get("PF HR", 1.0) if new_team_data else 1.0
    new_pf_avg = new_team_data.get("PF AVG", 1.0) if new_team_data else 1.0
    
    # Ensure valid park factors
    if not isinstance(current_pf_hr, (int, float)) or current_pf_hr <= 0:
        current_pf_hr = 1.0
    if not isinstance(new_pf_hr, (int, float)) or new_pf_hr <= 0:
        new_pf_hr = 1.0
    if not isinstance(current_pf_avg, (int, float)) or current_pf_avg <= 0:
        current_pf_avg = 1.0
    if not isinstance(new_pf_avg, (int, float)) or new_pf_avg <= 0:
        new_pf_avg = 1.0
    
    # Calculate relative park factor change
    # If moving from PF HR 0.90 to PF HR 1.10, the ratio is 1.10/0.90 = 1.22
    hr_ratio = new_pf_hr / current_pf_hr if current_pf_hr > 0 else 1.0
    avg_ratio = new_pf_avg / current_pf_avg if current_pf_avg > 0 else 1.0
    
    # Get player's raw power rating to estimate HR impact
    power_raw = parse_stat_value(player.get("POW", 0))
    
    # Estimate HR change based on power and park factor change
    # This is a simplified model: higher power = more sensitive to park factors
    # Base HR expectation: power/3 (so 60 power ≈ 20 HR baseline)
    base_hr_estimate = power_raw / 3
    projected_hr_change = base_hr_estimate * (hr_ratio - 1)
    
    # Estimate AVG change
    # AVG is less volatile, estimate based on contact rating
    avg_change = (avg_ratio - 1) * 0.030  # Max ~.030 swing
    
    # Determine impact level
    if abs(projected_hr_change) >= 5 or abs(avg_change) >= 0.015:
        impact_level = "significant"
    elif abs(projected_hr_change) >= 2 or abs(avg_change) >= 0.008:
        impact_level = "moderate"
    else:
        impact_level = "minimal"
    
    # Build description
    parts = []
    if abs(projected_hr_change) >= 1:
        sign = "+" if projected_hr_change > 0 else ""
        parts.append(f"{sign}{projected_hr_change:.0f} HR")
    if abs(avg_change) >= 0.005:
        sign = "+" if avg_change > 0 else ""
        parts.append(f"{sign}{avg_change:.3f} AVG")
    
    description = ", ".join(parts) if parts else "Minimal park impact"
    
    return {
        "hr_change": round(projected_hr_change, 1),
        "avg_change": round(avg_change, 3),
        "description": description,
        "impact_level": impact_level,
        "current_pf_hr": current_pf_hr,
        "new_pf_hr": new_pf_hr,
        "current_pf_avg": current_pf_avg,
        "new_pf_avg": new_pf_avg,
    }
