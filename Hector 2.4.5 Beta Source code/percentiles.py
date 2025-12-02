# Percentile Rankings Calculator
# Calculates league-wide percentiles for player metrics

from player_utils import parse_star_rating

# Percentile Tier Definitions
PERCENTILE_TIERS = {
    "elite": {"min": 90, "max": 100, "icon": "💎", "label": "Elite", "color": "#51cf66"},
    "above_average": {"min": 70, "max": 89, "icon": "⭐", "label": "Above Avg", "color": "#4dabf7"},
    "average": {"min": 40, "max": 69, "icon": "✅", "label": "Average", "color": "#ffd43b"},
    "below_average": {"min": 20, "max": 39, "icon": "📉", "label": "Below Avg", "color": "#ff922b"},
    "poor": {"min": 0, "max": 19, "icon": "❌", "label": "Poor", "color": "#ff6b6b"},
}

# Batter metrics to calculate percentiles for
# inverse=True means lower is better (e.g., SO%)
BATTER_METRICS = {
    # Stats
    "wRC+": {"key": "wRC+", "label": "wRC+", "inverse": False},
    "WAR": {"key": "WAR (Batter)", "fallback": "WAR", "label": "WAR", "inverse": False},
    "OPS+": {"key": "OPS+", "label": "OPS+", "inverse": False},
    "OPS": {"key": "OPS", "label": "OPS", "inverse": False},
    "wOBA": {"key": "wOBA", "label": "wOBA", "inverse": False},
    "AVG": {"key": "AVG", "label": "AVG", "inverse": False},
    "OBP": {"key": "OBP", "label": "OBP", "inverse": False},
    "SLG": {"key": "SLG", "label": "SLG", "inverse": False},
    "ISO": {"key": "ISO", "label": "ISO", "inverse": False},
    "BB%": {"key": "BB%", "label": "BB%", "inverse": False},
    "SO%": {"key": "SO%", "label": "SO%", "inverse": True},  # Lower is better
    # Ratings
    "CON": {"key": "CON", "label": "Contact", "inverse": False},
    "POW": {"key": "POW", "label": "Power", "inverse": False},
    "EYE": {"key": "EYE", "label": "Eye", "inverse": False},
    "SPE": {"key": "SPE", "label": "Speed", "inverse": False},
    "OVR": {"key": "OVR", "label": "Overall", "inverse": False},
    "POT": {"key": "POT", "label": "Potential", "inverse": False},
}

# Pitcher metrics to calculate percentiles for
PITCHER_METRICS = {
    # Stats
    "WAR": {"key": "WAR (Pitcher)", "fallback": "WAR", "label": "WAR", "inverse": False},
    "ERA+": {"key": "ERA+", "label": "ERA+", "inverse": False},
    "FIP": {"key": "FIP", "label": "FIP", "inverse": True},  # Lower is better
    "FIP-": {"key": "FIP-", "label": "FIP-", "inverse": True},  # Lower is better
    "SIERA": {"key": "SIERA", "label": "SIERA", "inverse": True},  # Lower is better
    "K/9": {"key": "K/9", "label": "K/9", "inverse": False},
    "BB/9": {"key": "BB/9", "label": "BB/9", "inverse": True},  # Lower is better
    "HR/9": {"key": "HR/9", "label": "HR/9", "inverse": True},  # Lower is better
    # Ratings
    "STU": {"key": "STU", "label": "Stuff", "inverse": False},
    "MOV": {"key": "MOV", "label": "Movement", "inverse": False},
    "CON": {"key": "CON", "label": "Control", "inverse": False},
    "OVR": {"key": "OVR", "label": "Overall", "inverse": False},
    "POT": {"key": "POT", "label": "Potential", "inverse": False},
}


def get_metric_value(player, metric_config):
    """Get the value for a metric from a player"""
    key = metric_config.get("key", "")
    fallback = metric_config.get("fallback", "")
    
    val = player.get(key, "")
    if (not val or val == "-") and fallback:
        val = player.get(fallback, "")
    
    return parse_star_rating(val)


def calculate_percentile(value, all_values, inverse=False):
    """
    Calculate the percentile rank for a value within a distribution.
    For inverse metrics (lower is better), we flip the calculation.
    
    Returns percentile as integer 0-100.
    """
    if not all_values:
        return 50  # Default to average if no data
    
    # Filter out zeros for better percentile calculation (0 often means no data)
    filtered_values = [v for v in all_values if v != 0]
    
    if not filtered_values:
        return 50
    
    if inverse:
        # For inverse metrics, count how many values are worse (higher)
        count_worse = sum(1 for v in filtered_values if v > value)
        count_equal = sum(1 for v in filtered_values if v == value)
    else:
        # Count how many values are worse (lower)
        count_worse = sum(1 for v in filtered_values if v < value)
        count_equal = sum(1 for v in filtered_values if v == value)
    
    # Percentile = (count below + 0.5 * count equal) / total * 100
    percentile = (count_worse + 0.5 * count_equal) / len(filtered_values) * 100
    
    return max(0, min(100, round(percentile)))


def get_percentile_tier(percentile):
    """Get the tier information for a given percentile"""
    for tier_key, tier_info in PERCENTILE_TIERS.items():
        if tier_info["min"] <= percentile <= tier_info["max"]:
            return {
                "key": tier_key,
                "icon": tier_info["icon"],
                "label": tier_info["label"],
                "color": tier_info["color"],
            }
    return {"key": "average", "icon": "✅", "label": "Average", "color": "#ffd43b"}


def generate_percentile_bar(percentile, width=20):
    """Generate a visual bar representation of the percentile"""
    filled = int(percentile / 100 * width)
    empty = width - filled
    return "█" * filled + "░" * empty


class PercentileCalculator:
    """Calculates and caches percentile rankings for players"""
    
    def __init__(self):
        self.batter_distributions = {}  # metric -> list of values
        self.pitcher_distributions = {}  # metric -> list of values
        self._cache_valid = False
    
    def build_distributions(self, batters, pitchers):
        """
        Build distributions for all metrics from player data.
        Call this once after loading data.
        """
        # Build batter distributions
        self.batter_distributions = {}
        for metric_name, config in BATTER_METRICS.items():
            values = []
            for batter in batters:
                val = get_metric_value(batter, config)
                if val != 0:  # Only include non-zero values
                    values.append(val)
            self.batter_distributions[metric_name] = sorted(values)
        
        # Build pitcher distributions
        self.pitcher_distributions = {}
        for metric_name, config in PITCHER_METRICS.items():
            values = []
            for pitcher in pitchers:
                val = get_metric_value(pitcher, config)
                if val != 0:  # Only include non-zero values
                    values.append(val)
            self.pitcher_distributions[metric_name] = sorted(values)
        
        self._cache_valid = True
    
    def get_batter_percentiles(self, batter):
        """
        Get percentile rankings for all metrics for a batter.
        Returns dict of metric_name -> {value, percentile, tier_info, bar}
        """
        if not self._cache_valid:
            return {}
        
        results = {}
        for metric_name, config in BATTER_METRICS.items():
            value = get_metric_value(batter, config)
            distribution = self.batter_distributions.get(metric_name, [])
            inverse = config.get("inverse", False)
            
            percentile = calculate_percentile(value, distribution, inverse)
            tier = get_percentile_tier(percentile)
            bar = generate_percentile_bar(percentile)
            
            results[metric_name] = {
                "label": config["label"],
                "value": value,
                "percentile": percentile,
                "tier": tier,
                "bar": bar,
                "inverse": inverse,
            }
        
        return results
    
    def get_pitcher_percentiles(self, pitcher):
        """
        Get percentile rankings for all metrics for a pitcher.
        Returns dict of metric_name -> {value, percentile, tier_info, bar}
        """
        if not self._cache_valid:
            return {}
        
        results = {}
        for metric_name, config in PITCHER_METRICS.items():
            value = get_metric_value(pitcher, config)
            distribution = self.pitcher_distributions.get(metric_name, [])
            inverse = config.get("inverse", False)
            
            percentile = calculate_percentile(value, distribution, inverse)
            tier = get_percentile_tier(percentile)
            bar = generate_percentile_bar(percentile)
            
            results[metric_name] = {
                "label": config["label"],
                "value": value,
                "percentile": percentile,
                "tier": tier,
                "bar": bar,
                "inverse": inverse,
            }
        
        return results
    
    def get_player_summary(self, player, player_type="batter"):
        """
        Get a summary of best and worst percentiles for a player.
        Returns dict with best/worst metrics.
        """
        if player_type == "batter":
            percentiles = self.get_batter_percentiles(player)
        else:
            percentiles = self.get_pitcher_percentiles(player)
        
        if not percentiles:
            return {"best": [], "worst": []}
        
        # Sort by percentile
        sorted_metrics = sorted(
            percentiles.items(),
            key=lambda x: x[1]["percentile"],
            reverse=True
        )
        
        # Get top 3 best and worst
        best = []
        worst = []
        
        for metric_name, data in sorted_metrics[:3]:
            if data["percentile"] >= 50:  # Only include if actually good
                best.append({
                    "name": metric_name,
                    "label": data["label"],
                    "percentile": data["percentile"],
                    "tier": data["tier"],
                })
        
        for metric_name, data in sorted_metrics[-3:]:
            if data["percentile"] < 50:  # Only include if actually bad
                worst.append({
                    "name": metric_name,
                    "label": data["label"],
                    "percentile": data["percentile"],
                    "tier": data["tier"],
                })
        
        return {"best": best, "worst": worst}
    
    def format_percentile_display(self, metric_data):
        """Format a single metric for display"""
        tier = metric_data["tier"]
        return (
            f"{metric_data['label']:>8} "
            f"{metric_data['value']:>6.1f} | "
            f"{metric_data['percentile']:>3}th | "
            f"{metric_data['bar']} "
            f"{tier['icon']} {tier['label']}"
        )


# Global instance for caching
_percentile_calculator = None


def get_percentile_calculator():
    """Get or create the global percentile calculator instance"""
    global _percentile_calculator
    if _percentile_calculator is None:
        _percentile_calculator = PercentileCalculator()
    return _percentile_calculator


def initialize_percentiles(batters, pitchers):
    """Initialize percentile distributions from player data"""
    calc = get_percentile_calculator()
    calc.build_distributions(batters, pitchers)
    return calc
