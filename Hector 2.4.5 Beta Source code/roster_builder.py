# Roster Builder Logic
# Handles roster building logic, grades, summaries, and archetype detection

from trade_value import parse_number, parse_salary, parse_years_left
from archetypes import get_best_archetype, ARCHETYPES
from player_utils import parse_star_rating, get_age, get_war, normalize_rating, STAR_TO_RATING_SCALE


# Roster slot definitions
LINEUP_SLOTS = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"]
BENCH_COUNT = 4
ROTATION_COUNT = 5
BULLPEN_COUNT = 7

# Position group definitions for grading
POSITION_GROUPS = {
    "C": ["C"],
    "1B": ["1B"],
    "2B": ["2B"],
    "3B": ["3B"],
    "SS": ["SS"],
    "OF": ["LF", "CF", "RF"],
    "SP": ["SP"],
    "RP": ["RP", "CL"],
}

# Grade thresholds based on OVR
GRADE_THRESHOLDS = {
    "A+": {"min": 80, "color": "#51cf66"},  # Best in league
    "A": {"min": 70, "color": "#4dabf7"},   # Top 10%
    "B+": {"min": 65, "color": "#74c0fc"},  # Top 25%
    "B": {"min": 60, "color": "#ffd43b"},   # Above average
    "C": {"min": 55, "color": "#ff922b"},   # Average
    "D": {"min": 50, "color": "#ff6b6b"},   # Below average
    "F": {"min": 0, "color": "#c92a2a"},    # Major weakness
}


def get_grade_for_ovr(ovr, league_avg=55):
    """
    Get letter grade for an OVR value.
    Handles both 20-80 scale and star scale.
    """
    # Normalize to 20-80 scale if needed using shared utility
    ovr = normalize_rating(ovr)
    
    for grade, info in GRADE_THRESHOLDS.items():
        if ovr >= info["min"]:
            return {"grade": grade, "color": info["color"]}
    
    return {"grade": "F", "color": GRADE_THRESHOLDS["F"]["color"]}


class RosterBuilder:
    """
    Manages a hypothetical roster build.
    Tracks lineup, bench, rotation, and bullpen.
    """
    
    def __init__(self):
        self.lineup = {pos: None for pos in LINEUP_SLOTS}
        self.bench = []
        self.rotation = []
        self.bullpen = []
        self._all_batters = []
        self._all_pitchers = []
    
    def set_player_pools(self, batters, pitchers):
        """Set the available player pools"""
        self._all_batters = list(batters)
        self._all_pitchers = list(pitchers)
    
    def add_to_lineup(self, player, position):
        """Add a player to a lineup position"""
        if position not in LINEUP_SLOTS:
            return False
        
        # Remove player from any other slot first
        self.remove_player(player)
        
        self.lineup[position] = player
        return True
    
    def add_to_bench(self, player):
        """Add a player to the bench"""
        if len(self.bench) >= BENCH_COUNT:
            return False
        
        # Remove from other slots first
        self.remove_player(player)
        
        self.bench.append(player)
        return True
    
    def add_to_rotation(self, player):
        """Add a pitcher to the rotation"""
        if len(self.rotation) >= ROTATION_COUNT:
            return False
        
        # Remove from other slots first
        self.remove_player(player)
        
        self.rotation.append(player)
        return True
    
    def add_to_bullpen(self, player):
        """Add a pitcher to the bullpen"""
        if len(self.bullpen) >= BULLPEN_COUNT:
            return False
        
        # Remove from other slots first
        self.remove_player(player)
        
        self.bullpen.append(player)
        return True
    
    def remove_player(self, player):
        """Remove a player from all roster slots"""
        player_name = player.get("Name", "")
        
        # Check lineup
        for pos, p in self.lineup.items():
            if p and p.get("Name", "") == player_name:
                self.lineup[pos] = None
                return True
        
        # Check bench
        for i, p in enumerate(self.bench):
            if p.get("Name", "") == player_name:
                self.bench.pop(i)
                return True
        
        # Check rotation
        for i, p in enumerate(self.rotation):
            if p.get("Name", "") == player_name:
                self.rotation.pop(i)
                return True
        
        # Check bullpen
        for i, p in enumerate(self.bullpen):
            if p.get("Name", "") == player_name:
                self.bullpen.pop(i)
                return True
        
        return False
    
    def clear_roster(self):
        """Clear all roster slots"""
        self.lineup = {pos: None for pos in LINEUP_SLOTS}
        self.bench = []
        self.rotation = []
        self.bullpen = []
    
    def get_all_roster_players(self):
        """Get all players currently on the roster"""
        players = []
        
        for pos, player in self.lineup.items():
            if player:
                players.append({"player": player, "slot": pos, "type": "lineup"})
        
        for i, player in enumerate(self.bench):
            players.append({"player": player, "slot": f"BN{i+1}", "type": "bench"})
        
        for i, player in enumerate(self.rotation):
            players.append({"player": player, "slot": f"SP{i+1}", "type": "rotation"})
        
        for i, player in enumerate(self.bullpen):
            players.append({"player": player, "slot": f"RP{i+1}", "type": "bullpen"})
        
        return players
    
    def get_roster_summary(self):
        """
        Get summary statistics for the current roster.
        Returns dict with WAR, salary, age, OVR averages, and position grades.
        """
        all_players = self.get_all_roster_players()
        
        if not all_players:
            return {
                "total_war": 0,
                "total_salary": 0,
                "avg_age": 0,
                "avg_ovr": 0,
                "position_grades": {},
                "archetype_fit": None,
                "player_count": 0,
            }
        
        total_war = 0
        total_salary = 0
        total_age = 0
        total_ovr = 0
        count = 0
        
        # Track position-specific OVRs for grading
        position_ovrs = {
            "C": [],
            "1B": [],
            "2B": [],
            "3B": [],
            "SS": [],
            "OF": [],
            "SP": [],
            "RP": [],
        }
        
        for entry in all_players:
            player = entry["player"]
            slot_type = entry["type"]
            
            # Determine player type
            if slot_type in ["rotation", "bullpen"]:
                player_type = "pitcher"
            else:
                player_type = "batter"
            
            # Get WAR
            war = get_war(player, player_type)
            total_war += war
            
            # Get salary
            salary = parse_salary(player.get("SLR", 0))
            total_salary += salary
            
            # Get age
            age = get_age(player)
            total_age += age
            
            # Get OVR
            ovr = parse_star_rating(player.get("OVR", "0"))
            total_ovr += ovr
            count += 1
            
            # Track for position grades
            pos = player.get("POS", "")
            if pos == "C":
                position_ovrs["C"].append(ovr)
            elif pos == "1B":
                position_ovrs["1B"].append(ovr)
            elif pos == "2B":
                position_ovrs["2B"].append(ovr)
            elif pos == "3B":
                position_ovrs["3B"].append(ovr)
            elif pos == "SS":
                position_ovrs["SS"].append(ovr)
            elif pos in ["LF", "CF", "RF"]:
                position_ovrs["OF"].append(ovr)
            elif pos == "SP":
                position_ovrs["SP"].append(ovr)
            elif pos in ["RP", "CL"]:
                position_ovrs["RP"].append(ovr)
        
        # Calculate position grades
        position_grades = {}
        for pos_group, ovrs in position_ovrs.items():
            if ovrs:
                avg_ovr = sum(ovrs) / len(ovrs)
                grade_info = get_grade_for_ovr(avg_ovr)
                position_grades[pos_group] = grade_info
        
        # Detect best-fitting archetype based on roster composition
        archetype_fit = self._detect_roster_archetype()
        
        return {
            "total_war": round(total_war, 1),
            "total_salary": round(total_salary, 1),
            "avg_age": round(total_age / count, 1) if count else 0,
            "avg_ovr": round(total_ovr / count, 1) if count else 0,
            "position_grades": position_grades,
            "archetype_fit": archetype_fit,
            "player_count": count,
        }
    
    def _detect_roster_archetype(self):
        """
        Detect the overall archetype of the roster based on player composition.
        """
        all_players = self.get_all_roster_players()
        
        if len(all_players) < 5:
            return None
        
        # Count archetype fits
        archetype_counts = {key: 0 for key in ARCHETYPES.keys()}
        
        for entry in all_players:
            player = entry["player"]
            slot_type = entry["type"]
            player_type = "pitcher" if slot_type in ["rotation", "bullpen"] else "batter"
            
            best = get_best_archetype(player, player_type)
            if best and best["score"] >= 50:
                archetype_counts[best["archetype"]] += 1
        
        # Find dominant archetype
        if max(archetype_counts.values()) == 0:
            return None
        
        dominant = max(archetype_counts.items(), key=lambda x: x[1])
        archetype_info = ARCHETYPES.get(dominant[0], {})
        
        return {
            "archetype": dominant[0],
            "count": dominant[1],
            "name": archetype_info.get("name", dominant[0]),
            "icon": archetype_info.get("icon", ""),
        }
    
    def get_lineup_war(self):
        """Get total WAR from lineup players"""
        total = 0
        for pos, player in self.lineup.items():
            if player:
                total += get_war(player, "batter")
        return round(total, 1)
    
    def get_rotation_war(self):
        """Get total WAR from rotation"""
        total = 0
        for player in self.rotation:
            total += get_war(player, "pitcher")
        return round(total, 1)
    
    def get_bullpen_war(self):
        """Get total WAR from bullpen"""
        total = 0
        for player in self.bullpen:
            total += get_war(player, "pitcher")
        return round(total, 1)
    
    def is_player_on_roster(self, player):
        """Check if a player is currently on the roster"""
        player_name = player.get("Name", "")
        
        for pos, p in self.lineup.items():
            if p and p.get("Name", "") == player_name:
                return True
        
        for p in self.bench:
            if p.get("Name", "") == player_name:
                return True
        
        for p in self.rotation:
            if p.get("Name", "") == player_name:
                return True
        
        for p in self.bullpen:
            if p.get("Name", "") == player_name:
                return True
        
        return False
    
    def export_roster(self):
        """Export roster to a serializable format"""
        return {
            "lineup": {pos: p.get("Name") if p else None for pos, p in self.lineup.items()},
            "bench": [p.get("Name") for p in self.bench],
            "rotation": [p.get("Name") for p in self.rotation],
            "bullpen": [p.get("Name") for p in self.bullpen],
        }
    
    def import_roster(self, data):
        """Import roster from a serialized format"""
        self.clear_roster()
        
        # Create name lookup
        batter_lookup = {b.get("Name"): b for b in self._all_batters}
        pitcher_lookup = {p.get("Name"): p for p in self._all_pitchers}
        
        # Import lineup
        for pos, name in data.get("lineup", {}).items():
            if name and name in batter_lookup:
                self.lineup[pos] = batter_lookup[name]
        
        # Import bench
        for name in data.get("bench", []):
            if name and name in batter_lookup:
                self.bench.append(batter_lookup[name])
        
        # Import rotation
        for name in data.get("rotation", []):
            if name and name in pitcher_lookup:
                self.rotation.append(pitcher_lookup[name])
        
        # Import bullpen
        for name in data.get("bullpen", []):
            if name and name in pitcher_lookup:
                self.bullpen.append(pitcher_lookup[name])


def calculate_trade_availability(player, player_type="batter"):
    """
    Calculate trade availability score (1-10) for a player.
    
    Availability levels:
    - 1-3: Easily Acquired (low value, rebuilding team, blocked)
    - 4-6: Available for Right Price (medium value)
    - 7-8: Unlikely (high value, good team)
    - 9-10: Untouchable (elite, franchise cornerstone)
    """
    score = 5  # Start at middle
    
    # Trade value component
    ovr = parse_star_rating(player.get("OVR", "0"))
    pot = parse_star_rating(player.get("POT", "0"))
    
    # Normalize OVR and POT to 20-80 scale using shared utility
    ovr = normalize_rating(ovr)
    pot = normalize_rating(pot)
    
    # Higher OVR = less available
    if ovr >= 75:
        score += 3
    elif ovr >= 70:
        score += 2
    elif ovr >= 65:
        score += 1
    elif ovr < 50:
        score -= 2
    elif ovr < 55:
        score -= 1
    
    # Contract component
    yl_data = parse_years_left(player.get("YL", ""))
    years_left = yl_data.get("years", 1)
    status = yl_data.get("status", "unknown")
    
    # More years = less available
    if years_left >= 5:
        score += 2
    elif years_left >= 3:
        score += 1
    elif years_left <= 1:
        score -= 1
    
    # Pre-arb = more valuable = less available
    if status == "pre_arb" and ovr >= 60:
        score += 1
    
    # Age component
    age = get_age(player)
    if age >= 33:
        score -= 1  # Older = more available
    elif age <= 26 and pot >= 70:
        score += 1  # Young with upside = less available
    
    # Clamp to 1-10
    return max(1, min(10, score))


def get_availability_tier(score):
    """Get availability tier info for a score"""
    if score <= 3:
        return {
            "tier": "🟢 Easily Acquired",
            "color": "#51cf66",
            "description": "Low value, likely available",
        }
    elif score <= 6:
        return {
            "tier": "🟡 Available for Right Price",
            "color": "#ffd43b",
            "description": "Would cost assets to acquire",
        }
    elif score <= 8:
        return {
            "tier": "🟠 Unlikely",
            "color": "#ff922b",
            "description": "High value, would cost a lot",
        }
    else:
        return {
            "tier": "🔴 Untouchable",
            "color": "#ff6b6b",
            "description": "Franchise cornerstone",
        }


def find_trade_targets_by_position(batters, pitchers, position, min_ovr=None, max_age=None, max_availability=None):
    """
    Find all players at a given position, ranked by value and availability.
    
    Args:
        position: Position to search (C, 1B, 2B, 3B, SS, LF, CF, RF, DH, SP, RP)
        min_ovr: Minimum OVR filter (optional)
        max_age: Maximum age filter (optional)
        max_availability: Maximum availability score (lower = more available)
    """
    results = []
    
    # Determine if this is a pitcher or batter position
    is_pitcher = position in {"SP", "RP", "CL", "P"}
    
    players = pitchers if is_pitcher else batters
    player_type = "pitcher" if is_pitcher else "batter"
    
    for player in players:
        pos = player.get("POS", "")
        
        # Match position (RP and CL both count as RP)
        if position == "RP" and pos not in {"RP", "CL"}:
            continue
        elif position != "RP" and pos != position:
            continue
        
        ovr = parse_star_rating(player.get("OVR", "0"))
        age = get_age(player)
        
        # Apply filters
        if min_ovr is not None:
            # Normalize for comparison using shared utility
            compare_ovr = normalize_rating(ovr)
            if compare_ovr < min_ovr:
                continue
        
        if max_age is not None and age > max_age:
            continue
        
        # Calculate availability
        availability = calculate_trade_availability(player, player_type)
        
        if max_availability is not None and availability > max_availability:
            continue
        
        availability_tier = get_availability_tier(availability)
        
        results.append({
            "player": player,
            "name": player.get("Name", ""),
            "team": player.get("ORG", ""),
            "pos": pos,
            "age": age,
            "ovr": ovr,
            "pot": parse_star_rating(player.get("POT", "0")),
            "availability": availability,
            "availability_tier": availability_tier,
            "war": get_war(player, player_type),
            "salary": parse_salary(player.get("SLR", 0)),
        })
    
    # Sort by availability (most available first), then by OVR
    results.sort(key=lambda x: (x["availability"], -x["ovr"]))
    
    return results
