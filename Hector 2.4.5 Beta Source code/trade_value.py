# Trade Value Calculator
# Calculates a composite Trade Value score (1-100) for every player

import re

# Position scarcity multipliers - scarce positions are more valuable
POSITION_SCARCITY = {
    "C": 1.15,
    "SS": 1.12,
    "CF": 1.10,
    "SP": 1.08,
    "2B": 1.05,
    "3B": 1.05,
    "RP": 0.95,
    "CL": 0.95,  # Treat CL same as RP
    "LF": 0.95,
    "RF": 0.95,
    "1B": 0.90,
    "DH": 0.85,
}

# Age multipliers for future value calculation
AGE_MULTIPLIERS = {
    "23_or_younger": 1.3,
    "24_25": 1.15,
    "26_27": 1.0,
    "28_29": 0.85,
    "30_32": 0.6,
    "33_plus": 0.4,
}

# Contract status multipliers for trade value calculation
CONTRACT_STATUS_MULTIPLIERS = {
    "pre_arb": 1.25,      # Pre-arbitration (auto.) - cheap team control = premium
    "arbitration": 1.10,  # Arbitration eligible - still controlled, costs rising
    "signed": 1.0,        # Signed deal (no status) - known cost
    "expiring": 0.85,     # Expiring (YL=1, no extension) - rental value only
}

# Trade Value Tiers
TRADE_VALUE_TIERS = {
    "Elite": {"min": 80, "max": 100, "icon": "💎", "description": "Franchise cornerstones, untouchable"},
    "Star": {"min": 65, "max": 79, "icon": "⭐", "description": "High-end starters, cost a lot to acquire"},
    "Solid": {"min": 50, "max": 64, "icon": "✅", "description": "Quality regulars, good trade chips"},
    "Average": {"min": 35, "max": 49, "icon": "📊", "description": "Role players, depth pieces"},
    "Below Average": {"min": 20, "max": 34, "icon": "📉", "description": "Marginal value, throw-ins"},
    "Minimal": {"min": 1, "max": 19, "icon": "❌", "description": "Replacement level or worse"},
}

# Enhanced Contract Categories
CONTRACT_CATEGORIES = {
    "surplus": {"icon": "💰", "color": "#51cf66", "description": "High WAR, low AAV, pre-arb or arb"},
    "fair_value": {"icon": "✅", "color": "#ffd43b", "description": "AAV within normal range for production"},
    "albatross": {"icon": "🚨", "color": "#ff6b6b", "description": "High AAV, low WAR, many years left"},
    "arb_target": {"icon": "🎯", "color": "#4dabf7", "description": "Arbitration status, good stats, affordable"},
    "extension_committed": {"icon": "📋", "color": "#9775fa", "description": "Has extension contract value > 0"},
}

# Extension grade thresholds
EXTENSION_GRADES = {
    "steal": {"icon": "💎", "color": "#51cf66", "description": "Extension AAV well below market"},
    "fair": {"icon": "✅", "color": "#ffd43b", "description": "Extension AAV appropriate for production"},
    "risky": {"icon": "⚠️", "color": "#ff922b", "description": "Extension AAV high, age/injury concerns"},
    "overpay": {"icon": "🚨", "color": "#ff6b6b", "description": "Extension AAV exceeds projected value"},
}

# League average $/WAR (used for surplus value calculation)
LEAGUE_AVG_DOLLAR_PER_WAR = 8.0  # In millions, typical MLB value


def parse_number(value):
    """Parse numeric value, handling '-' and empty strings"""
    if not value or value == "-" or value == "":
        return 0.0
    try:
        val = str(value).replace(",", "").strip()
        # Handle star ratings
        if "Stars" in val:
            return float(val.split()[0])
        return float(val)
    except (ValueError, AttributeError):
        return 0.0


def parse_salary(value):
    """
    Parse salary/dollar amount from OOTP format.
    Handles formats like: $850,000, $9,000,000, $133,550,000
    Returns value in millions (e.g., $9,000,000 -> 9.0)
    """
    if not value or value == "-" or value == "":
        return 0.0
    try:
        val = str(value).strip()
        # Remove dollar sign and commas
        val = val.replace("$", "").replace(",", "")
        # Convert to millions
        return float(val) / 1_000_000
    except (ValueError, AttributeError):
        return 0.0


def parse_years_left(value):
    """
    Parse YL (Years Left) field which may contain status indicators.
    Examples:
        "1 (auto.)" -> {"years": 1, "status": "pre_arb"}
        "1 (arbitr.)" -> {"years": 1, "status": "arbitration"}
        "7" -> {"years": 7, "status": "signed"}
        "5" -> {"years": 5, "status": "signed"}
    
    Returns dict with years (int) and status (str)
    """
    if not value or value == "-" or value == "":
        return {"years": 0, "status": "unknown"}
    
    val = str(value).strip()
    
    # Check for status indicators
    if "(auto.)" in val:
        # Pre-arbitration, automatic renewal
        years_match = re.match(r"(\d+)", val)
        years = int(years_match.group(1)) if years_match else 1
        return {"years": years, "status": "pre_arb"}
    elif "(arbitr.)" in val:
        # Arbitration eligible
        years_match = re.match(r"(\d+)", val)
        years = int(years_match.group(1)) if years_match else 1
        return {"years": years, "status": "arbitration"}
    else:
        # Just a number, no status - signed deal
        try:
            years = int(float(val))
            return {"years": years, "status": "signed"}
        except (ValueError, TypeError):
            return {"years": 0, "status": "unknown"}


def get_contract_status(player):
    """
    Determine the contract status category for a player.
    
    Categories:
    - Pre-Arb: (auto.) in YL - cheap, team-controlled
    - Arbitration: (arbitr.) in YL - costs rising, but still controlled
    - Free Agent Soon: YL = 1 (no status, no extension) - expiring, trade candidate
    - Locked Up: TY >= 4 - long-term deal
    
    Returns tuple (status_name, status_key, color)
    """
    yl_data = parse_years_left(player.get("YL", ""))
    ty = parse_number(player.get("TY", 0))
    ecv = parse_salary(player.get("ECV", 0))
    
    status = yl_data.get("status", "unknown")
    years = yl_data.get("years", 0)
    
    if status == "pre_arb":
        return ("Pre-Arb", "pre_arb", "#51cf66")  # Green
    elif status == "arbitration":
        return ("Arbitration", "arbitration", "#4dabf7")  # Blue
    elif years == 1 and ecv <= 0 and status == "signed":
        return ("FA Soon", "expiring", "#ff922b")  # Orange
    elif ty >= 4:
        return ("Locked Up", "signed", "#9775fa")  # Purple
    else:
        return ("Signed", "signed", "#d4d4d4")  # Gray


def calculate_aav(player):
    """
    Calculate Average Annual Value (AAV) from contract data.
    Formula: CV / TY (total contract value / total years)
    
    Returns AAV in millions, or 0 if data unavailable
    """
    cv = parse_salary(player.get("CV", 0))
    ty = parse_number(player.get("TY", 0))
    
    # Fallback to SLR if CV not available
    if cv <= 0:
        cv = parse_salary(player.get("SLR", 0))
        ty = 1  # If using current salary, assume 1 year
    
    if ty <= 0:
        return cv  # Return current salary if no years
    
    return cv / ty


def calculate_total_commitment(player):
    """
    Calculate total contract burden including extension.
    
    Returns dict with:
    - total_value: CV + ECV (total dollars committed)
    - total_years: TY + ETY (total years of commitment)
    - overall_aav: (CV + ECV) / (TY + ETY)
    """
    cv = parse_salary(player.get("CV", 0))
    ty = parse_number(player.get("TY", 0))
    ecv = parse_salary(player.get("ECV", 0))
    ety = parse_number(player.get("ETY", 0))
    
    # Fallback to SLR if CV not available
    if cv <= 0:
        cv = parse_salary(player.get("SLR", 0))
        ty = 1
    
    total_value = cv + ecv
    total_years = ty + ety
    
    if total_years <= 0:
        overall_aav = total_value
    else:
        overall_aav = total_value / total_years
    
    return {
        "total_value": total_value,
        "total_years": total_years,
        "overall_aav": overall_aav,
        "has_extension": ecv > 0
    }


def get_extension_analysis(player, player_type="batter"):
    """
    Analyze a player's extension if they have one.
    
    Returns dict with:
    - has_extension: bool
    - extension_aav: ECV / ETY
    - extension_grade: Steal/Fair/Risky/Overpay
    - red_flags: list of concerns
    """
    ecv = parse_salary(player.get("ECV", 0))
    ety = parse_number(player.get("ETY", 0))
    
    if ecv <= 0 or ety <= 0:
        return {"has_extension": False}
    
    extension_aav = ecv / ety
    
    # Get player attributes for grading
    if player_type == "pitcher":
        war = parse_number(player.get("WAR (Pitcher)", player.get("WAR", 0)))
    else:
        war = parse_number(player.get("WAR (Batter)", player.get("WAR", 0)))
    
    try:
        age = int(player.get("Age", 0))
    except (ValueError, TypeError):
        age = 0
    
    ovr = parse_number(player.get("OVR", 0))
    prone = str(player.get("Prone", "")).lower()
    
    # Calculate expected AAV based on WAR (rough estimate)
    # Use league average $/WAR as baseline
    expected_aav = war * LEAGUE_AVG_DOLLAR_PER_WAR
    if expected_aav <= 0:
        expected_aav = 5.0  # Minimum expected for a major league player
    
    # Grade the extension
    aav_ratio = extension_aav / expected_aav if expected_aav > 0 else 999
    
    red_flags = []
    
    # Check for red flags
    if age >= 30 and ety >= 5:
        red_flags.append(f"Age {age} + {ety} year extension")
    if "fragile" in prone or "prone" in prone:
        red_flags.append("Durability concerns")
    if ovr <= 10:  # Assuming star rating
        if ovr <= 3.0 and ety >= 4:
            red_flags.append("Low OVR with long extension")
    
    # Determine grade
    if aav_ratio <= 0.7:
        grade = "steal"
    elif aav_ratio <= 1.1:
        grade = "fair"
    elif len(red_flags) > 0 or aav_ratio <= 1.5:
        grade = "risky"
    else:
        grade = "overpay"
    
    grade_info = EXTENSION_GRADES[grade]
    
    # Calculate total commitment
    commitment = calculate_total_commitment(player)
    
    return {
        "has_extension": True,
        "extension_value": ecv,
        "extension_years": ety,
        "extension_aav": extension_aav,
        "grade": grade,
        "grade_icon": grade_info["icon"],
        "grade_color": grade_info["color"],
        "grade_description": grade_info["description"],
        "red_flags": red_flags,
        "total_commitment": commitment["total_value"],
        "total_years": commitment["total_years"],
        "overall_aav": commitment["overall_aav"]
    }


def get_age_multiplier(age):
    """Get age multiplier for future value calculation"""
    try:
        age = int(age)
    except (ValueError, TypeError):
        return 0.5  # Default for invalid age
    
    if age <= 23:
        return AGE_MULTIPLIERS["23_or_younger"]
    elif age <= 25:
        return AGE_MULTIPLIERS["24_25"]
    elif age <= 27:
        return AGE_MULTIPLIERS["26_27"]
    elif age <= 29:
        return AGE_MULTIPLIERS["28_29"]
    elif age <= 32:
        return AGE_MULTIPLIERS["30_32"]
    else:
        return AGE_MULTIPLIERS["33_plus"]


def get_position_scarcity(position):
    """Get position scarcity multiplier"""
    pos = str(position).upper()
    return POSITION_SCARCITY.get(pos, 1.0)


def get_trade_value_tier(trade_value):
    """Get the tier information for a given trade value score"""
    for tier_name, tier_info in TRADE_VALUE_TIERS.items():
        if tier_info["min"] <= trade_value <= tier_info["max"]:
            return {
                "name": tier_name,
                "icon": tier_info["icon"],
                "description": tier_info["description"]
            }
    return {"name": "Unknown", "icon": "?", "description": "Unknown tier"}


def calculate_current_production_score(player, player_type="batter"):
    """
    Calculate current production score (0-40 points) based on stat score or WAR
    40% weight in final trade value
    """
    # Get WAR based on player type
    if player_type == "pitcher":
        war = parse_number(player.get("WAR (Pitcher)", player.get("WAR", 0)))
    else:
        war = parse_number(player.get("WAR (Batter)", player.get("WAR", 0)))
    
    # Try to use the existing score system if available
    scores = player.get("Scores", {})
    total_score = scores.get("total", 0)
    
    # Normalize WAR to 0-40 scale
    # WAR range: -2 to 8 for elite players
    war_normalized = max(0, min(40, ((war + 2) / 10) * 40))
    
    # Also consider the calculated score (normalized to 0-40)
    # Typical scores range from 0-200, normalize to 0-40
    score_normalized = min(40, (total_score / 200) * 40)
    
    # Use the average of both for a more balanced view
    return round((war_normalized + score_normalized) / 2, 2)


def calculate_future_value_score(player):
    """
    Calculate future value score (0-30 points) based on POT and age
    30% weight in final trade value
    """
    pot = parse_number(player.get("POT", 0))
    age = player.get("Age", 30)
    
    age_multiplier = get_age_multiplier(age)
    
    # POT is typically on 1-5 star scale or 0-80 scale
    # Normalize to 0-30 scale
    if pot <= 10:  # Likely star rating (1-5 or 1-10)
        pot_normalized = (pot / 10) * 30
    else:  # Likely 0-80 scale
        pot_normalized = (pot / 80) * 30
    
    future_value = pot_normalized * age_multiplier
    return round(min(30, max(0, future_value)), 2)


def calculate_contract_value_score(player):
    """
    Calculate enhanced contract value score (0-25 points) based on:
    - Years of control (using TY for total years)
    - Contract status (Pre-Arb/Arb/Signed/Expiring)
    - AAV (Average Annual Value)
    - Extension impact
    
    25% weight in final trade value (updated from 20%)
    More years of control at low cost = more value
    """
    # Parse contract data with new columns
    yl_data = parse_years_left(player.get("YL", ""))
    years_left = yl_data.get("years", 0)
    status = yl_data.get("status", "unknown")
    
    # Use TY (Total Years) if available, otherwise fall back to YL
    ty = parse_number(player.get("TY", 0))
    if ty <= 0:
        ty = years_left
    
    # Calculate AAV
    aav = calculate_aav(player)
    
    # Check for extension
    ecv = parse_salary(player.get("ECV", 0))
    ety = parse_number(player.get("ETY", 0))
    has_extension = ecv > 0 and ety > 0
    
    # Years of control contribution (0-10 points)
    # More years = more value, capped at 6 years
    # Pre-arb years worth more than arb years
    if status == "pre_arb":
        years_score = min(10, years_left * 2.0)  # Pre-arb years are premium
    elif status == "arbitration":
        years_score = min(10, years_left * 1.8)  # Arb years still valuable
    else:
        years_score = min(10, years_left * 1.67)  # Signed years normal value
    
    # Contract status multiplier contribution (0-5 points)
    status_multiplier = CONTRACT_STATUS_MULTIPLIERS.get(status, 1.0)
    status_score = (status_multiplier - 0.85) / (1.25 - 0.85) * 5  # Scale to 0-5
    
    # AAV efficiency contribution (0-8 points)
    # Lower AAV = more value
    if aav <= 0:
        aav_score = 8  # No salary = max value
    elif aav < 1:
        aav_score = 8
    elif aav < 5:
        aav_score = 6
    elif aav < 10:
        aav_score = 4
    elif aav < 20:
        aav_score = 2
    elif aav < 25:
        aav_score = 1
    else:
        aav_score = 0  # Very high AAV = slight penalty
    
    # Extension impact (0-2 points bonus or penalty)
    extension_score = 0
    if has_extension:
        extension_aav = ecv / ety if ety > 0 else 0
        # Team-friendly extension = bonus, overpay = penalty
        if extension_aav < 10:
            extension_score = 2  # Good extension
        elif extension_aav < 20:
            extension_score = 0  # Neutral
        else:
            extension_score = -2  # Expensive extension (harder to trade)
    
    total_score = years_score + status_score + aav_score + extension_score
    return round(max(0, min(25, total_score)), 2)


def calculate_position_scarcity_score(player):
    """
    Calculate position scarcity score (0-10 points)
    10% weight in final trade value
    """
    pos = player.get("POS", "")
    scarcity_mult = get_position_scarcity(pos)
    
    # Base score of 5, modified by scarcity
    # Range: 0.85x to 1.15x gives range of ~4.25 to 5.75, then scaled
    base_score = 5 * scarcity_mult
    
    # Scale to 0-10 range
    # Min would be 4.25 (DH), max would be 5.75 (C)
    # Rescale to 0-10
    scaled = ((base_score - 4.25) / (5.75 - 4.25)) * 10
    return round(max(0, min(10, scaled)), 2)


def calculate_trade_value(player, player_type="batter"):
    """
    Calculate composite Trade Value score (1-100) for a player
    
    Updated Components with enhanced contract analysis:
    - Current Production: 35% weight (0-35 points)
    - Future Value: 30% weight (0-30 points)  
    - Contract Value: 25% weight (0-25 points) - enhanced with status multipliers
    - Position Scarcity: 10% weight (0-10 points)
    
    Returns dict with trade value and component breakdown
    """
    current_prod = calculate_current_production_score(player, player_type)
    # Scale current production to 0-35 (from 0-40)
    current_prod = round(current_prod * 0.875, 2)
    
    future_value = calculate_future_value_score(player)
    contract_value = calculate_contract_value_score(player)  # Now returns 0-25
    position_scarcity = calculate_position_scarcity_score(player)
    
    # Apply contract status multiplier to base value
    yl_data = parse_years_left(player.get("YL", ""))
    status = yl_data.get("status", "unknown")
    status_multiplier = CONTRACT_STATUS_MULTIPLIERS.get(status, 1.0)
    
    # Total trade value (scaled 1-100)
    raw_total = current_prod + future_value + contract_value + position_scarcity
    
    # Apply status multiplier to the total (capped effect)
    adjusted_total = raw_total * min(1.1, max(0.9, (status_multiplier - 1) * 0.5 + 1))
    trade_value = max(1, min(100, round(adjusted_total)))
    
    tier = get_trade_value_tier(trade_value)
    
    # Get additional contract info
    aav = calculate_aav(player)
    contract_status = get_contract_status(player)
    commitment = calculate_total_commitment(player)
    extension = get_extension_analysis(player, player_type)
    
    return {
        "trade_value": trade_value,
        "current_production": current_prod,
        "future_value": future_value,
        "contract_value": contract_value,
        "position_scarcity": position_scarcity,
        "tier": tier["name"],
        "tier_icon": tier["icon"],
        "tier_description": tier["description"],
        # Enhanced contract info
        "aav": aav,
        "contract_status": contract_status[0],
        "contract_status_key": contract_status[1],
        "contract_status_color": contract_status[2],
        "total_commitment": commitment["total_value"],
        "total_years": commitment["total_years"],
        "has_extension": extension.get("has_extension", False),
        "extension_aav": extension.get("extension_aav", 0),
        "extension_grade": extension.get("grade", ""),
        "extension_grade_icon": extension.get("grade_icon", ""),
    }


def calculate_dollars_per_war(player, player_type="batter"):
    """
    Calculate $/WAR (dollars per WAR)
    Lower is better
    
    Returns tuple (dollars_per_war, display_string)
    """
    if player_type == "pitcher":
        war = parse_number(player.get("WAR (Pitcher)", player.get("WAR", 0)))
    else:
        war = parse_number(player.get("WAR (Batter)", player.get("WAR", 0)))
    
    salary = parse_number(player.get("SLR", 0))
    
    if war <= 0:
        return float('inf'), "∞" if salary > 0 else "N/A"
    
    dollars_per_war = salary / war
    return dollars_per_war, f"${dollars_per_war:.1f}M"


def calculate_surplus_value(player, player_type="batter"):
    """
    Calculate surplus value: (WAR * league_avg_$/WAR) - salary
    Positive = surplus value (good deal)
    Negative = overpay
    
    Returns tuple (surplus_value, display_string)
    """
    if player_type == "pitcher":
        war = parse_number(player.get("WAR (Pitcher)", player.get("WAR", 0)))
    else:
        war = parse_number(player.get("WAR (Batter)", player.get("WAR", 0)))
    
    salary = parse_number(player.get("SLR", 0))
    
    expected_value = war * LEAGUE_AVG_DOLLAR_PER_WAR
    surplus = expected_value - salary
    
    if surplus >= 0:
        return surplus, f"+${surplus:.1f}M"
    else:
        return surplus, f"-${abs(surplus):.1f}M"


def get_contract_category(player, player_type="batter"):
    """
    Enhanced categorization of player's contract value using new contract columns.
    
    Categories:
    - 💰 Surplus: High WAR, low AAV, pre-arb or arb status
    - ✅ Fair Value: AAV within normal range for production
    - 🚨 Albatross: High AAV, low WAR, many years left
    - 🎯 Arb Target: Arbitration status, good stats, affordable
    - 📋 Extension Committed: Has ECV > 0
    
    Returns tuple (category_name, icon, color)
    """
    if player_type == "pitcher":
        war = parse_number(player.get("WAR (Pitcher)", player.get("WAR", 0)))
    else:
        war = parse_number(player.get("WAR (Batter)", player.get("WAR", 0)))
    
    # Get enhanced contract data
    aav = calculate_aav(player)
    yl_data = parse_years_left(player.get("YL", ""))
    years_left = yl_data.get("years", 0)
    status = yl_data.get("status", "unknown")
    
    # Check for extension
    ecv = parse_salary(player.get("ECV", 0))
    has_extension = ecv > 0
    
    try:
        age = int(player.get("Age", 0))
    except (ValueError, TypeError):
        age = 0
    
    # Check for Extension Committed first (special category)
    if has_extension:
        cat_info = CONTRACT_CATEGORIES["extension_committed"]
        return ("Extension", cat_info["icon"], cat_info["color"])
    
    # Check for Albatross (high AAV, low WAR, many years left)
    if aav >= 20 and war < 1.0 and years_left >= 2:
        cat_info = CONTRACT_CATEGORIES["albatross"]
        return ("Albatross", cat_info["icon"], cat_info["color"])
    
    # Check for Arb Target (arbitration status, good stats, affordable)
    if status == "arbitration" and war >= 1.5 and aav < 10:
        cat_info = CONTRACT_CATEGORIES["arb_target"]
        return ("Arb Target", cat_info["icon"], cat_info["color"])
    
    # Check for Surplus value (high WAR, low AAV, pre-arb or arb)
    if war >= 2.0 and aav < 8 and status in ["pre_arb", "arbitration"]:
        cat_info = CONTRACT_CATEGORIES["surplus"]
        return ("Surplus", cat_info["icon"], cat_info["color"])
    
    # Also check traditional surplus criteria
    if war >= 2.0 and (aav <= 5 or years_left <= 2):
        cat_info = CONTRACT_CATEGORIES["surplus"]
        return ("Surplus", cat_info["icon"], cat_info["color"])
    
    # Default to Fair Value
    cat_info = CONTRACT_CATEGORIES["fair_value"]
    return ("Fair Value", cat_info["icon"], cat_info["color"])
