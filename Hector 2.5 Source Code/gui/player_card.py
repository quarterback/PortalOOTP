# Player Card with Percentile View
# Display detailed player info with percentile rankings

import tkinter as tk
from tkinter import ttk
from percentiles import get_percentile_calculator, PERCENTILE_TIERS
from archetypes import get_player_archetype_fits, get_best_archetype, ARCHETYPES
from advanced_stats import (
    calculate_all_batter_advanced_stats,
    calculate_all_pitcher_advanced_stats,
)

# Player card window dimensions
PLAYER_CARD_WIDTH = 700
PLAYER_CARD_HEIGHT = 780


def show_player_card(parent, player, player_type="batter"):
    """
    Display a popup window with detailed player percentiles.
    
    Args:
        parent: Parent window
        player: Player dict
        player_type: "batter" or "pitcher"
    """
    # Create popup window
    popup = tk.Toplevel(parent)
    popup.title(f"Player Card - {player.get('Name', 'Unknown')}")
    popup.geometry(f"{PLAYER_CARD_WIDTH}x{PLAYER_CARD_HEIGHT}")
    popup.configure(bg="#2d2d2d")
    
    # Make it modal-ish
    popup.transient(parent)
    popup.grab_set()
    
    # Header with player name and basic info
    header_frame = tk.Frame(popup, bg="#2d2d2d")
    header_frame.pack(fill="x", padx=20, pady=15)
    
    name_label = tk.Label(
        header_frame,
        text=player.get("Name", "Unknown"),
        font=("Consolas", 16, "bold"),
        bg="#2d2d2d",
        fg="#00ff7f"
    )
    name_label.pack(anchor="w")
    
    info_text = f"{player.get('ORG', '')} | {player.get('POS', '')} | Age {player.get('Age', '')}"
    if player_type == "batter":
        info_text += f" | Bats: {player.get('B', '')}"
    else:
        info_text += f" | Throws: {player.get('T', '')}"
    
    info_label = tk.Label(
        header_frame,
        text=info_text,
        font=("Consolas", 11),
        bg="#2d2d2d",
        fg="#888888"
    )
    info_label.pack(anchor="w")
    
    # OVR/POT display
    ratings_frame = tk.Frame(header_frame, bg="#2d2d2d")
    ratings_frame.pack(anchor="w", pady=(10, 0))
    
    tk.Label(
        ratings_frame,
        text=f"OVR: {player.get('OVR', '-')}",
        font=("Consolas", 12, "bold"),
        bg="#2d2d2d",
        fg="#4dabf7"
    ).pack(side="left", padx=(0, 20))
    
    tk.Label(
        ratings_frame,
        text=f"POT: {player.get('POT', '-')}",
        font=("Consolas", 12, "bold"),
        bg="#2d2d2d",
        fg="#9775fa"
    ).pack(side="left")
    
    # Separator
    ttk.Separator(popup, orient="horizontal").pack(fill="x", padx=20, pady=10)
    
    # Percentile rankings
    percentile_frame = tk.Frame(popup, bg="#2d2d2d")
    percentile_frame.pack(fill="both", expand=True, padx=20, pady=10)
    
    tk.Label(
        percentile_frame,
        text="Percentile Rankings (League-Wide)",
        font=("Consolas", 12, "bold"),
        bg="#2d2d2d",
        fg="#d4d4d4"
    ).pack(anchor="w", pady=(0, 10))
    
    # Get percentiles
    calc = get_percentile_calculator()
    
    if player_type == "batter":
        percentiles = calc.get_batter_percentiles(player)
    else:
        percentiles = calc.get_pitcher_percentiles(player)
    
    # Scrollable frame for percentiles
    canvas = tk.Canvas(percentile_frame, bg="#2d2d2d", highlightthickness=0)
    scrollbar = ttk.Scrollbar(percentile_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg="#2d2d2d")
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Display each percentile
    if percentiles:
        # Sort by percentile descending
        sorted_percentiles = sorted(
            percentiles.items(),
            key=lambda x: x[1]["percentile"],
            reverse=True
        )
        
        for metric_name, data in sorted_percentiles:
            row = tk.Frame(scrollable_frame, bg="#2d2d2d")
            row.pack(fill="x", pady=2)
            
            # Metric name
            tk.Label(
                row,
                text=f"{data['label']:>10}",
                font=("Consolas", 10),
                bg="#2d2d2d",
                fg="#888888",
                width=10,
                anchor="e"
            ).pack(side="left")
            
            # Value
            value_text = f"{data['value']:>7.1f}" if data['value'] != 0 else "      -"
            tk.Label(
                row,
                text=value_text,
                font=("Consolas", 10),
                bg="#2d2d2d",
                fg="#d4d4d4",
                width=8
            ).pack(side="left")
            
            # Percentile
            tk.Label(
                row,
                text=f"{data['percentile']:>3}th",
                font=("Consolas", 10),
                bg="#2d2d2d",
                fg="#d4d4d4",
                width=6
            ).pack(side="left", padx=5)
            
            # Bar
            tier = data["tier"]
            tk.Label(
                row,
                text=data["bar"],
                font=("Consolas", 10),
                bg="#2d2d2d",
                fg=tier["color"],
                width=22
            ).pack(side="left")
            
            # Tier icon and label
            tk.Label(
                row,
                text=f"{tier['icon']} {tier['label']}",
                font=("Consolas", 10),
                bg="#2d2d2d",
                fg=tier["color"],
                width=14
            ).pack(side="left")
    else:
        tk.Label(
            scrollable_frame,
            text="No percentile data available.\nLoad player data and try again.",
            font=("Consolas", 11),
            bg="#2d2d2d",
            fg="#888888"
        ).pack(pady=20)
    
    # Summary section
    summary_frame = tk.Frame(popup, bg="#2a2a2a", relief="raised", bd=1)
    summary_frame.pack(fill="x", padx=20, pady=10)
    
    summary = calc.get_player_summary(player, player_type)
    
    # Best percentiles
    if summary["best"]:
        best_frame = tk.Frame(summary_frame, bg="#2a2a2a")
        best_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(
            best_frame,
            text="💎 Best:",
            font=("Consolas", 10, "bold"),
            bg="#2a2a2a",
            fg="#51cf66"
        ).pack(side="left")
        
        best_text = ", ".join([
            f"{b['label']} ({b['percentile']}th)"
            for b in summary["best"]
        ])
        tk.Label(
            best_frame,
            text=best_text,
            font=("Consolas", 10),
            bg="#2a2a2a",
            fg="#d4d4d4"
        ).pack(side="left", padx=10)
    
    # Worst percentiles
    if summary["worst"]:
        worst_frame = tk.Frame(summary_frame, bg="#2a2a2a")
        worst_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(
            worst_frame,
            text="❌ Worst:",
            font=("Consolas", 10, "bold"),
            bg="#2a2a2a",
            fg="#ff6b6b"
        ).pack(side="left")
        
        worst_text = ", ".join([
            f"{w['label']} ({w['percentile']}th)"
            for w in summary["worst"]
        ])
        tk.Label(
            worst_frame,
            text=worst_text,
            font=("Consolas", 10),
            bg="#2a2a2a",
            fg="#d4d4d4"
        ).pack(side="left", padx=10)
    
    # Archetype Fits Section
    ttk.Separator(popup, orient="horizontal").pack(fill="x", padx=20, pady=10)
    
    archetype_frame = tk.Frame(popup, bg="#2d2d2d")
    archetype_frame.pack(fill="x", padx=20, pady=5)
    
    tk.Label(
        archetype_frame,
        text="🎯 Archetype Fits",
        font=("Consolas", 12, "bold"),
        bg="#2d2d2d",
        fg="#ffd43b"
    ).pack(anchor="w")
    
    # Get archetype fits for this player
    archetype_fits = get_player_archetype_fits(player, player_type)
    best_archetype = get_best_archetype(player, player_type)
    
    if archetype_fits:
        # Show best archetype prominently
        if best_archetype and best_archetype["score"] >= 40:
            best_frame = tk.Frame(archetype_frame, bg="#2a2a2a", relief="raised", bd=1)
            best_frame.pack(fill="x", pady=5)
            
            tk.Label(
                best_frame,
                text=f"Best Fit: {best_archetype['icon']} {best_archetype['name']}",
                font=("Consolas", 11, "bold"),
                bg="#2a2a2a",
                fg="#00ff7f"
            ).pack(side="left", padx=10, pady=5)
            
            tk.Label(
                best_frame,
                text=f"{best_archetype['score']:.0f} - {best_archetype['label']}",
                font=("Consolas", 10),
                bg="#2a2a2a",
                fg="#888888"
            ).pack(side="left", padx=10, pady=5)
        
        # Show other good fits (score >= 40, sorted)
        sorted_fits = sorted(
            [(k, v) for k, v in archetype_fits.items() if v["score"] >= 40],
            key=lambda x: x[1]["score"],
            reverse=True
        )
        
        if sorted_fits:
            other_frame = tk.Frame(archetype_frame, bg="#2d2d2d")
            other_frame.pack(fill="x", pady=5)
            
            for i, (arch_key, fit_info) in enumerate(sorted_fits[:6]):  # Show top 6
                arch_info = ARCHETYPES.get(arch_key, {})
                
                fit_frame = tk.Frame(other_frame, bg="#2d2d2d")
                fit_frame.pack(fill="x", pady=1)
                
                # Color based on fit level
                if fit_info["score"] >= 80:
                    score_color = "#51cf66"  # Green
                elif fit_info["score"] >= 60:
                    score_color = "#4dabf7"  # Blue
                else:
                    score_color = "#ffd43b"  # Yellow
                
                tk.Label(
                    fit_frame,
                    text=f"{arch_info.get('icon', '•')} {fit_info['archetype_name']}",
                    font=("Consolas", 10),
                    bg="#2d2d2d",
                    fg="#d4d4d4",
                    width=22,
                    anchor="w"
                ).pack(side="left")
                
                tk.Label(
                    fit_frame,
                    text=f"{fit_info['score']:.0f}",
                    font=("Consolas", 10, "bold"),
                    bg="#2d2d2d",
                    fg=score_color,
                    width=4
                ).pack(side="left")
                
                tk.Label(
                    fit_frame,
                    text=fit_info['label'],
                    font=("Consolas", 9),
                    bg="#2d2d2d",
                    fg="#888888"
                ).pack(side="left", padx=5)
        else:
            tk.Label(
                archetype_frame,
                text="No strong archetype fits (score < 40)",
                font=("Consolas", 10),
                bg="#2d2d2d",
                fg="#888888"
            ).pack(anchor="w", pady=5)
    else:
        tk.Label(
            archetype_frame,
            text="No archetype data available",
            font=("Consolas", 10),
            bg="#2d2d2d",
            fg="#888888"
        ).pack(anchor="w", pady=5)
    
    # Advanced Stats Section
    ttk.Separator(popup, orient="horizontal").pack(fill="x", padx=20, pady=10)
    
    advanced_frame = tk.Frame(popup, bg="#2d2d2d")
    advanced_frame.pack(fill="x", padx=20, pady=5)
    
    tk.Label(
        advanced_frame,
        text="📊 Advanced Stats",
        font=("Consolas", 12, "bold"),
        bg="#2d2d2d",
        fg="#4dabf7"
    ).pack(anchor="w")
    
    # Calculate advanced stats
    if player_type == "batter":
        advanced_stats = player.get("advanced_stats") or calculate_all_batter_advanced_stats(player)
        
        # Display key batter metrics
        stats_row1 = tk.Frame(advanced_frame, bg="#2d2d2d")
        stats_row1.pack(fill="x", pady=2)
        
        for label, key, fmt in [
            ("xBA", "xBA", ".3f"),
            ("xSLG", "xSLG", ".3f"),
            ("xWOBA", "xWOBA", ".3f"),
            ("xOPS+", "xOPS+", ".0f"),
        ]:
            val = advanced_stats.get(key, 0)
            tk.Label(
                stats_row1,
                text=f"{label}: {val:{fmt}}",
                font=("Consolas", 10),
                bg="#2d2d2d",
                fg="#d4d4d4",
                width=12
            ).pack(side="left", padx=2)
        
        stats_row2 = tk.Frame(advanced_frame, bg="#2d2d2d")
        stats_row2.pack(fill="x", pady=2)
        
        for label, key, fmt in [
            ("Contact+", "Contact+", ".0f"),
            ("Barrel%", "Barrel%", ".1f"),
            ("Off.Rtg", "Offensive_Rating", ".0f"),
            ("PwrSpd", "Power_Speed", ".1f"),
        ]:
            val = advanced_stats.get(key, 0)
            tk.Label(
                stats_row2,
                text=f"{label}: {val:{fmt}}",
                font=("Consolas", 10),
                bg="#2d2d2d",
                fg="#d4d4d4",
                width=12
            ).pack(side="left", padx=2)
    else:
        advanced_stats = player.get("advanced_stats") or calculate_all_pitcher_advanced_stats(player)
        
        # Display key pitcher metrics
        stats_row = tk.Frame(advanced_frame, bg="#2d2d2d")
        stats_row.pack(fill="x", pady=2)
        
        for label, key, fmt in [
            ("Stuff+", "Stuff+", ".0f"),
            ("K/BB", "K/BB", ".2f"),
            ("xERA", "xERA", ".2f"),
            ("Score", "Pitcher_Score", ".0f"),
        ]:
            val = advanced_stats.get(key, 0)
            tk.Label(
                stats_row,
                text=f"{label}: {val:{fmt}}",
                font=("Consolas", 10),
                bg="#2d2d2d",
                fg="#d4d4d4",
                width=12
            ).pack(side="left", padx=2)
    
    # Show indicators
    undervalued = advanced_stats.get("Undervalued", {})
    regression = advanced_stats.get("Regression", {})
    breakout = advanced_stats.get("Breakout", {})
    
    indicators_row = tk.Frame(advanced_frame, bg="#2d2d2d")
    indicators_row.pack(fill="x", pady=5)
    
    if undervalued.get("undervalued"):
        tk.Label(
            indicators_row,
            text=f"💎 Undervalued: {undervalued.get('reason', '')}",
            font=("Consolas", 9),
            bg="#2d2d2d",
            fg="#51cf66"
        ).pack(side="left", padx=5)
    
    if regression.get("is_regression_candidate"):
        direction = regression.get("direction", "neutral")
        color = "#ff6b6b" if direction == "down" else "#4dabf7"
        icon = "📉" if direction == "down" else "📈"
        reasons = "; ".join(regression.get("reasons", []))
        tk.Label(
            indicators_row,
            text=f"{icon} Regression: {reasons}",
            font=("Consolas", 9),
            bg="#2d2d2d",
            fg=color
        ).pack(side="left", padx=5)
    
    if breakout.get("is_breakout"):
        indicators_text = ", ".join(breakout.get("indicators", [])[:2])
        tk.Label(
            indicators_row,
            text=f"🚀 Breakout: {indicators_text}",
            font=("Consolas", 9),
            bg="#2d2d2d",
            fg="#ffd43b"
        ).pack(side="left", padx=5)
    
    # Close button
    close_btn = ttk.Button(popup, text="Close", command=popup.destroy)
    close_btn.pack(pady=10)
    
    # Center window on parent
    popup.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() - popup.winfo_width()) // 2
    y = parent.winfo_y() + (parent.winfo_height() - popup.winfo_height()) // 2
    popup.geometry(f"+{x}+{y}")
    
    return popup


def create_percentile_summary_widget(parent, player, player_type="batter", font=("Consolas", 10)):
    """
    Create a compact percentile summary widget that can be embedded.
    
    Returns a frame with top 3 best/worst percentiles.
    """
    frame = tk.Frame(parent, bg="#2a2a2a", relief="raised", bd=1)
    
    calc = get_percentile_calculator()
    summary = calc.get_player_summary(player, player_type)
    
    # Header
    tk.Label(
        frame,
        text="Percentile Summary",
        font=(font[0], font[1], "bold"),
        bg="#2a2a2a",
        fg="#d4d4d4"
    ).pack(fill="x", padx=5, pady=3)
    
    # Best
    if summary["best"]:
        best_row = tk.Frame(frame, bg="#2a2a2a")
        best_row.pack(fill="x", padx=5, pady=2)
        
        tk.Label(
            best_row,
            text="💎",
            font=font,
            bg="#2a2a2a",
            fg="#51cf66"
        ).pack(side="left")
        
        for b in summary["best"][:3]:
            tk.Label(
                best_row,
                text=f"{b['label']} {b['percentile']}th",
                font=font,
                bg="#2a2a2a",
                fg="#51cf66"
            ).pack(side="left", padx=3)
    
    # Worst
    if summary["worst"]:
        worst_row = tk.Frame(frame, bg="#2a2a2a")
        worst_row.pack(fill="x", padx=5, pady=2)
        
        tk.Label(
            worst_row,
            text="❌",
            font=font,
            bg="#2a2a2a",
            fg="#ff6b6b"
        ).pack(side="left")
        
        for w in summary["worst"][:3]:
            tk.Label(
                worst_row,
                text=f"{w['label']} {w['percentile']}th",
                font=font,
                bg="#2a2a2a",
                fg="#ff6b6b"
            ).pack(side="left", padx=3)
    
    return frame


def get_percentile_color(percentile):
    """Get color for a percentile value"""
    for tier_key, tier_info in PERCENTILE_TIERS.items():
        if tier_info["min"] <= percentile <= tier_info["max"]:
            return tier_info["color"]
    return "#d4d4d4"
