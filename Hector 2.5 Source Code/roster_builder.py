# Roster Builder Logic
# Handles roster building logic, grades, summaries, and archetype detection

import random

from trade_value import parse_number, parse_salary, parse_years_left
from archetypes import get_best_archetype, ARCHETYPES
from player_utils import (
    parse_star_rating, get_age, get_war, normalize_rating, STAR_TO_RATING_SCALE,
    normalize_to_100, apply_scouting_uncertainty, get_games_played, get_innings_pitched
)
from philosophy_profiles import (
    get_philosophy_profile, get_position_scarcity_score, is_premium_position,
    PHILOSOPHY_PROFILES, PRIME_YEARS_MIN, PRIME_YEARS_MAX
)
from batter_stat_weights import stat_weights as batter_stat_weights, normalization as batter_normalization, MIN_PLATE_APPEARANCES
from pitcher_stat_weights import stat_weights as pitcher_stat_weights, normalization as pitcher_normalization, MIN_INNINGS_PITCHED


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

# Auto-generate weight multipliers
ARCHETYPE_MATCH_WEIGHT_MULTIPLIER = 1.8  # Weight boost for matching archetype
ARCHETYPE_GOOD_FIT_MULTIPLIER = 1.2      # Weight boost for good archetype fit
MINIMUM_SELECTION_WEIGHT = 0.1           # Floor weight to allow surprises

# Composite scoring constants
RANDOMNESS_JITTER_SCALE = 10             # Scale factor for randomness jitter (score range is 0-100)
PRE_ARB_VALUE_BONUS = 10                 # Bonus points for pre-arb players in value efficiency scoring
ARBITRATION_VALUE_BONUS = 5              # Bonus points for arbitration players in value efficiency scoring

# Bench positions for auto-generate (utility-focused)
BENCH_POSITIONS = ["C", "1B", "2B", "SS", "LF", "CF", "RF"]


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
    
    def auto_generate_roster(self, competitive_level="Middle of the pack", 
                              salary_tier="Mid-market", identity="Any"):
        """
        Auto-generate a complete roster using weighted random selection.
        
        Args:
            competitive_level: "Contender", "Middle of the pack", or "Rebuilding"
            salary_tier: "Big spender", "Mid-market", or "Budget"
            identity: "Any", "Power-focused", "Speed-focused", "Pitching-focused", 
                     or archetype keys like "mashers", "speed_defense", etc.
        
        Each call produces a different roster due to weighted randomness.
        All three options (competitive_level, salary_tier, identity) are applied together.
        """
        self.clear_roster()
        
        # Track used players to avoid duplicates
        used_players = set()
        
        # Determine candidate pool size based on competitive level
        # Rebuilding/Budget teams need access to a much larger pool to find cheap/young players
        if competitive_level == "Rebuilding" or salary_tier == "Budget":
            candidate_count = 50  # Look through more players
        elif competitive_level == "Contender" or salary_tier == "Big spender":
            candidate_count = 20  # Still some variety for contenders
        else:
            candidate_count = 30  # Middle of the pack
        
        # Fill lineup positions
        for pos in LINEUP_SLOTS:
            candidates = self._get_position_candidates(pos, candidate_count, "batter", used_players,
                                                        competitive_level, salary_tier)
            if candidates:
                weights = self._calculate_weights(candidates, competitive_level, 
                                                   salary_tier, identity, "batter")
                selected = random.choices(candidates, weights=weights, k=1)[0]
                self.add_to_lineup(selected, pos)
                used_players.add(selected.get("Name", ""))
        
        # Fill rotation
        self._fill_rotation_random(competitive_level, salary_tier, identity, used_players)
        
        # Fill bullpen
        self._fill_bullpen_random(competitive_level, salary_tier, identity, used_players)
        
        # Fill bench
        self._fill_bench_random(competitive_level, salary_tier, identity, used_players)
    
    def _get_position_candidates(self, position, count, player_type, used_players,
                                  competitive_level="Middle of the pack", salary_tier="Mid-market"):
        """
        Get candidate players for a position, excluding already used players.
        The pool and sorting depends on competitive_level and salary_tier.
        
        Args:
            position: Position to find candidates for (C, 1B, SP, RP, etc.)
            count: Number of candidates to return
            player_type: "batter" or "pitcher"
            used_players: Set of player names already on roster
            competitive_level: "Contender", "Middle of the pack", or "Rebuilding"
            salary_tier: "Big spender", "Mid-market", or "Budget"
        
        Returns:
            List of player dicts - the sorting depends on team philosophy
        """
        candidates = []
        
        if player_type == "pitcher":
            pool = self._all_pitchers
        else:
            pool = self._all_batters
        
        for player in pool:
            # Skip already used players
            if player.get("Name", "") in used_players:
                continue
            
            player_pos = player.get("POS", "")
            
            # Match position
            if position == "RP":
                # RP slot accepts RP or CL
                if player_pos not in ["RP", "CL"]:
                    continue
            elif position == "DH":
                # DH can be any batter position
                pass
            else:
                if player_pos != position:
                    continue
            
            candidates.append(player)
        
        # Sort strategy depends on team philosophy - this affects which players 
        # make it into the candidate pool
        if competitive_level == "Rebuilding":
            # For rebuilding: prioritize young players with high potential
            # Sort by age (ascending) first, then by potential (descending)
            candidates.sort(key=lambda p: (
                get_age(p),  # Younger first
                -parse_star_rating(p.get("POT", "0"))  # Then high potential
            ))
        elif salary_tier == "Budget":
            # For budget: prioritize low salary players
            # Sort by salary (ascending), then by OVR (descending)
            candidates.sort(key=lambda p: (
                parse_salary(p.get("SLR", 0)),  # Cheaper first
                -parse_star_rating(p.get("OVR", "0"))  # Then high OVR within salary tier
            ))
        elif competitive_level == "Contender" or salary_tier == "Big spender":
            # For contenders: prioritize high OVR players
            candidates.sort(key=lambda p: parse_star_rating(p.get("OVR", "0")), reverse=True)
        else:
            # Middle of the pack: mix of OVR and value
            # Sort by a blend of OVR and age (prefer prime-age players)
            def middle_sort_key(p):
                ovr = parse_star_rating(p.get("OVR", "0"))
                age = get_age(p)
                # Prefer players aged 25-30 (prime years)
                age_bonus = 0
                if 25 <= age <= 30:
                    age_bonus = 10
                elif 23 <= age <= 32:
                    age_bonus = 5
                return ovr + age_bonus
            candidates.sort(key=middle_sort_key, reverse=True)
        
        return candidates[:count]
    
    def _calculate_weights(self, candidates, competitive_level, salary_tier, 
                           identity, player_type):
        """
        Calculate selection weights for candidate players.
        
        Weights are influenced by:
        - Competitive level (favors high OVR for contenders, youth for rebuilding)
        - Salary tier (favors budget contracts or allows premium spending)
        - Identity (boosts players matching requested archetype)
        
        All three factors are combined multiplicatively, so selecting 
        "Rebuilding" + "Budget" + "Youth-focused" will strongly favor 
        young, cheap players with high potential.
        
        Returns:
            List of weights corresponding to each candidate
        """
        weights = []
        
        for player in candidates:
            weight = 1.0
            
            # Get player attributes
            ovr = parse_star_rating(player.get("OVR", "0"))
            ovr_normalized = normalize_rating(ovr)
            pot = parse_star_rating(player.get("POT", "0"))
            pot_normalized = normalize_rating(pot)
            age = get_age(player)
            salary = parse_salary(player.get("SLR", 0))
            
            # Competitive level adjustments
            if competitive_level == "Contender":
                # Strongly favor high OVR players, penalize low OVR
                if ovr_normalized >= 75:
                    weight *= 4.0
                elif ovr_normalized >= 70:
                    weight *= 3.0
                elif ovr_normalized >= 65:
                    weight *= 2.0
                elif ovr_normalized >= 60:
                    weight *= 1.5
                elif ovr_normalized < 55:
                    weight *= 0.3  # Stronger penalty for weak players
                elif ovr_normalized < 50:
                    weight *= 0.1
            elif competitive_level == "Rebuilding":
                # Strongly favor younger players with upside, penalize older players
                if age <= 23:
                    weight *= 3.0  # Strongest boost for very young
                elif age <= 25:
                    weight *= 2.5
                elif age <= 27:
                    weight *= 1.5
                elif age >= 33:
                    weight *= 0.1  # Strong penalty for old players
                elif age >= 30:
                    weight *= 0.3
                # Favor high potential
                if pot_normalized >= 75:
                    weight *= 2.5
                elif pot_normalized >= 70:
                    weight *= 2.0
                elif pot_normalized >= 65:
                    weight *= 1.5
                elif pot_normalized >= 60:
                    weight *= 1.2
                # Slight penalty for high OVR (want players not yet at peak)
                if ovr_normalized >= 75:
                    weight *= 0.7
            # "Middle of the pack" uses balanced weights (no major adjustments)
            # but still applies salary and identity modifiers
            
            # Salary tier adjustments
            if salary_tier == "Budget":
                # Strongly reduce weight for high-salary players
                if salary >= 25:
                    weight *= 0.05  # Almost never pick $25M+ players
                elif salary >= 15:
                    weight *= 0.15
                elif salary >= 10:
                    weight *= 0.3
                elif salary >= 5:
                    weight *= 0.6
                elif salary <= 1:
                    weight *= 2.5  # Strong boost for minimum salary
                elif salary <= 3:
                    weight *= 1.8
            elif salary_tier == "Big spender":
                # Boost for star players (who tend to be expensive)
                if ovr_normalized >= 75:
                    weight *= 2.0
                elif ovr_normalized >= 70:
                    weight *= 1.5
                elif ovr_normalized >= 65:
                    weight *= 1.2
            # "Mid-market" uses balanced approach (no major salary adjustments)
            
            # Identity/archetype adjustments
            if identity and identity not in ["Any", "Balanced"]:
                archetype_key = self._map_identity_to_archetype(identity)
                if archetype_key:
                    best = get_best_archetype(player, player_type)
                    if best and best["archetype"] == archetype_key:
                        # Strong boost for matching archetype
                        weight *= ARCHETYPE_MATCH_WEIGHT_MULTIPLIER
                    elif best and best["score"] >= 60:
                        # Moderate boost for good archetype fit (any archetype)
                        weight *= ARCHETYPE_GOOD_FIT_MULTIPLIER
            
            # Ensure minimum weight (allow surprises)
            weight = max(MINIMUM_SELECTION_WEIGHT, weight)
            weights.append(weight)
        
        return weights
    
    def _map_identity_to_archetype(self, identity):
        """Map user-friendly identity names to archetype keys."""
        identity_map = {
            "Power-focused": "mashers",
            "Speed-focused": "speed_defense",
            "Pitching-focused": "win_now",  # Pitching focus uses win_now for quality
            "Youth-focused": "youth_movement",
            "Budget-focused": "budget_build",
            "OBP-focused": "moneyball",
            # Direct archetype keys also work
            "mashers": "mashers",
            "speed_defense": "speed_defense",
            "moneyball": "moneyball",
            "youth_movement": "youth_movement",
            "win_now": "win_now",
            "budget_build": "budget_build",
            "balanced": "balanced",
        }
        return identity_map.get(identity, None)
    
    def _fill_rotation_random(self, competitive_level, salary_tier, identity, used_players):
        """Fill rotation slots with weighted random selection."""
        # Determine candidate pool size based on competitive level
        if competitive_level == "Rebuilding" or salary_tier == "Budget":
            candidate_count = 30
        elif competitive_level == "Contender" or salary_tier == "Big spender":
            candidate_count = 15
        else:
            candidate_count = 20
            
        for _ in range(ROTATION_COUNT):
            if len(self.rotation) >= ROTATION_COUNT:
                break
            
            candidates = self._get_position_candidates("SP", candidate_count, "pitcher", used_players,
                                                        competitive_level, salary_tier)
            if candidates:
                weights = self._calculate_weights(candidates, competitive_level, 
                                                   salary_tier, identity, "pitcher")
                selected = random.choices(candidates, weights=weights, k=1)[0]
                self.add_to_rotation(selected)
                used_players.add(selected.get("Name", ""))
    
    def _fill_bullpen_random(self, competitive_level, salary_tier, identity, used_players):
        """Fill bullpen slots with weighted random selection."""
        # Determine candidate pool size based on competitive level
        if competitive_level == "Rebuilding" or salary_tier == "Budget":
            candidate_count = 40
        elif competitive_level == "Contender" or salary_tier == "Big spender":
            candidate_count = 20
        else:
            candidate_count = 25
            
        for _ in range(BULLPEN_COUNT):
            if len(self.bullpen) >= BULLPEN_COUNT:
                break
            
            candidates = self._get_position_candidates("RP", candidate_count, "pitcher", used_players,
                                                        competitive_level, salary_tier)
            if candidates:
                weights = self._calculate_weights(candidates, competitive_level, 
                                                   salary_tier, identity, "pitcher")
                selected = random.choices(candidates, weights=weights, k=1)[0]
                self.add_to_bullpen(selected)
                used_players.add(selected.get("Name", ""))
    
    def _fill_bench_random(self, competitive_level, salary_tier, identity, used_players):
        """Fill bench slots with weighted random selection, preferring versatile players."""
        # Determine candidate pool size based on competitive level
        if competitive_level == "Rebuilding" or salary_tier == "Budget":
            candidate_count = 15
        elif competitive_level == "Contender" or salary_tier == "Big spender":
            candidate_count = 8
        else:
            candidate_count = 10
            
        for i in range(BENCH_COUNT):
            if len(self.bench) >= BENCH_COUNT:
                break
            
            # Rotate through preferred bench positions
            preferred_pos = BENCH_POSITIONS[i % len(BENCH_POSITIONS)]
            
            # Get candidates - for bench, be more flexible with positions
            all_candidates = []
            for pos in LINEUP_SLOTS:
                if pos == "DH":
                    continue  # Skip DH for bench
                candidates = self._get_position_candidates(pos, candidate_count, "batter", used_players,
                                                            competitive_level, salary_tier)
                all_candidates.extend(candidates)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_candidates = []
            for c in all_candidates:
                name = c.get("Name", "")
                if name not in seen:
                    seen.add(name)
                    unique_candidates.append(c)
            
            if unique_candidates:
                weights = self._calculate_weights(unique_candidates, competitive_level, 
                                                   salary_tier, identity, "batter")
                selected = random.choices(unique_candidates, weights=weights, k=1)[0]
                self.add_to_bench(selected)
                used_players.add(selected.get("Name", ""))
    
    # ========================================================================
    # Philosophy-Based Roster Generation (v2)
    # ========================================================================
    
    def auto_generate_roster_v2(self, philosophy="balanced", constraints=None,
                                num_alternates=1, randomness=0.15):
        """
        Generate roster(s) using philosophy-weighted optimization.
        
        Args:
            philosophy: Philosophy profile name or custom weights dict
            constraints: Override constraints (budget, age limits, etc.)
            num_alternates: Number of alternate rosters to generate
            randomness: Noise factor (0-1) to introduce variety between runs
        
        Returns:
            List of roster builds with scores and summaries
        """
        profile = get_philosophy_profile(philosophy)
        
        # Merge constraints with profile constraints
        merged_constraints = profile.get("constraints", {}).copy()
        if constraints:
            merged_constraints.update(constraints)
        
        results = []
        
        for i in range(num_alternates):
            # Clear roster for each alternate
            self.clear_roster()
            
            # Track used players
            used_players = set()
            
            # Score all players upfront
            batter_scores = self._score_all_players(
                self._all_batters, "batter", profile, merged_constraints, randomness
            )
            pitcher_scores = self._score_all_players(
                self._all_pitchers, "pitcher", profile, merged_constraints, randomness
            )
            
            # Fill lineup positions by selecting best available
            for pos in LINEUP_SLOTS:
                best = self._select_best_for_position(
                    pos, batter_scores, used_players, merged_constraints
                )
                if best:
                    self.add_to_lineup(best, pos)
                    used_players.add(best.get("Name", ""))
            
            # Fill rotation
            for _ in range(ROTATION_COUNT):
                if len(self.rotation) >= ROTATION_COUNT:
                    break
                best = self._select_best_for_position(
                    "SP", pitcher_scores, used_players, merged_constraints
                )
                if best:
                    self.add_to_rotation(best)
                    used_players.add(best.get("Name", ""))
            
            # Fill bullpen
            for _ in range(BULLPEN_COUNT):
                if len(self.bullpen) >= BULLPEN_COUNT:
                    break
                best = self._select_best_for_position(
                    "RP", pitcher_scores, used_players, merged_constraints
                )
                if best:
                    self.add_to_bullpen(best)
                    used_players.add(best.get("Name", ""))
            
            # Fill bench
            for _ in range(BENCH_COUNT):
                if len(self.bench) >= BENCH_COUNT:
                    break
                best = self._select_best_for_bench(
                    batter_scores, used_players, merged_constraints
                )
                if best:
                    self.add_to_bench(best)
                    used_players.add(best.get("Name", ""))
            
            # Get roster summary and calculate overall score
            summary = self.get_roster_summary()
            roster_score = self._calculate_roster_score(profile)
            
            results.append({
                "roster": self.export_roster(),
                "summary": summary,
                "score": roster_score,
                "philosophy": profile["name"],
                "constraints_applied": merged_constraints,
            })
        
        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # If only one roster requested, import it back
        if num_alternates == 1 and results:
            self.import_roster(results[0]["roster"])
        
        return results
    
    def _score_all_players(self, players, player_type, profile, constraints, randomness):
        """
        Score all players using composite scoring.
        
        Returns dict of player_name -> {player, score, component_scores}
        """
        scores = {}
        
        for player in players:
            # Apply hard constraints first
            if not self._meets_constraints(player, player_type, constraints):
                continue
            
            # Calculate composite score
            composite, components = self.calculate_composite_score(
                player, player_type, profile
            )
            
            # Apply randomness jitter
            if randomness > 0:
                jitter = random.gauss(0, randomness * RANDOMNESS_JITTER_SCALE)
                composite = max(0, min(100, composite + jitter))
            
            name = player.get("Name", "")
            scores[name] = {
                "player": player,
                "score": composite,
                "components": components,
            }
        
        return scores
    
    def _meets_constraints(self, player, player_type, constraints):
        """Check if a player meets the hard constraints."""
        if not constraints:
            return True
        
        age = get_age(player)
        salary = parse_salary(player.get("SLR", 0))
        yl_data = parse_years_left(player.get("YL", ""))
        status = yl_data.get("status", "unknown")
        
        # Max age constraint
        if "max_age" in constraints:
            if age > constraints["max_age"]:
                return False
        
        # Max salary per player constraint
        if "max_salary_per_player" in constraints:
            if salary > constraints["max_salary_per_player"]:
                return False
        
        # Prefer pre-arb constraint (soft, but implemented as harder filter)
        if constraints.get("prefer_pre_arb"):
            # Don't exclude, but this is handled in scoring with preference
            pass
        
        return True
    
    def _select_best_for_position(self, position, player_scores, used_players, constraints):
        """
        Select the best available player for a position.
        
        Args:
            position: Position to fill (C, 1B, SP, RP, etc.)
            player_scores: Dict of scored players
            used_players: Set of already used player names
            constraints: Constraint dict
        
        Returns:
            Best available player dict or None
        """
        candidates = []
        
        for name, data in player_scores.items():
            if name in used_players:
                continue
            
            player = data["player"]
            player_pos = player.get("POS", "")
            
            # Match position
            if position == "RP":
                if player_pos not in ["RP", "CL"]:
                    continue
            elif position == "DH":
                # DH can be any batter
                pass
            else:
                if player_pos != position:
                    continue
            
            candidates.append((data["score"], player))
        
        if not candidates:
            return None
        
        # Sort by score descending and return the best
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    
    def _select_best_for_bench(self, player_scores, used_players, constraints):
        """
        Select the best available player for bench.
        Prefers utility players who can play multiple positions.
        """
        candidates = []
        
        for name, data in player_scores.items():
            if name in used_players:
                continue
            
            player = data["player"]
            player_pos = player.get("POS", "")
            
            # Skip DH for bench
            if player_pos == "DH":
                continue
            
            # Valid bench positions
            if player_pos in LINEUP_SLOTS or player_pos in ["LF", "CF", "RF"]:
                candidates.append((data["score"], player))
        
        if not candidates:
            return None
        
        # Sort by score descending and return the best
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    
    def _calculate_roster_score(self, profile):
        """Calculate overall roster score based on philosophy weights."""
        all_players = self.get_all_roster_players()
        
        if not all_players:
            return 0
        
        total_score = 0
        for entry in all_players:
            player = entry["player"]
            slot_type = entry["type"]
            player_type = "pitcher" if slot_type in ["rotation", "bullpen"] else "batter"
            
            score, _ = self.calculate_composite_score(player, player_type, profile)
            total_score += score
        
        # Return average score
        return round(total_score / len(all_players), 1)
    
    def calculate_composite_score(self, player, player_type, profile):
        """
        Calculate composite score for a player using philosophy weights.
        
        Args:
            player: Player dict
            player_type: "batter" or "pitcher"
            profile: Philosophy profile dict with weights
        
        Returns:
            Tuple of (composite_score, component_scores_dict)
        """
        weights = profile.get("weights", {})
        
        # Calculate individual component scores
        stats_score = self._score_current_stats(player, player_type)
        ratings_score = self._score_current_ratings(player)
        potential_score = self._score_potential(player)
        value_score = self._score_value_efficiency(player, player_type)
        age_score = self._score_age_curve(player, profile)
        position = player.get("POS", "")
        scarcity_score = self._score_positional_scarcity(player, position, player_type)
        
        components = {
            "current_stats": stats_score,
            "current_ratings": ratings_score,
            "potential": potential_score,
            "value_efficiency": value_score,
            "age_curve": age_score,
            "positional_scarcity": scarcity_score,
        }
        
        # Calculate weighted composite
        composite = 0
        for key, component_score in components.items():
            weight = weights.get(key, 0)
            composite += component_score * weight
        
        return round(composite, 2), components
    
    def _score_current_stats(self, player, player_type):
        """
        Score player based on current stats.
        Uses wRC+, WAR, OPS+ for batters; ERA+, WAR for pitchers.
        Falls back to ratings for limited sample size.
        
        Returns score 0-100.
        """
        if player_type == "batter":
            games = get_games_played(player, "batter")
            
            # Check sample size (games played used as proxy for plate appearances)
            if games < MIN_PLATE_APPEARANCES:
                # Fall back to ratings-based scoring
                return self._score_current_ratings(player)
            
            # Calculate stats-based score
            score = 0
            total_weight = 0
            
            # wRC+ (30% weight from batter_stat_weights)
            wrc_plus = parse_number(player.get("wRC+", 100))
            wrc_norm = batter_normalization.get("wRC+", {})
            wrc_score = normalize_to_100(
                wrc_plus, 
                wrc_norm.get("min", 50), 
                wrc_norm.get("max", 180)
            )
            weight = batter_stat_weights.get("wRC+", {}).get("weight", 0.30)
            score += wrc_score * weight
            total_weight += weight
            
            # WAR (30% weight)
            war = get_war(player, "batter")
            war_norm = batter_normalization.get("WAR (Batter)", {})
            war_score = normalize_to_100(
                war,
                war_norm.get("min", -2.0),
                war_norm.get("max", 8.0)
            )
            weight = batter_stat_weights.get("WAR (Batter)", {}).get("weight", 0.30)
            score += war_score * weight
            total_weight += weight
            
            # OPS+ (15% weight)
            ops_plus = parse_number(player.get("OPS+", 100))
            ops_norm = batter_normalization.get("OPS+", {})
            ops_score = normalize_to_100(
                ops_plus,
                ops_norm.get("min", 50),
                ops_norm.get("max", 180)
            )
            weight = batter_stat_weights.get("OPS+", {}).get("weight", 0.15)
            score += ops_score * weight
            total_weight += weight
            
            # Normalize by total weight to get 0-100 scale
            if total_weight > 0:
                score = score / total_weight
            
            return min(100, max(0, score))
        
        else:  # pitcher
            ip = get_innings_pitched(player)
            
            # Check sample size
            if ip < MIN_INNINGS_PITCHED:
                return self._score_current_ratings(player)
            
            score = 0
            total_weight = 0
            
            # ERA+ (30% weight)
            era_plus = parse_number(player.get("ERA+", 100))
            era_norm = pitcher_normalization.get("ERA+", {})
            era_score = normalize_to_100(
                era_plus,
                era_norm.get("min", 50),
                era_norm.get("max", 200)
            )
            weight = pitcher_stat_weights.get("ERA+", {}).get("weight", 0.30)
            score += era_score * weight
            total_weight += weight
            
            # WAR (30% weight)
            war = get_war(player, "pitcher")
            war_norm = pitcher_normalization.get("WAR (Pitcher)", {})
            war_score = normalize_to_100(
                war,
                war_norm.get("min", -2.0),
                war_norm.get("max", 8.0)
            )
            weight = pitcher_stat_weights.get("WAR (Pitcher)", {}).get("weight", 0.30)
            score += war_score * weight
            total_weight += weight
            
            if total_weight > 0:
                score = score / total_weight
            
            return min(100, max(0, score))
    
    def _score_current_ratings(self, player):
        """
        Score player based on current OVR rating.
        Normalizes to 0-100 scale.
        
        Returns score 0-100.
        """
        ovr = parse_star_rating(player.get("OVR", "0"))
        ovr_normalized = normalize_rating(ovr)
        
        # Map 20-80 scale to 0-100
        # 20 = 0, 80 = 100
        score = normalize_to_100(ovr_normalized, 20, 80)
        return min(100, max(0, score))
    
    def _score_potential(self, player):
        """
        Score player based on POT rating and upside gap.
        Blends POT with (POT - OVR) gap.
        
        Returns score 0-100.
        """
        pot = parse_star_rating(player.get("POT", "0"))
        ovr = parse_star_rating(player.get("OVR", "0"))
        
        pot_normalized = normalize_rating(pot)
        ovr_normalized = normalize_rating(ovr)
        
        # POT component (70% of potential score)
        pot_score = normalize_to_100(pot_normalized, 20, 80)
        
        # Upside gap component (30% of potential score)
        # Gap range: -20 to +30 (negative means OVR > POT, rare)
        upside_gap = pot_normalized - ovr_normalized
        gap_score = normalize_to_100(upside_gap, -20, 30)
        
        # Blend
        score = (pot_score * 0.7) + (gap_score * 0.3)
        return min(100, max(0, score))
    
    def _score_value_efficiency(self, player, player_type):
        """
        Score player based on WAR/$ ratio.
        Higher WAR per dollar = better value.
        
        Returns score 0-100.
        """
        war = get_war(player, player_type)
        salary = parse_salary(player.get("SLR", 0))
        
        # Handle edge cases
        if salary <= 0:
            # Pre-arb or minimum salary - excellent value if positive WAR
            if war >= 2.0:
                return 100
            elif war >= 1.0:
                return 85
            elif war >= 0:
                return 70
            else:
                return 30
        
        # Calculate WAR per million dollars
        war_per_million = war / salary
        
        # Normalize: 0 $/WAR = 0, 2+ WAR/$ = 100
        # Typical range: -0.5 to 2.0 WAR/$
        score = normalize_to_100(war_per_million, -0.5, 2.0)
        
        # Bonus for pre-arb/arb status
        yl_data = parse_years_left(player.get("YL", ""))
        status = yl_data.get("status", "unknown")
        
        if status == "pre_arb":
            score = min(100, score + PRE_ARB_VALUE_BONUS)
        elif status == "arbitration":
            score = min(100, score + ARBITRATION_VALUE_BONUS)
        
        return min(100, max(0, score))
    
    def _score_age_curve(self, player, profile):
        """
        Score player based on age relative to philosophy preferences.
        
        Returns score 0-100.
        """
        age = get_age(player)
        
        if age <= 0:
            return 50  # Unknown age, neutral score
        
        age_prefs = profile.get("age_preferences", {})
        ideal_min = age_prefs.get("ideal_min", PRIME_YEARS_MIN)
        ideal_max = age_prefs.get("ideal_max", PRIME_YEARS_MAX)
        acceptable_min = age_prefs.get("acceptable_min", 22)
        acceptable_max = age_prefs.get("acceptable_max", 33)
        
        # Ideal age range = 100
        if ideal_min <= age <= ideal_max:
            return 100
        
        # Acceptable range outside ideal = scaled score
        if acceptable_min <= age < ideal_min:
            # Between acceptable and ideal min
            distance = ideal_min - age
            range_size = ideal_min - acceptable_min
            if range_size > 0:
                return 100 - (distance / range_size) * 30  # 70-100
            return 85
        
        if ideal_max < age <= acceptable_max:
            # Between ideal max and acceptable max
            distance = age - ideal_max
            range_size = acceptable_max - ideal_max
            if range_size > 0:
                return 100 - (distance / range_size) * 30  # 70-100
            return 85
        
        # Outside acceptable range = lower scores
        if age < acceptable_min:
            # Too young
            distance = acceptable_min - age
            return max(30, 70 - distance * 10)
        
        if age > acceptable_max:
            # Too old
            distance = age - acceptable_max
            return max(10, 70 - distance * 15)
        
        return 50
    
    def _score_positional_scarcity(self, player, position, player_type):
        """
        Score player based on positional scarcity.
        Premium positions (C, SS, CF for batters; SP for pitchers) get bonus.
        
        Returns score 0-100.
        """
        # Base score of 50
        base_score = 50
        
        # Get scarcity multiplier from philosophy_profiles
        scarcity_mult = get_position_scarcity_score(position)
        
        # Scale: 0.85 -> 35, 1.0 -> 50, 1.15 -> 65
        # Formula: base + (mult - 1.0) * 100
        score = base_score + (scarcity_mult - 1.0) * 100
        
        # Additional bonus for premium positions
        if is_premium_position(position, player_type):
            score += 15
        
        return min(100, max(0, score))


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
