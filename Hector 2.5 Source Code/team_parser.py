# Team Parser Module
# Parse team HTML data for surplus value trade finder

from bs4 import BeautifulSoup
from trade_value import parse_number, parse_salary
from player_utils import parse_star_rating


# Team status thresholds
SELLER_WIN_PCT_THRESHOLD = 0.450      # Below this, likely seller
BUYER_WIN_PCT_THRESHOLD = 0.550       # Above this, likely buyer
GAMES_BACK_SELLER_THRESHOLD = 10.0    # 10+ games back = likely seller

# Surplus value calculation constants
DOLLARS_PER_WAR = 8.0  # Millions per WAR (league average)

# Park factor columns that may be present in Team List.html
PARK_FACTOR_COLUMNS = [
    "PF", "PF AVG", "AVG L", "AVG R",
    "PF HR", "HR L", "HR R",
    "PF D", "PF T"
]


def parse_team_html(html_path):
    """
    Parse team standings/data from an HTML file.
    
    Expected columns:
    - Team/Team Name/Abbr: Team identification
    - W/L/%: Current record and win percentage
    - POS/GB: Division position and games back
    - WAR/rWAR: Team-level WAR totals
    - lyW/lyL/ly%: Last year's record for trend analysis
    - Park factor columns: PF, PF AVG, AVG L, AVG R, PF HR, HR L, HR R, PF D, PF T
    
    Args:
        html_path: Path to the team HTML file
    
    Returns:
        List of team dicts with parsed data including park factors
    """
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, "html.parser")
    except FileNotFoundError:
        return []
    except Exception:
        return []
    
    table = soup.find("table", class_="data")
    if not table:
        return []
    
    # Get headers
    thead = table.find("thead")
    if thead:
        header_row = thead.find("tr")
    else:
        header_row = table.find("tr")
    
    if not header_row:
        return []
    
    headers = [th.get_text(strip=True) for th in header_row.find_all("th")]
    
    # Parse data rows
    tbody = table.find("tbody")
    if tbody:
        rows = tbody.find_all("tr")
    else:
        rows = table.find_all("tr")[1:]
    
    teams = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) != len(headers):
            continue
        
        team_data = {headers[i]: cells[i].get_text(strip=True) for i in range(len(headers))}
        
        # Parse park factor columns into numeric values
        for pf_col in PARK_FACTOR_COLUMNS:
            if pf_col in team_data:
                team_data[pf_col] = parse_number(team_data[pf_col])
        
        teams.append(team_data)
    
    return teams


def build_teams_by_abbr(teams_list):
    """
    Build a dictionary mapping team abbreviation to team data.
    
    The Abbr column in Team List.html corresponds to the ORG field 
    in Player List.html, enabling player-to-team lookups.
    
    Args:
        teams_list: List of team dicts from parse_team_html()
    
    Returns:
        Dict mapping team abbreviation to team data with status info:
        {
            "SF": {"Team Name": "San Francisco Giants", "status": "seller", ...},
            "PHI": {"Team Name": "Philadelphia Phillies", "status": "buyer", ...},
            ...
        }
    """
    teams_by_abbr = {}
    
    for team in teams_list:
        # Try different column names for team abbreviation
        abbr = team.get("Abbr", team.get("ORG", team.get("TM", "")))
        if not abbr:
            continue
        
        # Add team status info
        status_info = get_team_status(team)
        team_with_status = {**team, **status_info}
        
        teams_by_abbr[abbr] = team_with_status
    
    return teams_by_abbr


def get_park_factor_context(team_data, stat_type="HR"):
    """
    Get park factor context for player evaluation.
    
    Args:
        team_data: Team dict with park factor data
        stat_type: "HR", "AVG", "D", "T", or "overall"
    
    Returns:
        Dict with park factor info and interpretation:
        {
            "factor": 0.688,
            "type": "pitcher_friendly",
            "description": "Suppresses home runs significantly (-31%)"
        }
    """
    if not team_data:
        return {"factor": 1.0, "type": "neutral", "description": "No park data available"}
    
    # Map stat type to column names
    column_map = {
        "HR": "PF HR",
        "AVG": "PF AVG", 
        "D": "PF D",
        "T": "PF T",
        "overall": "PF"
    }
    
    col = column_map.get(stat_type, "PF HR")
    factor = team_data.get(col, 1.0)
    
    if not isinstance(factor, (int, float)):
        factor = parse_number(factor)
    
    # Default to 1.0 if factor is 0 or invalid
    if factor == 0 or factor is None:
        factor = 1.0
    
    # Calculate percentage change with consistent formatting
    pct_change = int((factor - 1) * 100)
    pct_str = f"{pct_change:+d}%" if pct_change != 0 else "0%"
    
    # Interpret the park factor
    if factor < 0.85:
        pf_type = "pitcher_friendly"
        effect = f"Suppresses {stat_type} significantly ({pct_str})"
    elif factor < 0.95:
        pf_type = "slightly_pitcher_friendly"
        effect = f"Slightly suppresses {stat_type} ({pct_str})"
    elif factor > 1.15:
        pf_type = "hitter_friendly"
        effect = f"Boosts {stat_type} significantly ({pct_str})"
    elif factor > 1.05:
        pf_type = "slightly_hitter_friendly"
        effect = f"Slightly boosts {stat_type} ({pct_str})"
    else:
        pf_type = "neutral"
        effect = f"Neutral for {stat_type}"
    
    return {
        "factor": factor,
        "type": pf_type,
        "description": effect
    }


def get_team_status(team_data):
    """
    Determine if a team is a buyer, seller, or neutral.
    
    Args:
        team_data: Team dict with W, L, %, GB, lyW, lyL, ly% keys
    
    Returns:
        Dict with status info:
        - status: "buyer", "seller", or "neutral"
        - win_pct: Current win percentage
        - games_back: Games behind leader
        - trend: "improving", "declining", or "stable"
        - confidence: 0-100 score of how confident the classification is
    """
    # Parse current record
    wins = parse_number(team_data.get("W", 0))
    losses = parse_number(team_data.get("L", 0))
    
    # Win percentage - try both "%" and "W%" as column names
    win_pct = parse_number(team_data.get("%", team_data.get("W%", 0)))
    if win_pct == 0 and (wins + losses) > 0:
        win_pct = wins / (wins + losses)
    
    # Games back
    gb_raw = team_data.get("GB", "0")
    if gb_raw == "-" or gb_raw == "":
        games_back = 0.0
    else:
        games_back = parse_number(gb_raw)
    
    # Last year's record for trend
    ly_wins = parse_number(team_data.get("lyW", 0))
    ly_losses = parse_number(team_data.get("lyL", 0))
    ly_pct = parse_number(team_data.get("ly%", 0))
    if ly_pct == 0 and (ly_wins + ly_losses) > 0:
        ly_pct = ly_wins / (ly_wins + ly_losses)
    
    # Calculate trend
    if ly_pct > 0:
        pct_change = win_pct - ly_pct
        if pct_change > 0.03:
            trend = "improving"
        elif pct_change < -0.03:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "unknown"
    
    # Determine status
    confidence = 50  # Start at neutral confidence
    
    if win_pct < SELLER_WIN_PCT_THRESHOLD:
        status = "seller"
        confidence = min(100, 50 + int((SELLER_WIN_PCT_THRESHOLD - win_pct) * 200))
    elif win_pct > BUYER_WIN_PCT_THRESHOLD:
        status = "buyer"
        confidence = min(100, 50 + int((win_pct - BUYER_WIN_PCT_THRESHOLD) * 200))
    elif games_back >= GAMES_BACK_SELLER_THRESHOLD:
        status = "seller"
        confidence = min(100, 50 + int(games_back * 3))
    else:
        status = "neutral"
    
    # Adjust confidence based on trend
    if status == "seller" and trend == "declining":
        confidence = min(100, confidence + 15)
    elif status == "buyer" and trend == "improving":
        confidence = min(100, confidence + 15)
    elif status == "seller" and trend == "improving":
        confidence = max(30, confidence - 10)
    elif status == "buyer" and trend == "declining":
        confidence = max(30, confidence - 10)
    
    return {
        "status": status,
        "win_pct": win_pct,
        "wins": wins,
        "losses": losses,
        "games_back": games_back,
        "trend": trend,
        "last_year_pct": ly_pct,
        "confidence": confidence,
    }


def calculate_surplus_value(war, salary):
    """
    Calculate surplus value for a player.
    
    Surplus Value = (WAR * $/WAR baseline) - Actual Salary
    
    Positive values indicate the player is providing more value
    than they're being paid for.
    
    Args:
        war: Player's WAR value
        salary: Player's salary in millions
    
    Returns:
        Surplus value in millions (can be negative for overpays)
    """
    expected_salary = war * DOLLARS_PER_WAR
    return expected_salary - salary


def get_surplus_tier(surplus_value):
    """
    Get a tier label for surplus value.
    
    Args:
        surplus_value: Calculated surplus value in millions
    
    Returns:
        Dict with tier info (name, icon, color, description)
    """
    if surplus_value >= 15:
        return {
            "tier": "Elite",
            "icon": "💎",
            "color": "#51cf66",
            "description": "Exceptional value, franchise-altering"
        }
    elif surplus_value >= 8:
        return {
            "tier": "Excellent",
            "icon": "⭐",
            "color": "#4dabf7",
            "description": "Great value, impact player at low cost"
        }
    elif surplus_value >= 3:
        return {
            "tier": "Good",
            "icon": "✅",
            "color": "#ffd43b",
            "description": "Solid value, useful contributor"
        }
    elif surplus_value >= 0:
        return {
            "tier": "Fair",
            "icon": "➖",
            "color": "#ced4da",
            "description": "Market rate value"
        }
    elif surplus_value >= -5:
        return {
            "tier": "Overpay",
            "icon": "⚠️",
            "color": "#ff922b",
            "description": "Slightly overpaid"
        }
    else:
        return {
            "tier": "Bad",
            "icon": "🚨",
            "color": "#ff6b6b",
            "description": "Significantly overpaid"
        }


def find_trade_candidates(players, teams_data, player_type="batter"):
    """
    Find players who are good trade candidates based on surplus value
    and team context.
    
    Args:
        players: List of player dicts
        teams_data: Dict mapping team abbr to team status info
        player_type: "batter" or "pitcher"
    
    Returns:
        List of trade candidate dicts sorted by trade fit score
    """
    candidates = []
    
    for player in players:
        team_abbr = player.get("ORG", player.get("TM", ""))
        
        # Get player stats
        if player_type == "pitcher":
            war = parse_number(player.get("WAR (Pitcher)", player.get("WAR", 0)))
        else:
            war = parse_number(player.get("WAR (Batter)", player.get("WAR", 0)))
        
        # Get salary using the existing parse_salary function
        salary = parse_salary(player.get("SLR", 0))
        
        # Calculate surplus value
        surplus = calculate_surplus_value(war, salary)
        surplus_tier = get_surplus_tier(surplus)
        
        # Get team context
        team_info = teams_data.get(team_abbr, {})
        team_status = team_info.get("status", "neutral")
        
        # Calculate trade fit score
        # Higher score = better trade candidate for acquiring teams
        trade_fit = 50  # Base score
        
        # Surplus value contribution (40 points max)
        trade_fit += min(40, max(-20, surplus * 3))
        
        # Team status contribution (20 points max)
        if team_status == "seller":
            trade_fit += 20
        elif team_status == "neutral":
            trade_fit += 5
        # Buyers get no bonus
        
        # Age consideration (10 points max)
        try:
            age = int(player.get("Age", 30))
        except (ValueError, TypeError):
            age = 30
        
        if age <= 27:
            trade_fit += 10
        elif age <= 30:
            trade_fit += 5
        elif age >= 34:
            trade_fit -= 5
        
        # WAR contribution (10 points max)
        trade_fit += min(10, war * 3)
        
        # Get OVR for display using shared utility
        ovr = parse_star_rating(player.get("OVR", "0"))
        
        candidates.append({
            "player": player,
            "name": player.get("Name", ""),
            "pos": player.get("POS", ""),
            "team": team_abbr,
            "age": age,
            "ovr": ovr,
            "war": war,
            "salary": salary,
            "surplus_value": surplus,
            "surplus_tier": surplus_tier,
            "team_status": team_status,
            "team_info": team_info,
            "trade_fit": max(0, min(100, trade_fit)),
        })
    
    # Sort by trade fit descending
    candidates.sort(key=lambda x: x["trade_fit"], reverse=True)
    return candidates


# Trade value calculation constants
TRADE_GRADE_THRESHOLDS = {
    "A+": 0.30,   # Gain 30%+ value
    "A": 0.15,    # Gain 15-30%
    "B": 0.15,    # Within ±15% (fair trade)
    "C": -0.15,   # Lose 15-30%
    "D": -0.30,   # Lose 30-50%
    "F": -0.50,   # Lose 50%+
}


def calculate_comprehensive_trade_value(player, teams_data, player_type="batter"):
    """
    Calculate comprehensive trade value for a player.
    
    Trade Value = base_surplus_value + park_adjustment_bonus + age_adjustment + contract_value
    
    Args:
        player: Player dict
        teams_data: Dict mapping team abbr to team data with park factors
        player_type: "batter" or "pitcher"
    
    Returns:
        Dict with detailed trade value breakdown:
        {
            "total_trade_value": 85.5,
            "base_surplus_value": 12.0,
            "park_adjustment_bonus": 3.5,
            "age_adjustment": 5.0,
            "contract_value": 8.0,
            "is_hidden_gem": True,
            "trade_grade_modifier": 0.0,
        }
    """
    from trade_value import parse_years_left
    
    team_abbr = player.get("ORG", player.get("TM", ""))
    team_info = teams_data.get(team_abbr, {})
    
    # Get player stats
    if player_type == "pitcher":
        war = parse_number(player.get("WAR (Pitcher)", player.get("WAR", 0)))
    else:
        war = parse_number(player.get("WAR (Batter)", player.get("WAR", 0)))
    
    salary = parse_salary(player.get("SLR", 0))
    
    # 1. Base surplus value (WAR-based)
    base_surplus = calculate_surplus_value(war, salary)
    
    # 2. Park adjustment bonus
    park_bonus = 0.0
    is_hidden_gem = False
    
    if team_info:
        pf_overall = team_info.get("PF", 1.0)
        pf_hr = team_info.get("PF HR", 1.0)
        
        if not isinstance(pf_overall, (int, float)) or pf_overall <= 0:
            pf_overall = 1.0
        if not isinstance(pf_hr, (int, float)) or pf_hr <= 0:
            pf_hr = 1.0
        
        if player_type == "batter":
            # Batters in pitcher parks get bonus
            if pf_overall < 0.95 or pf_hr < 0.90:
                # Calculate bonus based on how suppressive the park is
                suppression = (1.0 - pf_overall) + (1.0 - pf_hr) / 2
                park_bonus = suppression * 5.0  # Up to ~5M bonus
                
                # Check hidden gem criteria
                power = parse_number(player.get("POW", 0))
                contact = parse_number(player.get("CON", 0))
                if power >= 50 or contact >= 55:
                    is_hidden_gem = True
        else:
            # Pitchers in hitter parks get bonus
            if pf_overall > 1.05 or pf_hr > 1.10:
                # Calculate bonus based on how inflating the park is
                inflation = (pf_overall - 1.0) + (pf_hr - 1.0) / 2
                park_bonus = inflation * 5.0  # Up to ~5M bonus
                
                # Check hidden gem criteria
                stuff = parse_number(player.get("STU", 0))
                movement = parse_number(player.get("MOV", 0))
                if stuff >= 50 or movement >= 55:
                    is_hidden_gem = True
    
    # 3. Age adjustment
    try:
        age = int(player.get("Age", 30))
    except (ValueError, TypeError):
        age = 30
    
    if age <= 23:
        age_adjustment = 8.0
    elif age <= 25:
        age_adjustment = 5.0
    elif age <= 27:
        age_adjustment = 2.0
    elif age <= 29:
        age_adjustment = 0.0
    elif age <= 32:
        age_adjustment = -3.0
    else:
        age_adjustment = -6.0
    
    # 4. Contract value (years of control, salary efficiency)
    yl_data = parse_years_left(player.get("YL", ""))
    years_left = yl_data.get("years", 0)
    status = yl_data.get("status", "unknown")
    
    contract_value = 0.0
    
    # Years of control bonus
    if status == "pre_arb":
        contract_value += years_left * 3.0  # Pre-arb years very valuable
    elif status == "arbitration":
        contract_value += years_left * 2.0  # Arb years still valuable
    else:
        contract_value += years_left * 1.0  # Signed years
    
    # Salary efficiency bonus (low salary = more valuable)
    if salary < 1.0:
        contract_value += 4.0
    elif salary < 5.0:
        contract_value += 2.0
    elif salary > 20.0:
        contract_value -= 3.0
    elif salary > 15.0:
        contract_value -= 1.0
    
    # Calculate total trade value (normalize to 0-100 scale)
    raw_total = base_surplus + park_bonus + age_adjustment + contract_value
    
    # Normalize: surplus typically ranges from -20 to +30, map to 0-100
    normalized_total = max(0, min(100, 50 + raw_total * 1.5))
    
    return {
        "total_trade_value": round(normalized_total, 1),
        "base_surplus_value": round(base_surplus, 1),
        "park_adjustment_bonus": round(park_bonus, 1),
        "age_adjustment": round(age_adjustment, 1),
        "contract_value": round(contract_value, 1),
        "is_hidden_gem": is_hidden_gem,
        "raw_total": round(raw_total, 1),
    }


def calculate_trade_grade(offered_value, received_value):
    """
    Calculate trade grade based on value differential.
    
    Args:
        offered_value: Total value of players you're trading away
        received_value: Total value of players you're receiving
    
    Returns:
        Dict with grade info:
        {
            "grade": "A",
            "differential": 0.25,
            "differential_pct": "+25%",
            "description": "You gain 15-30% value"
        }
    """
    if offered_value <= 0:
        offered_value = 1  # Avoid division by zero
    
    differential = (received_value - offered_value) / offered_value
    
    # Determine grade
    if differential >= 0.30:
        grade = "A+"
        description = "You gain 30%+ value - Excellent trade!"
        color = "#51cf66"  # Green
    elif differential >= 0.15:
        grade = "A"
        description = "You gain 15-30% value - Great trade"
        color = "#4dabf7"  # Blue
    elif differential >= -0.15:
        grade = "B"
        description = "Roughly fair trade (±15%)"
        color = "#ffd43b"  # Yellow
    elif differential >= -0.30:
        grade = "C"
        description = "You lose 15-30% value"
        color = "#ff922b"  # Orange
    elif differential >= -0.50:
        grade = "D"
        description = "You lose 30-50% value"
        color = "#ff6b6b"  # Red
    else:
        grade = "F"
        description = "You lose 50%+ value - You got fleeced!"
        color = "#e03131"  # Dark red
    
    # Format differential percentage
    if differential >= 0:
        diff_pct = f"+{differential*100:.0f}%"
    else:
        diff_pct = f"{differential*100:.0f}%"
    
    return {
        "grade": grade,
        "differential": round(differential, 3),
        "differential_pct": diff_pct,
        "description": description,
        "color": color,
    }


def find_hidden_gem_trade_targets(players, teams_data, player_type="batter"):
    """
    Find hidden gem players who are undervalued due to park factors.
    
    Hidden Gem Criteria:
    - Plays in extreme pitcher park (PF < 0.95 or PF HR < 0.90) for batters
    - Plays in extreme hitter park (PF > 1.05 or PF HR > 1.10) for pitchers
    - Has good raw power/contact/stuff being suppressed
    - On a seller team (more likely available via trade)
    - Good surplus value (underpaid relative to production)
    
    Args:
        players: List of player dicts
        teams_data: Dict mapping team abbr to team data
        player_type: "batter" or "pitcher"
    
    Returns:
        List of hidden gem candidates with park-adjusted upside info
    """
    hidden_gems = []
    
    for player in players:
        team_abbr = player.get("ORG", player.get("TM", ""))
        team_info = teams_data.get(team_abbr, {})
        
        if not team_info:
            continue
        
        # Get park factors
        pf_overall = team_info.get("PF", 1.0)
        pf_hr = team_info.get("PF HR", 1.0)
        
        if not isinstance(pf_overall, (int, float)) or pf_overall <= 0:
            pf_overall = 1.0
        if not isinstance(pf_hr, (int, float)) or pf_hr <= 0:
            pf_hr = 1.0
        
        is_hidden_gem = False
        park_adjusted_upside = 0.0
        upside_description = ""
        
        if player_type == "batter":
            # Check for suppressive park
            if pf_overall < 0.95 or pf_hr < 0.90:
                power = parse_number(player.get("POW", 0))
                contact = parse_number(player.get("CON", 0))
                
                if power >= 50 or contact >= 55:
                    is_hidden_gem = True
                    
                    # Calculate park-adjusted upside
                    power_upside = power * (1 / pf_hr) - power if pf_hr > 0 else 0
                    contact_upside = contact * (1 / pf_overall) - contact if pf_overall > 0 else 0
                    park_adjusted_upside = power_upside + contact_upside
                    
                    upside_description = f"+{power_upside:.1f} POW, +{contact_upside:.1f} CON in neutral park"
        else:
            # Check for inflating park
            if pf_overall > 1.05 or pf_hr > 1.10:
                stuff = parse_number(player.get("STU", 0))
                movement = parse_number(player.get("MOV", 0))
                
                if stuff >= 50 or movement >= 55:
                    is_hidden_gem = True
                    
                    # Calculate park-adjusted upside (stats look better in neutral park)
                    stuff_upside = stuff * pf_overall - stuff
                    movement_upside = movement * pf_overall - movement
                    park_adjusted_upside = stuff_upside + movement_upside
                    
                    upside_description = f"+{stuff_upside:.1f} STU, +{movement_upside:.1f} MOV effective value"
        
        if not is_hidden_gem:
            continue
        
        # Get additional info
        if player_type == "pitcher":
            war = parse_number(player.get("WAR (Pitcher)", player.get("WAR", 0)))
        else:
            war = parse_number(player.get("WAR (Batter)", player.get("WAR", 0)))
        
        salary = parse_salary(player.get("SLR", 0))
        surplus = calculate_surplus_value(war, salary)
        team_status = team_info.get("status", "neutral")
        
        try:
            age = int(player.get("Age", 30))
        except (ValueError, TypeError):
            age = 30
        
        ovr = parse_star_rating(player.get("OVR", "0"))
        
        # Calculate gem score (how good of a hidden gem this is)
        gem_score = 50  # Base
        gem_score += min(25, park_adjusted_upside * 2)  # Park upside contribution
        gem_score += min(15, surplus * 2)  # Surplus value contribution
        if team_status == "seller":
            gem_score += 10  # Availability bonus
        if age <= 27:
            gem_score += 10  # Youth bonus
        
        hidden_gems.append({
            "player": player,
            "name": player.get("Name", ""),
            "pos": player.get("POS", ""),
            "team": team_abbr,
            "age": age,
            "ovr": ovr,
            "war": war,
            "salary": salary,
            "surplus_value": surplus,
            "team_status": team_status,
            "pf_overall": pf_overall,
            "pf_hr": pf_hr,
            "park_adjusted_upside": round(park_adjusted_upside, 1),
            "upside_description": upside_description,
            "gem_score": max(0, min(100, gem_score)),
        })
    
    # Sort by gem score descending
    hidden_gems.sort(key=lambda x: x["gem_score"], reverse=True)
    return hidden_gems
