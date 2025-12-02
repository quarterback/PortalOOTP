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


def calculate_pitcher_stat_score(player, stat_weights_module):
    """
    Calculate pitcher score based on actual stats instead of ratings.
    Returns stat-based score and whether stats were used (has sufficient sample size).
    """
    stat_weights = stat_weights_module.stat_weights
    normalization = stat_weights_module.normalization
    min_ip = getattr(stat_weights_module, 'MIN_INNINGS_PITCHED', 20)
    
    # Check sample size - use IP (innings pitched)
    ip = parse_stat_value(player.get("IP", 0))
    has_sufficient_sample = ip >= min_ip
    
    if not has_sufficient_sample:
        return None, False
    
    stat_score = 0.0
    pos = player.get("POS", "").upper()
    
    for stat_name, config in stat_weights.items():
        if stat_name == "age_adjustment":
            continue  # Skip meta configuration
            
        weight = config.get("weight", 0)
        if weight == 0:
            continue
        
        # Check if this stat applies only to certain positions
        applies_to = config.get("applies_to", None)
        if applies_to is not None and pos not in applies_to:
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


def calculate_score(player, section_weights, use_stats=False, stat_weights_module=None):
    total_core = 0
    total_core_potential = 0
    total_pitch_arsenal = 0
    total_pitch_potential = 0
    total_other = 0
    penalties = 0
    pitch_key_map_actual = {
        "FB": "Fastball", "CH": "Changeup", "CB": "Curveball", "SL": "Slider", "SI": "Sinker",
        "SP": "Splitter", "CT": "Cutter", "FO": "Forkball", "CC": "Circle Change",
        "SC": "Screwball", "KC": "Knuckle Curve", "KN": "Knuckleball"
    }
    pitch_key_map_potential = {
        "FBP": "Fastball Potential", "CHP": "Changeup Potential", "CBP": "Curveball Potential",
        "SLP": "Slider Potential", "SIP": "Sinker Potential", "SPP": "Splitter Potential",
        "CTP": "Cutter Potential", "FOP": "Forkball Potential", "CCP": "Circle Change Potential",
        "SCP": "Screwball Potential", "KCP": "Knuckle Curve Potential", "KNP": "Knuckleball Potential"
    }

    def parse_value(raw_value):
        raw_value = str(raw_value).strip()
        if "Stars" in raw_value:
            try: return float(raw_value.split()[0])
            except Exception: return 0
        elif "-" in raw_value and raw_value != "-" and not raw_value.startswith("-"):
            parts = [p.strip() for p in raw_value.replace("mph", "").split("-")]
            nums = []
            for p in parts:
                try: nums.append(float(p))
                except Exception: pass
            return sum(nums) / len(nums) if nums else 0
        elif raw_value == "-" or raw_value == "":
            return 0
        else:
            import re
            match = re.search(r"\d+(\.\d+)?", raw_value)
            if match:
                return float(match.group(0))
            else:
                return 0

    meta = section_weights.get("meta", {})
    meta_core = meta.get("core_attributes", 1.0)
    meta_core_potential = meta.get("core_potentials", 1.0)
    meta_pitch = meta.get("pitch_arsenal", 1.0)
    meta_pitch_potential = meta.get("pitch_arsenal_potential", 1.0)
    meta_other = meta.get("other_attributes", 1.0)
    meta_penalties = meta.get("penalties", 1.0)

    pitch_values = []
    for header, value in player.items():
        val = parse_value(value)
        if header in pitch_key_map_actual:
            key = pitch_key_map_actual[header]
            weight = section_weights["pitch_arsenal"].get(key, 0)
            total_pitch_arsenal += val * weight * meta_pitch
            if val > 0:
                pitch_values.append(val)
        elif header in pitch_key_map_potential:
            key = pitch_key_map_potential[header]
            weight_key = key.lower().replace(" ", "_")
            weight = section_weights["pitch_arsenal_potential"].get(weight_key, 0)
            total_pitch_potential += val * weight * meta_pitch_potential
        else:
            header_to_weight = {
                'STU': 'stuff', 'MOV': 'movement', 'CON': 'control',
                'STU P': 'stuff_potential', 'MOV P': 'movement_potential', 'CON P': 'control_potential',
                'PIT': 'number_of_pitches', 'VELO': 'velocity', 'STM': 'stamina',
                'G/F': 'ground_fly_ratio', 'HLD': 'holds', 'SctAcc': 'scout_accuracy'
            }

            weight_key = header_to_weight.get(header)
            if weight_key:
                if weight_key in ["stuff", "movement", "control", "overall_rating"]:
                    weight = section_weights["core_attributes"].get(weight_key, 0)
                    total_core += val * weight * meta_core
                elif weight_key in ["stuff_potential", "movement_potential", "control_potential", "potential_rating"]:
                    weight_key_norm = weight_key.lower().replace(" ", "_")
                    weight = section_weights["core_potentials"].get(weight_key_norm, 0)
                    total_core_potential += val * weight * meta_core_potential
                else:
                    weight = section_weights["other_attributes"].get(weight_key, 0)
                    total_other += val * weight * meta_other
        pos = player.get("POS", "").upper()
    try:
        if pos == "SP":
            if int(player.get("PIT", 0)) < 4:
                penalties += section_weights["penalties"].get("penalty_sp_low_pitches", 0)
            if int(player.get("STM", 0)) < 50:
                penalties += section_weights["penalties"].get("penalty_sp_low_stamina", 0)
            control_potential = parse_value(player.get("CON P", 0))
            if control_potential < 50:
                penalties += section_weights["penalties"].get("penalty_sp_low_control_potential", 0)
    except Exception:
        pass


    if pitch_values and max(pitch_values) < 50:
        penalties += section_weights["penalties"].get("no_pitch_50_plus", 0)
    total_other += penalties * meta_penalties
    total_potential = total_pitch_potential + total_core_potential
    total_score = total_core + total_potential + total_pitch_arsenal + total_other
    
    # Calculate stat-based score if enabled and module provided
    stat_score = None
    used_stats = False
    if use_stats and stat_weights_module is not None:
        stat_score, used_stats = calculate_pitcher_stat_score(player, stat_weights_module)
        if used_stats and stat_score is not None:
            # Use stat score as the total when stats are available
            total_score = stat_score
    
    return {
        'total': round(total_score, 2),
        'pitches': round(total_pitch_arsenal, 2),
        'pitches_potential': round(total_pitch_potential, 2),
        'core_potential': round(total_core_potential, 2),
        'curr_total': round(total_core + total_pitch_arsenal + total_other, 2),
        'stat_score': stat_score,  # None if not calculated or insufficient sample
        'used_stats': used_stats   # True if stat-based scoring was used
    }
# No file loader needed!
