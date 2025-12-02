# Hidden Gems / AAAA Finder
# Detects overlooked players who deserve a second look

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


# Hidden Gem Category Definitions
HIDDEN_GEM_CATEGORIES = {
    "aaaa": {
        "icon": "📦",
        "name": "AAAA Players",
        "description": "Solid but not star, good stats, could start elsewhere",
        "color": "#4dabf7",
    },
    "late_bloomer": {
        "icon": "🌸",
        "name": "Late Bloomers",
        "description": "Age 26-28, OVR close to POT, still has upside",
        "color": "#9775fa",
    },
    "miscast": {
        "icon": "🎯",
        "name": "Miscast Players",
        "description": "Good bat, poor defense at premium position, should be DH/corner",
        "color": "#ff922b",
    },
    "undervalued_vet": {
        "icon": "👴",
        "name": "Undervalued Veterans",
        "description": "Age 30+, still producing, cheap/expiring contract",
        "color": "#51cf66",
    },
    "toolsy_gamble": {
        "icon": "🎰",
        "name": "Toolsy Gambles",
        "description": "1-2 elite tools (65+), other ratings mediocre, age ≤27",
        "color": "#ff6b6b",
    },
    "reliever_convert": {
        "icon": "🔄",
        "name": "Reliever Converts",
        "description": "SP with low stamina but good stuff/movement, better as RP",
        "color": "#ffd43b",
    },
}


def find_aaaa_players(batters, pitchers):
    """
    Find AAAA Players:
    - OVR 45-55 (solid but not star)
    - Good stats (wRC+ ≥ 100 or ERA+ ≥ 100)
    - Not necessarily starting (might be blocked)
    - Could start elsewhere
    """
    results = []
    
    # Process batters
    for batter in batters:
        ovr = parse_star_rating(batter.get("OVR", "0"))
        
        # Check if OVR is in range (handle both 20-80 scale and star scale)
        if ovr > 10:  # 20-80 scale
            if not (45 <= ovr <= 55):
                continue
        else:  # Star scale (1-5)
            if not (2.5 <= ovr <= 3.5):
                continue
        
        wrc_plus = parse_number(batter.get("wRC+", 0))
        
        if wrc_plus < 100:
            continue
        
        # This player qualifies
        results.append({
            "player": batter,
            "type": "batter",
            "category": "aaaa",
            "name": batter.get("Name", ""),
            "team": batter.get("ORG", ""),
            "pos": batter.get("POS", ""),
            "age": get_age(batter),
            "ovr": ovr,
            "pot": parse_star_rating(batter.get("POT", "0")),
            "key_stat": f"wRC+ {wrc_plus:.0f}",
            "why_hidden": "Solid OVR, producing well",
            "upside": "Could be everyday starter",
        })
    
    # Process pitchers
    for pitcher in pitchers:
        ovr = parse_star_rating(pitcher.get("OVR", "0"))
        
        # Check if OVR is in range
        if ovr > 10:  # 20-80 scale
            if not (45 <= ovr <= 55):
                continue
        else:  # Star scale (1-5)
            if not (2.5 <= ovr <= 3.5):
                continue
        
        era_plus = parse_number(pitcher.get("ERA+", 0))
        
        if era_plus < 100:
            continue
        
        results.append({
            "player": pitcher,
            "type": "pitcher",
            "category": "aaaa",
            "name": pitcher.get("Name", ""),
            "team": pitcher.get("ORG", ""),
            "pos": pitcher.get("POS", ""),
            "age": get_age(pitcher),
            "ovr": ovr,
            "pot": parse_star_rating(pitcher.get("POT", "0")),
            "key_stat": f"ERA+ {era_plus:.0f}",
            "why_hidden": "Solid OVR, producing well",
            "upside": "Could be rotation/bullpen piece",
        })
    
    return results


def find_late_bloomers(batters, pitchers):
    """
    Find Late Bloomers:
    - Age 26-28
    - OVR increased (current OVR close to POT)
    - Still has upside (POT - OVR ≥ 5 on 20-80 scale, or ≥ 0.5 on star scale)
    - Good current stats
    """
    results = []
    
    for batter in batters:
        age = get_age(batter)
        if not (26 <= age <= 28):
            continue
        
        ovr = parse_star_rating(batter.get("OVR", "0"))
        pot = parse_star_rating(batter.get("POT", "0"))
        
        # Calculate remaining upside
        if ovr > 10:  # 20-80 scale
            upside_gap = pot - ovr
            if upside_gap < 5:
                continue
        else:  # Star scale
            upside_gap = pot - ovr
            if upside_gap < 0.5:
                continue
        
        wrc_plus = parse_number(batter.get("wRC+", 0))
        if wrc_plus < 95:  # Still producing reasonably
            continue
        
        results.append({
            "player": batter,
            "type": "batter",
            "category": "late_bloomer",
            "name": batter.get("Name", ""),
            "team": batter.get("ORG", ""),
            "pos": batter.get("POS", ""),
            "age": age,
            "ovr": ovr,
            "pot": pot,
            "key_stat": f"wRC+ {wrc_plus:.0f}, Gap {upside_gap:.1f}",
            "why_hidden": "Still developing at age 26-28",
            "upside": f"Could reach {pot:.1f} POT",
        })
    
    for pitcher in pitchers:
        age = get_age(pitcher)
        if not (26 <= age <= 28):
            continue
        
        ovr = parse_star_rating(pitcher.get("OVR", "0"))
        pot = parse_star_rating(pitcher.get("POT", "0"))
        
        if ovr > 10:  # 20-80 scale
            upside_gap = pot - ovr
            if upside_gap < 5:
                continue
        else:  # Star scale
            upside_gap = pot - ovr
            if upside_gap < 0.5:
                continue
        
        era_plus = parse_number(pitcher.get("ERA+", 0))
        if era_plus < 95:
            continue
        
        results.append({
            "player": pitcher,
            "type": "pitcher",
            "category": "late_bloomer",
            "name": pitcher.get("Name", ""),
            "team": pitcher.get("ORG", ""),
            "pos": pitcher.get("POS", ""),
            "age": age,
            "ovr": ovr,
            "pot": pot,
            "key_stat": f"ERA+ {era_plus:.0f}, Gap {upside_gap:.1f}",
            "why_hidden": "Still developing at age 26-28",
            "upside": f"Could reach {pot:.1f} POT",
        })
    
    return results


def find_miscast_players(batters):
    """
    Find Miscast Players (batters only):
    - Good batting ratings but poor defensive ratings
    - Playing a premium defensive position (C, SS, CF) but shouldn't be
    - Should be DH or corner position
    """
    results = []
    premium_positions = {"C", "SS", "CF"}
    
    for batter in batters:
        pos = batter.get("POS", "")
        if pos not in premium_positions:
            continue
        
        # Get batting ratings
        con = parse_number(batter.get("CON", 0))
        pow_ = parse_number(batter.get("POW", 0))
        eye = parse_number(batter.get("EYE", 0))
        bat_avg = (con + pow_ + eye) / 3
        
        # Get defensive ratings based on position
        if pos == "C":
            def_ratings = [
                parse_number(batter.get("C ABI", 0)),
                parse_number(batter.get("C ARM", 0)),
                parse_number(batter.get("C FRM", 0)),
            ]
        elif pos == "SS":
            def_ratings = [
                parse_number(batter.get("IF RNG", 0)),
                parse_number(batter.get("IF ARM", 0)),
                parse_number(batter.get("IF ERR", 0)),
            ]
        else:  # CF
            def_ratings = [
                parse_number(batter.get("OF RNG", 0)),
                parse_number(batter.get("OF ARM", 0)),
                parse_number(batter.get("OF ERR", 0)),
            ]
        
        def_avg = sum(def_ratings) / len(def_ratings) if def_ratings else 0
        
        # Good bat (avg rating >= 50) but poor defense (< 40)
        if bat_avg >= 50 and def_avg < 40:
            results.append({
                "player": batter,
                "type": "batter",
                "category": "miscast",
                "name": batter.get("Name", ""),
                "team": batter.get("ORG", ""),
                "pos": pos,
                "age": get_age(batter),
                "ovr": parse_star_rating(batter.get("OVR", "0")),
                "pot": parse_star_rating(batter.get("POT", "0")),
                "key_stat": f"Bat {bat_avg:.0f}, Def {def_avg:.0f}",
                "why_hidden": f"Good bat stuck at {pos}",
                "upside": "Would thrive at DH/corner",
            })
    
    return results


def find_undervalued_veterans(batters, pitchers):
    """
    Find Undervalued Veterans:
    - Age 30+
    - Still producing (wRC+ ≥ 95 or ERA+ ≥ 95)
    - Cheap contract (AAV < $5M) or expiring
    - Teams may have given up too early
    """
    results = []
    
    for batter in batters:
        age = get_age(batter)
        if age < 30:
            continue
        
        wrc_plus = parse_number(batter.get("wRC+", 0))
        if wrc_plus < 95:
            continue
        
        # Check contract
        salary = parse_salary(batter.get("SLR", 0))
        yl_data = parse_years_left(batter.get("YL", ""))
        years_left = yl_data.get("years", 99)
        
        # Cheap (< $5M) or expiring
        is_cheap = salary < 5
        is_expiring = years_left <= 1
        
        if not (is_cheap or is_expiring):
            continue
        
        contract_note = ""
        if is_cheap:
            contract_note = f"${salary:.1f}M AAV"
        if is_expiring:
            contract_note = "Expiring" if not contract_note else f"{contract_note}, Expiring"
        
        results.append({
            "player": batter,
            "type": "batter",
            "category": "undervalued_vet",
            "name": batter.get("Name", ""),
            "team": batter.get("ORG", ""),
            "pos": batter.get("POS", ""),
            "age": age,
            "ovr": parse_star_rating(batter.get("OVR", "0")),
            "pot": parse_star_rating(batter.get("POT", "0")),
            "key_stat": f"wRC+ {wrc_plus:.0f}",
            "why_hidden": contract_note,
            "upside": "Productive veteran depth",
        })
    
    for pitcher in pitchers:
        age = get_age(pitcher)
        if age < 30:
            continue
        
        era_plus = parse_number(pitcher.get("ERA+", 0))
        if era_plus < 95:
            continue
        
        salary = parse_salary(pitcher.get("SLR", 0))
        yl_data = parse_years_left(pitcher.get("YL", ""))
        years_left = yl_data.get("years", 99)
        
        is_cheap = salary < 5
        is_expiring = years_left <= 1
        
        if not (is_cheap or is_expiring):
            continue
        
        contract_note = ""
        if is_cheap:
            contract_note = f"${salary:.1f}M AAV"
        if is_expiring:
            contract_note = "Expiring" if not contract_note else f"{contract_note}, Expiring"
        
        results.append({
            "player": pitcher,
            "type": "pitcher",
            "category": "undervalued_vet",
            "name": pitcher.get("Name", ""),
            "team": pitcher.get("ORG", ""),
            "pos": pitcher.get("POS", ""),
            "age": age,
            "ovr": parse_star_rating(pitcher.get("OVR", "0")),
            "pot": parse_star_rating(pitcher.get("POT", "0")),
            "key_stat": f"ERA+ {era_plus:.0f}",
            "why_hidden": contract_note,
            "upside": "Productive veteran depth",
        })
    
    return results


def find_toolsy_gambles(batters, pitchers):
    """
    Find Toolsy Gambles:
    - 1-2 ratings at 65+ (elite tools)
    - Other ratings mediocre (40-50)
    - High variance - could be star or bust
    - Age ≤ 27 (still time to develop)
    """
    results = []
    
    for batter in batters:
        age = get_age(batter)
        if age > 27:
            continue
        
        # Get all tool ratings
        tools = {
            "CON": parse_number(batter.get("CON", 0)),
            "POW": parse_number(batter.get("POW", 0)),
            "EYE": parse_number(batter.get("EYE", 0)),
            "SPE": parse_number(batter.get("SPE", 0)),
        }
        
        # Count elite tools (65+) and mediocre tools (40-50)
        elite_tools = [(name, val) for name, val in tools.items() if val >= 65]
        mediocre_tools = [(name, val) for name, val in tools.items() if 40 <= val <= 50]
        
        # Need 1-2 elite tools and at least 1-2 mediocre
        if not (1 <= len(elite_tools) <= 2):
            continue
        if len(mediocre_tools) < 1:
            continue
        
        elite_names = ", ".join([t[0] for t in elite_tools])
        
        results.append({
            "player": batter,
            "type": "batter",
            "category": "toolsy_gamble",
            "name": batter.get("Name", ""),
            "team": batter.get("ORG", ""),
            "pos": batter.get("POS", ""),
            "age": age,
            "ovr": parse_star_rating(batter.get("OVR", "0")),
            "pot": parse_star_rating(batter.get("POT", "0")),
            "key_stat": f"Elite: {elite_names}",
            "why_hidden": "Uneven profile, high variance",
            "upside": "Elite tools could emerge",
        })
    
    for pitcher in pitchers:
        age = get_age(pitcher)
        if age > 27:
            continue
        
        tools = {
            "STU": parse_number(pitcher.get("STU", 0)),
            "MOV": parse_number(pitcher.get("MOV", 0)),
            "CON": parse_number(pitcher.get("CON", 0)),
        }
        
        elite_tools = [(name, val) for name, val in tools.items() if val >= 65]
        mediocre_tools = [(name, val) for name, val in tools.items() if 40 <= val <= 50]
        
        if not (1 <= len(elite_tools) <= 2):
            continue
        if len(mediocre_tools) < 1:
            continue
        
        elite_names = ", ".join([t[0] for t in elite_tools])
        
        results.append({
            "player": pitcher,
            "type": "pitcher",
            "category": "toolsy_gamble",
            "name": pitcher.get("Name", ""),
            "team": pitcher.get("ORG", ""),
            "pos": pitcher.get("POS", ""),
            "age": age,
            "ovr": parse_star_rating(pitcher.get("OVR", "0")),
            "pot": parse_star_rating(pitcher.get("POT", "0")),
            "key_stat": f"Elite: {elite_names}",
            "why_hidden": "Uneven profile, high variance",
            "upside": "Elite tools could emerge",
        })
    
    return results


def find_reliever_converts(pitchers):
    """
    Find Reliever Converts:
    - Listed as SP
    - Low stamina (STM < 45)
    - Good stuff (STU ≥ 55) or movement (MOV ≥ 55)
    - Would be better as RP
    """
    results = []
    
    for pitcher in pitchers:
        pos = pitcher.get("POS", "")
        if pos != "SP":
            continue
        
        stamina = parse_number(pitcher.get("STM", 0))
        if stamina >= 45:
            continue
        
        stuff = parse_number(pitcher.get("STU", 0))
        movement = parse_number(pitcher.get("MOV", 0))
        
        if stuff < 55 and movement < 55:
            continue
        
        best_pitch = "Stuff" if stuff >= movement else "Movement"
        best_value = max(stuff, movement)
        
        results.append({
            "player": pitcher,
            "type": "pitcher",
            "category": "reliever_convert",
            "name": pitcher.get("Name", ""),
            "team": pitcher.get("ORG", ""),
            "pos": pos,
            "age": get_age(pitcher),
            "ovr": parse_star_rating(pitcher.get("OVR", "0")),
            "pot": parse_star_rating(pitcher.get("POT", "0")),
            "key_stat": f"STM {stamina:.0f}, {best_pitch} {best_value:.0f}",
            "why_hidden": "Listed as SP, low stamina",
            "upside": "High-leverage reliever potential",
        })
    
    return results


def find_all_hidden_gems(batters, pitchers):
    """
    Find all hidden gems across all categories.
    Returns dict of category -> list of players
    """
    return {
        "aaaa": find_aaaa_players(batters, pitchers),
        "late_bloomer": find_late_bloomers(batters, pitchers),
        "miscast": find_miscast_players(batters),
        "undervalued_vet": find_undervalued_veterans(batters, pitchers),
        "toolsy_gamble": find_toolsy_gambles(batters, pitchers),
        "reliever_convert": find_reliever_converts(pitchers),
    }


def get_hidden_gems_summary(hidden_gems):
    """Get a summary count of hidden gems by category"""
    summary = {}
    for category, players in hidden_gems.items():
        cat_info = HIDDEN_GEM_CATEGORIES.get(category, {})
        summary[category] = {
            "count": len(players),
            "name": cat_info.get("name", category),
            "icon": cat_info.get("icon", ""),
        }
    return summary
