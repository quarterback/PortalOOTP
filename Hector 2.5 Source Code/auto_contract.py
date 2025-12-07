# Autocontract Generator
# Generates realistic competing contract offers for free agents based on performance data

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
import random
from trade_value import parse_number, parse_salary
from player_utils import get_war, parse_star_rating


class TeamArchetype(Enum):
    """Team archetypes that influence bidding behavior"""
    DYNASTY = "dynasty"           # Will pay premium to keep core (1.15-1.35x multiplier)
    CONTENDER = "contender"       # Aggressive on impact players (1.05-1.25x)
    WINDOW_BUILDER = "window"     # Selective spending on fits (0.90-1.10x)
    REBUILDING = "rebuilding"     # Value deals only (0.70-0.90x)
    TANKING = "tanking"          # Minimum viable contracts (0.50-0.75x)


@dataclass
class ContractOffer:
    """Represents a contract offer from a team"""
    team_archetype: TeamArchetype
    aav: float  # Average Annual Value in millions
    years: int
    total_value: float
    hometown_discount: bool = False
    notes: str = ""


@dataclass
class PlayerContractInput:
    """Input data for contract generation"""
    name: str
    age: int
    position: str
    war: float
    wrc_plus: Optional[float] = None  # For batters
    era_plus: Optional[float] = None  # For pitchers
    ovr_rating: Optional[int] = None
    years_with_team: int = 0
    is_international: bool = False
    projected_war: Optional[float] = None  # For international players


def calculate_market_dollar_per_war(players):
    """
    Calculate actual $/WAR from loaded Player List.html data.
    
    Args:
        players: List of player dicts with WAR and salary data
    
    Returns:
        Median $/WAR value across all meaningful contracts
    """
    war_salary_pairs = []
    
    for p in players:
        # Determine player type
        pos = p.get("POS", "").upper()
        player_type = "pitcher" if pos in ["SP", "RP", "CL", "P"] else "batter"
        
        # Get WAR value
        war = get_war(p, player_type)
        
        # Get salary value
        salary = parse_salary(p.get("SLR", 0))
        
        # Only include meaningful contracts (productive players with real salaries)
        if war > 0.5 and salary > 0.5:
            war_salary_pairs.append((war, salary))
    
    if not war_salary_pairs:
        return 8.0  # Fallback default (typical MLB market rate)
    
    # Calculate median $/WAR to avoid outlier skew
    ratios = [sal / war for war, sal in war_salary_pairs]
    ratios.sort()
    median_index = len(ratios) // 2
    
    return ratios[median_index]


def calculate_ovr_percentile(player_ovr, free_agent_pool):
    """
    Calculate a player's percentile rank within the free agent pool based on OVR.
    
    Args:
        player_ovr: The player's OVR rating (int or float)
        free_agent_pool: List of player dicts from the free agent pool
    
    Returns:
        Percentile rank (0-100) where 100 is the best player in the pool
    """
    if not free_agent_pool:
        return 50.0  # Default to median if no pool data
    
    # Extract OVR values from all players in the pool
    pool_ovr_values = []
    for player in free_agent_pool:
        ovr = parse_star_rating(player.get("OVR", 0))
        if ovr > 0:
            pool_ovr_values.append(ovr)
    
    if not pool_ovr_values:
        return 50.0  # Default to median if no valid OVR data
    
    # Count how many players have OVR less than the player's OVR
    players_below = sum(1 for ovr in pool_ovr_values if ovr < player_ovr)
    
    # Calculate percentile
    percentile = (players_below / len(pool_ovr_values)) * 100
    
    return percentile


def war_from_percentile(percentile):
    """
    Convert a percentile rank to an estimated WAR value.
    
    Uses a curve that maps percentile to WAR:
    - 99th percentile = ~6 WAR (elite)
    - 90th percentile = ~4 WAR (star)
    - 75th percentile = ~2.5 WAR (solid)
    - 50th percentile = ~1 WAR (average)
    - 25th percentile = ~0.5 WAR (below average)
    - 10th percentile = ~0.2 WAR (replacement level)
    
    Args:
        percentile: Percentile rank (0-100)
    
    Returns:
        Estimated WAR value
    """
    # Clamp percentile to valid range
    percentile = max(0.0, min(100.0, percentile))
    
    # Use a non-linear curve for WAR mapping
    # Higher percentiles get exponentially higher WAR
    if percentile >= 99:
        return 6.0
    elif percentile >= 95:
        # 95-99: 4.5-6 WAR
        return 4.5 + ((percentile - 95) / 4) * 1.5
    elif percentile >= 90:
        # 90-95: 4-4.5 WAR
        return 4.0 + ((percentile - 90) / 5) * 0.5
    elif percentile >= 75:
        # 75-90: 2.5-4 WAR
        return 2.5 + ((percentile - 75) / 15) * 1.5
    elif percentile >= 50:
        # 50-75: 1-2.5 WAR
        return 1.0 + ((percentile - 50) / 25) * 1.5
    elif percentile >= 25:
        # 25-50: 0.5-1 WAR
        return 0.5 + ((percentile - 25) / 25) * 0.5
    elif percentile >= 10:
        # 10-25: 0.2-0.5 WAR
        return 0.2 + ((percentile - 10) / 15) * 0.3
    else:
        # 0-10: 0-0.2 WAR
        return (percentile / 10) * 0.2


def calculate_contract_years(age):
    """
    Calculate contract years based on player age.
    
    Age brackets:
    - Age ≤ 26: 5-7 years
    - Age 27-29: 4-6 years
    - Age 30-32: 2-4 years
    - Age 33-35: 1-2 years
    - Age 36+: 1 year
    
    Returns tuple (min_years, max_years)
    """
    if age <= 26:
        return (5, 7)
    elif age <= 29:
        return (4, 6)
    elif age <= 32:
        return (2, 4)
    elif age <= 35:
        return (1, 2)
    else:
        return (1, 1)


def get_archetype_multiplier(archetype: TeamArchetype):
    """
    Get the bidding multiplier range for a team archetype.
    
    Returns tuple (min_multiplier, max_multiplier)
    """
    multipliers = {
        TeamArchetype.DYNASTY: (1.15, 1.35),
        TeamArchetype.CONTENDER: (1.05, 1.25),
        TeamArchetype.WINDOW_BUILDER: (0.90, 1.10),
        TeamArchetype.REBUILDING: (0.70, 0.90),
        TeamArchetype.TANKING: (0.50, 0.75),
    }
    return multipliers[archetype]


def generate_contract_offers(
    player_input: PlayerContractInput,
    dollar_per_war: float,
    eye_test_weight: float = 0.15,
    market_randomness: float = 0.15,
    hometown_discount_pct: float = 0.10,
    num_bidding_teams: int = 5,
    team_archetypes: List[TeamArchetype] = None,
    league_scale_multiplier: float = 1.0,
) -> List[ContractOffer]:
    """
    Generate competing contract offers for a free agent.
    
    Args:
        player_input: PlayerContractInput with player data
        dollar_per_war: Market $/WAR baseline
        eye_test_weight: Weight for OVR ratings (0-0.30)
        market_randomness: Variance in offers (0.10-0.30)
        hometown_discount_pct: Hometown discount percentage (0.05-0.15)
        num_bidding_teams: Number of teams bidding (1-8)
        team_archetypes: List of archetypes that should bid (default: all)
        league_scale_multiplier: Multiplier for all contract values (0.1-3.0)
    
    Returns:
        List of ContractOffer objects sorted by total value (descending)
    """
    if team_archetypes is None:
        team_archetypes = list(TeamArchetype)
    
    # Ensure we have enough archetypes for the number of teams
    if len(team_archetypes) < num_bidding_teams:
        # Cycle through available archetypes
        team_archetypes = team_archetypes * ((num_bidding_teams // len(team_archetypes)) + 1)
    
    # Randomly select archetypes for bidding teams
    random.shuffle(team_archetypes)
    selected_archetypes = team_archetypes[:num_bidding_teams]
    
    # Calculate base WAR value
    if player_input.is_international and player_input.projected_war is not None:
        base_war = player_input.projected_war
        # Higher randomness for international players
        market_randomness = max(market_randomness, 0.25)
    else:
        base_war = player_input.war
    
    # Apply stats adjustment
    stats_adjustment = 1.0
    if player_input.wrc_plus is not None:
        # For batters, adjust based on wRC+ (100 = league average)
        stats_adjustment = player_input.wrc_plus / 100.0
    elif player_input.era_plus is not None:
        # For pitchers, adjust based on ERA+ (100 = league average)
        stats_adjustment = player_input.era_plus / 100.0
    
    # Apply eye test weight (OVR ratings)
    if player_input.ovr_rating is not None and eye_test_weight > 0:
        # Normalize OVR to a multiplier (assuming 20-80 scale or 1-5 star scale)
        ovr = player_input.ovr_rating
        if ovr <= 10:
            # Star scale (1-5 or 1-10), normalize to multiplier
            ovr_multiplier = ovr / 5.0
        else:
            # 20-80 scale, normalize to multiplier (50 = 1.0)
            ovr_multiplier = ovr / 50.0
        
        # Blend WAR-based and OVR-based valuation
        war_weight = 1.0 - eye_test_weight
        adjusted_war = (base_war * stats_adjustment * war_weight) + (base_war * ovr_multiplier * eye_test_weight)
    else:
        adjusted_war = base_war * stats_adjustment
    
    # Calculate base AAV
    base_aav = adjusted_war * dollar_per_war
    
    # Ensure minimum viable AAV (at least league minimum for MLB ~$0.7M)
    base_aav = max(base_aav, 0.7)
    
    offers = []
    
    for archetype in selected_archetypes:
        # Get archetype multiplier
        min_mult, max_mult = get_archetype_multiplier(archetype)
        archetype_mult = random.uniform(min_mult, max_mult)
        
        # Apply market randomness
        randomness_mult = random.uniform(1.0 - market_randomness, 1.0 + market_randomness)
        
        # Calculate offer AAV
        offer_aav = base_aav * archetype_mult * randomness_mult
        
        # Apply league scale multiplier
        offer_aav = offer_aav * league_scale_multiplier
        
        # Determine contract years
        min_years, max_years = calculate_contract_years(player_input.age)
        
        # Adjust years based on archetype
        if archetype == TeamArchetype.DYNASTY:
            # Dynasty teams prefer longer deals
            years = max_years
        elif archetype == TeamArchetype.TANKING:
            # Tanking teams prefer short deals
            years = min_years
        else:
            # Other archetypes vary
            years = random.randint(min_years, max_years)
        
        # Special handling for international players
        if player_input.is_international:
            # Default to shorter contracts (2-4 years)
            years = random.randint(2, 4)
        
        # Calculate total value
        total_value = offer_aav * years
        
        # Generate notes
        notes = f"{archetype.value.title()}"
        if archetype_mult > 1.1:
            notes += " (paying premium)"
        elif archetype_mult < 0.9:
            notes += " (value seeking)"
        
        offers.append(ContractOffer(
            team_archetype=archetype,
            aav=offer_aav,
            years=years,
            total_value=total_value,
            hometown_discount=False,
            notes=notes
        ))
    
    # Add hometown discount option if applicable
    if player_input.years_with_team > 0:
        # Generate a hometown discount offer
        discount_mult = 1.0 - hometown_discount_pct
        hometown_aav = base_aav * discount_mult * league_scale_multiplier
        
        # Hometown deals tend to be longer (loyalty)
        min_years, max_years = calculate_contract_years(player_input.age)
        hometown_years = max_years
        
        hometown_total = hometown_aav * hometown_years
        
        offers.append(ContractOffer(
            team_archetype=TeamArchetype.DYNASTY,  # Placeholder for hometown team
            aav=hometown_aav,
            years=hometown_years,
            total_value=hometown_total,
            hometown_discount=True,
            notes=f"Hometown discount ({int(hometown_discount_pct * 100)}% off)"
        ))
    
    # Sort by total value (descending)
    offers.sort(key=lambda x: x.total_value, reverse=True)
    
    return offers


def parse_player_from_dict(player_dict, is_international=False, projected_war=None, free_agent_pool=None):
    """
    Convert a player dictionary (from HTML parsing) to PlayerContractInput.
    
    Args:
        player_dict: Player dictionary from parse_players_from_html()
        is_international: Whether player is international (no stats)
        projected_war: Manual projected WAR for international players
        free_agent_pool: List of all free agents for OVR-percentile calculation
    
    Returns:
        PlayerContractInput object
    """
    name = player_dict.get("Name", "Unknown")
    
    try:
        age = int(player_dict.get("Age", 25))
    except (ValueError, TypeError):
        age = 25
    
    position = player_dict.get("POS", "").upper()
    player_type = "pitcher" if position in ["SP", "RP", "CL", "P"] else "batter"
    
    war = get_war(player_dict, player_type)
    
    # Get stats based on player type
    wrc_plus = None
    era_plus = None
    if player_type == "batter":
        wrc_plus = parse_number(player_dict.get("wRC+", 0))
        if wrc_plus == 0:
            wrc_plus = None
    else:
        era_plus = parse_number(player_dict.get("ERA+", 0))
        if era_plus == 0:
            era_plus = None
    
    # Get OVR rating
    ovr_rating = parse_star_rating(player_dict.get("OVR", 0))
    if ovr_rating == 0:
        ovr_rating = None
    
    # If player has no WAR data and has OVR, use OVR-percentile mode
    if war == 0 and ovr_rating is not None and free_agent_pool is not None:
        # Automatically calculate WAR from OVR percentile
        percentile = calculate_ovr_percentile(ovr_rating, free_agent_pool)
        projected_war = war_from_percentile(percentile)
        is_international = True  # Treat as international (OVR-based valuation)
    
    # Years with team (not available in standard export, would need custom field)
    years_with_team = 0
    
    return PlayerContractInput(
        name=name,
        age=age,
        position=position,
        war=war,
        wrc_plus=wrc_plus,
        era_plus=era_plus,
        ovr_rating=ovr_rating,
        years_with_team=years_with_team,
        is_international=is_international,
        projected_war=projected_war
    )
