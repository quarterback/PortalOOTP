# League Analytics Module
# Analyzes league-wide patterns, competitive balance, park factors, and team construction
# from Team List.html data

from trade_value import parse_number
import statistics


def calculate_league_environment(teams_list):
    """
    Calculate league-wide offensive and pitching environment metrics.
    
    Args:
        teams_list: List of team dicts from parse_team_html()
    
    Returns:
        Dict with league environment metrics:
        {
            "total_teams": 30,
            "park_factors": {
                "avg_pf": 1.0,
                "avg_pf_hr": 1.0,
                "avg_pf_avg": 1.0,
                ...
            },
            "batting_war": {"mean": 20.5, "std": 5.2, "min": 12.0, "max": 37.2},
            "pitching_war": {"mean": 18.0, "std": 4.8, "min": 10.7, "max": 28.6},
            "environment_type": "neutral" | "hitter_friendly" | "pitcher_friendly"
        }
    """
    if not teams_list:
        return {}
    
    result = {
        "total_teams": len(teams_list),
        "park_factors": {},
        "batting_war": {},
        "pitching_war": {},
    }
    
    # Collect park factor data
    pf_columns = ["PF", "PF AVG", "PF HR", "PF D", "PF T"]
    pf_data = {col: [] for col in pf_columns}
    
    for team in teams_list:
        for col in pf_columns:
            val = team.get(col)
            if val is not None and isinstance(val, (int, float)) and val > 0:
                pf_data[col].append(val)
    
    # Calculate park factor stats
    for col, values in pf_data.items():
        if values:
            result["park_factors"][f"{col}_mean"] = round(statistics.mean(values), 3)
            result["park_factors"][f"{col}_median"] = round(statistics.median(values), 3)
            if len(values) > 1:
                result["park_factors"][f"{col}_std"] = round(statistics.stdev(values), 3)
            result["park_factors"][f"{col}_min"] = round(min(values), 3)
            result["park_factors"][f"{col}_max"] = round(max(values), 3)
    
    # Collect WAR data
    batting_wars = []
    pitching_wars = []
    
    for team in teams_list:
        war = parse_number(team.get("WAR", 0))
        rwar = parse_number(team.get("rWAR", 0))
        if war > 0:
            batting_wars.append(war)
        if rwar > 0:
            pitching_wars.append(rwar)
    
    # Calculate WAR stats
    if batting_wars:
        result["batting_war"] = {
            "mean": round(statistics.mean(batting_wars), 1),
            "median": round(statistics.median(batting_wars), 1),
            "std": round(statistics.stdev(batting_wars), 1) if len(batting_wars) > 1 else 0,
            "min": round(min(batting_wars), 1),
            "max": round(max(batting_wars), 1),
        }
    
    if pitching_wars:
        result["pitching_war"] = {
            "mean": round(statistics.mean(pitching_wars), 1),
            "median": round(statistics.median(pitching_wars), 1),
            "std": round(statistics.stdev(pitching_wars), 1) if len(pitching_wars) > 1 else 0,
            "min": round(min(pitching_wars), 1),
            "max": round(max(pitching_wars), 1),
        }
    
    # Determine environment type based on overall park factor average
    avg_pf = result["park_factors"].get("PF_mean", 1.0)
    if avg_pf > 1.05:
        result["environment_type"] = "hitter_friendly"
    elif avg_pf < 0.95:
        result["environment_type"] = "pitcher_friendly"
    else:
        result["environment_type"] = "neutral"
    
    return result


def calculate_parity_index(teams_list):
    """
    Calculate competitive balance metrics across the league.
    
    Args:
        teams_list: List of team dicts from parse_team_html()
    
    Returns:
        Dict with parity metrics:
        {
            "win_pct_std": 0.082,
            "teams_near_500": {"within_5_games": 12, "within_10_games": 18},
            "division_balance": {
                "AL Central": {"std": 0.065, "spread": 0.186, "status": "competitive"},
                ...
            },
            "overall_parity": "high" | "medium" | "low"
        }
    """
    if not teams_list:
        return {}
    
    result = {
        "teams_near_500": {},
        "division_balance": {},
    }
    
    # Collect win percentages
    win_pcts = []
    for team in teams_list:
        pct = parse_number(team.get("%", 0))
        if pct > 0:
            win_pcts.append(pct)
    
    # Calculate overall standard deviation
    if len(win_pcts) > 1:
        result["win_pct_std"] = round(statistics.stdev(win_pcts), 3)
    else:
        result["win_pct_std"] = 0
    
    # Count teams near .500
    within_5 = sum(1 for pct in win_pcts if abs(pct - 0.500) <= 0.031)  # ~5 games in 162
    within_10 = sum(1 for pct in win_pcts if abs(pct - 0.500) <= 0.062)  # ~10 games
    result["teams_near_500"] = {
        "within_5_games": within_5,
        "within_10_games": within_10,
    }
    
    # Group by division
    divisions = {}
    for team in teams_list:
        div = team.get("DIV", "Unknown")
        pct = parse_number(team.get("%", 0))
        if pct > 0:
            if div not in divisions:
                divisions[div] = []
            divisions[div].append(pct)
    
    # Calculate division-by-division balance
    for div_name, div_pcts in divisions.items():
        if len(div_pcts) > 1:
            div_std = statistics.stdev(div_pcts)
            div_spread = max(div_pcts) - min(div_pcts)
            
            # Classify division competitiveness
            if div_std < 0.070:
                status = "highly_competitive"
            elif div_std < 0.100:
                status = "competitive"
            elif div_std < 0.130:
                status = "moderate"
            else:
                status = "runaway"
            
            result["division_balance"][div_name] = {
                "std": round(div_std, 3),
                "spread": round(div_spread, 3),
                "min_pct": round(min(div_pcts), 3),
                "max_pct": round(max(div_pcts), 3),
                "status": status,
            }
    
    # Overall parity classification
    if result["win_pct_std"] < 0.070:
        result["overall_parity"] = "high"
    elif result["win_pct_std"] < 0.100:
        result["overall_parity"] = "medium"
    else:
        result["overall_parity"] = "low"
    
    return result


def analyze_park_factors(teams_list):
    """
    Analyze park factor distribution and identify outliers.
    
    Args:
        teams_list: List of team dicts from parse_team_html()
    
    Returns:
        Dict with park analysis:
        {
            "extreme_parks": [
                {"team": "SF", "park": "Oracle Park", "PF HR": 0.688, "type": "hr_suppressing"},
                ...
            ],
            "park_groups": {
                "hr_friendly": [...],
                "hr_suppressing": [...],
                "avg_inflating": [...],
                "neutral": [...]
            }
        }
    """
    if not teams_list:
        return {}
    
    result = {
        "extreme_parks": [],
        "park_groups": {
            "hr_friendly": [],
            "hr_suppressing": [],
            "avg_inflating": [],
            "avg_suppressing": [],
            "neutral": []
        }
    }
    
    for team in teams_list:
        team_abbr = team.get("Abbr", "")
        park_name = team.get("Park", "")
        pf_hr = team.get("PF HR")
        pf_avg = team.get("PF AVG")
        pf_overall = team.get("PF")
        
        # Skip if missing park factors
        if not isinstance(pf_hr, (int, float)) or not isinstance(pf_avg, (int, float)):
            continue
        
        park_info = {
            "team": team_abbr,
            "team_name": team.get("Team Name", ""),
            "park": park_name,
            "PF": pf_overall if isinstance(pf_overall, (int, float)) else 1.0,
            "PF HR": pf_hr,
            "PF AVG": pf_avg,
        }
        
        # Identify extreme parks (>1.10 or <0.90)
        if pf_hr > 1.10:
            result["extreme_parks"].append({**park_info, "type": "hr_friendly", "severity": "extreme"})
        elif pf_hr < 0.90:
            result["extreme_parks"].append({**park_info, "type": "hr_suppressing", "severity": "extreme"})
        
        if pf_avg > 1.10:
            if not any(p["team"] == team_abbr and p["type"] == "hr_friendly" for p in result["extreme_parks"]):
                result["extreme_parks"].append({**park_info, "type": "avg_inflating", "severity": "extreme"})
        elif pf_avg < 0.90:
            if not any(p["team"] == team_abbr and p["type"] == "hr_suppressing" for p in result["extreme_parks"]):
                result["extreme_parks"].append({**park_info, "type": "avg_suppressing", "severity": "extreme"})
        
        # Group parks by type
        if pf_hr > 1.05:
            result["park_groups"]["hr_friendly"].append(park_info)
        elif pf_hr < 0.95:
            result["park_groups"]["hr_suppressing"].append(park_info)
        
        if pf_avg > 1.05:
            result["park_groups"]["avg_inflating"].append(park_info)
        elif pf_avg < 0.95:
            result["park_groups"]["avg_suppressing"].append(park_info)
        
        if 0.95 <= pf_hr <= 1.05 and 0.95 <= pf_avg <= 1.05:
            result["park_groups"]["neutral"].append(park_info)
    
    # Sort extreme parks by severity
    result["extreme_parks"].sort(key=lambda x: abs(x.get("PF HR", 1.0) - 1.0), reverse=True)
    
    return result


def classify_roster_constructions(teams_list):
    """
    Classify teams by their offensive and pitching construction style.
    
    Note: This function requires detailed batting/pitching stats from Team List.html.
    If those columns are not available, returns limited classification based on WAR.
    
    Args:
        teams_list: List of team dicts from parse_team_html()
    
    Returns:
        Dict with roster construction classifications:
        {
            "offensive_styles": {
                "power_heavy": [...],
                "speed_heavy": [...],
                "balanced": [...]
            },
            "pitching_styles": {
                "strikeout_staff": [...],
                "contact_management": [...]
            }
        }
    """
    if not teams_list:
        return {}
    
    result = {
        "offensive_styles": {
            "power_heavy": [],
            "speed_heavy": [],
            "balanced": [],
            "unknown": []
        },
        "pitching_styles": {
            "strikeout_staff": [],
            "contact_management": [],
            "unknown": []
        },
        "note": "Full roster construction analysis requires detailed batting/pitching stats in Team List.html"
    }
    
    # For now, classify based on available data (WAR split)
    # In a real implementation with full stats, we'd use HR, SB, K%, BB%, etc.
    for team in teams_list:
        team_abbr = team.get("Abbr", "")
        team_name = team.get("Team Name", "")
        
        # Check if we have detailed stats
        has_detailed_stats = False
        # These would be columns like: HR, SB, K%, BB%, etc.
        # Since sample data doesn't have them, mark as unknown
        
        if not has_detailed_stats:
            result["offensive_styles"]["unknown"].append({
                "team": team_abbr,
                "team_name": team_name,
                "war": parse_number(team.get("WAR", 0))
            })
            result["pitching_styles"]["unknown"].append({
                "team": team_abbr,
                "team_name": team_name,
                "rwar": parse_number(team.get("rWAR", 0))
            })
    
    return result


def analyze_talent_distribution(teams_list):
    """
    Analyze WAR distribution across teams and divisions.
    
    Args:
        teams_list: List of team dicts from parse_team_html()
    
    Returns:
        Dict with talent distribution analysis:
        {
            "top_teams": [...],
            "bottom_teams": [...],
            "division_talent": {...},
            "super_teams": [...],
            "war_concentration": "high" | "medium" | "low"
        }
    """
    if not teams_list:
        return {}
    
    result = {
        "top_teams": [],
        "bottom_teams": [],
        "division_talent": {},
        "super_teams": []
    }
    
    # Collect team talent data
    team_talent = []
    for team in teams_list:
        batting_war = parse_number(team.get("WAR", 0))
        pitching_war = parse_number(team.get("rWAR", 0))
        total_war = batting_war + pitching_war
        
        team_talent.append({
            "team": team.get("Abbr", ""),
            "team_name": team.get("Team Name", ""),
            "division": team.get("DIV", ""),
            "batting_war": batting_war,
            "pitching_war": pitching_war,
            "total_war": total_war,
        })
    
    # Sort by total WAR
    team_talent.sort(key=lambda x: x["total_war"], reverse=True)
    
    # Identify top and bottom teams
    result["top_teams"] = team_talent[:5]
    result["bottom_teams"] = team_talent[-5:]
    
    # Identify super teams (top 10% in both batting and pitching)
    if team_talent:
        batting_90th = statistics.quantiles([t["batting_war"] for t in team_talent], n=10)[-1] if len(team_talent) >= 10 else 0
        pitching_90th = statistics.quantiles([t["pitching_war"] for t in team_talent], n=10)[-1] if len(team_talent) >= 10 else 0
        
        for team in team_talent:
            if team["batting_war"] >= batting_90th and team["pitching_war"] >= pitching_90th:
                result["super_teams"].append(team)
    
    # Analyze by division
    divisions = {}
    for team in team_talent:
        div = team["division"]
        if div not in divisions:
            divisions[div] = []
        divisions[div].append(team)
    
    for div_name, div_teams in divisions.items():
        if div_teams:
            total_wars = [t["total_war"] for t in div_teams]
            result["division_talent"][div_name] = {
                "teams": len(div_teams),
                "avg_war": round(statistics.mean(total_wars), 1),
                "total_war": round(sum(total_wars), 1),
                "top_team": div_teams[0]["team"],
                "top_team_war": round(div_teams[0]["total_war"], 1),
            }
    
    # Calculate concentration (using coefficient of variation)
    if team_talent:
        wars = [t["total_war"] for t in team_talent]
        if statistics.mean(wars) > 0:
            cv = statistics.stdev(wars) / statistics.mean(wars)
            if cv > 0.25:
                result["war_concentration"] = "high"
            elif cv > 0.15:
                result["war_concentration"] = "medium"
            else:
                result["war_concentration"] = "low"
    
    return result


def calculate_run_differential_analysis(teams_list):
    """
    Calculate run differential and Pythagorean expectation.
    
    Note: Requires runs scored and runs allowed columns in Team List.html.
    Falls back to win% analysis if detailed stats unavailable.
    
    Args:
        teams_list: List of team dicts from parse_team_html()
    
    Returns:
        Dict with run differential analysis:
        {
            "overperformers": [...],
            "underperformers": [...],
            "expected_standings": [...],
            "note": "..."
        }
    """
    if not teams_list:
        return {}
    
    result = {
        "overperformers": [],
        "underperformers": [],
        "note": "Detailed run differential analysis requires R (runs scored) and RA (runs allowed) columns in Team List.html"
    }
    
    # Since sample data doesn't have R and RA columns, we can't do full analysis
    # Could potentially derive from pitching ERA and innings, but that's complex
    
    return result


def analyze_year_over_year_trends(teams_list):
    """
    Analyze changes from last year using ly* columns.
    
    Args:
        teams_list: List of team dicts from parse_team_html()
    
    Returns:
        Dict with year-over-year trends:
        {
            "biggest_improvers": [...],
            "biggest_decliners": [...],
            "league_trend": "improving" | "declining" | "stable",
            "division_power_shifts": {...}
        }
    """
    if not teams_list:
        return {}
    
    result = {
        "biggest_improvers": [],
        "biggest_decliners": [],
        "division_power_shifts": {}
    }
    
    # Collect year-over-year changes
    team_changes = []
    total_change = 0
    teams_with_ly_data = 0
    
    for team in teams_list:
        curr_pct = parse_number(team.get("%", 0))
        ly_pct = parse_number(team.get("ly%", 0))
        
        if curr_pct > 0 and ly_pct > 0:
            change = curr_pct - ly_pct
            curr_wins = parse_number(team.get("W", 0))
            ly_wins = parse_number(team.get("lyW", 0))
            # Handle potential None values from parse_number
            wins_change = (curr_wins - ly_wins) if (curr_wins is not None and ly_wins is not None) else 0
            
            team_changes.append({
                "team": team.get("Abbr", ""),
                "team_name": team.get("Team Name", ""),
                "division": team.get("DIV", ""),
                "current_pct": curr_pct,
                "ly_pct": ly_pct,
                "pct_change": round(change, 3),
                "wins_change": wins_change,
            })
            
            total_change += change
            teams_with_ly_data += 1
    
    # Sort by change
    team_changes.sort(key=lambda x: x["pct_change"], reverse=True)
    
    # Identify biggest movers
    result["biggest_improvers"] = team_changes[:5]
    result["biggest_decliners"] = team_changes[-5:]
    
    # League-wide trend
    if teams_with_ly_data > 0:
        avg_change = total_change / teams_with_ly_data
        if avg_change > 0.01:
            result["league_trend"] = "improving"
        elif avg_change < -0.01:
            result["league_trend"] = "declining"
        else:
            result["league_trend"] = "stable"
        result["avg_win_pct_change"] = round(avg_change, 3)
    
    # Division power shifts
    divisions = {}
    for team_change in team_changes:
        div = team_change["division"]
        if div not in divisions:
            divisions[div] = []
        divisions[div].append(team_change)
    
    for div_name, div_teams in divisions.items():
        if div_teams:
            # Find team with biggest positive change
            improver = max(div_teams, key=lambda x: x["pct_change"])
            # Find team with biggest negative change
            decliner = min(div_teams, key=lambda x: x["pct_change"])
            
            result["division_power_shifts"][div_name] = {
                "biggest_improver": {
                    "team": improver["team"],
                    "change": improver["pct_change"]
                },
                "biggest_decliner": {
                    "team": decliner["team"],
                    "change": decliner["pct_change"]
                }
            }
    
    return result


def generate_league_report(teams_list):
    """
    Generate comprehensive league analysis report combining all metrics.
    
    Args:
        teams_list: List of team dicts from parse_team_html()
    
    Returns:
        Dict with complete league analysis:
        {
            "environment": {...},
            "parity": {...},
            "park_factors": {...},
            "roster_construction": {...},
            "talent_distribution": {...},
            "run_differential": {...},
            "year_over_year": {...},
            "summary_insights": [...]
        }
    """
    if not teams_list:
        return {
            "error": "No team data available",
            "summary_insights": ["No team data loaded. Please ensure Team List.html is available."]
        }
    
    report = {
        "environment": calculate_league_environment(teams_list),
        "parity": calculate_parity_index(teams_list),
        "park_factors": analyze_park_factors(teams_list),
        "roster_construction": classify_roster_constructions(teams_list),
        "talent_distribution": analyze_talent_distribution(teams_list),
        "run_differential": calculate_run_differential_analysis(teams_list),
        "year_over_year": analyze_year_over_year_trends(teams_list),
        "summary_insights": []
    }
    
    # Generate human-readable insights
    insights = []
    
    # Environment insight
    env = report["environment"]
    if env.get("environment_type"):
        insights.append(f"League environment: {env['environment_type']}")
    
    # Park factor insight
    park = report["park_factors"]
    if park.get("extreme_parks"):
        extreme = park["extreme_parks"][0]
        insights.append(
            f"Most extreme park: {extreme['park']} ({extreme['team']}) - "
            f"PF HR: {extreme['PF HR']:.3f}"
        )
    
    # Parity insight
    parity = report["parity"]
    if parity.get("overall_parity"):
        insights.append(f"Competitive balance: {parity['overall_parity']} parity")
    
    # Talent insight
    talent = report["talent_distribution"]
    if talent.get("top_teams"):
        top = talent["top_teams"][0]
        insights.append(
            f"League leader: {top['team_name']} with {top['total_war']:.1f} total WAR"
        )
    
    if talent.get("super_teams"):
        insights.append(f"{len(talent['super_teams'])} super team(s) dominating both offense and pitching")
    
    # Year-over-year insight
    yoy = report["year_over_year"]
    if yoy.get("biggest_improvers"):
        improver = yoy["biggest_improvers"][0]
        insights.append(
            f"Biggest improvement: {improver['team_name']} "
            f"({improver['wins_change']:+.0f} wins)"
        )
    
    report["summary_insights"] = insights
    
    return report
