# Player Card with Percentile View
# Display detailed player info with percentile rankings

import tkinter as tk
from tkinter import ttk
from percentiles import get_percentile_calculator, PERCENTILE_TIERS


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
    popup.geometry("600x500")
    popup.configure(bg="#1e1e1e")
    
    # Make it modal-ish
    popup.transient(parent)
    popup.grab_set()
    
    # Header with player name and basic info
    header_frame = tk.Frame(popup, bg="#1e1e1e")
    header_frame.pack(fill="x", padx=20, pady=15)
    
    name_label = tk.Label(
        header_frame,
        text=player.get("Name", "Unknown"),
        font=("Consolas", 16, "bold"),
        bg="#1e1e1e",
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
        bg="#1e1e1e",
        fg="#888888"
    )
    info_label.pack(anchor="w")
    
    # OVR/POT display
    ratings_frame = tk.Frame(header_frame, bg="#1e1e1e")
    ratings_frame.pack(anchor="w", pady=(10, 0))
    
    tk.Label(
        ratings_frame,
        text=f"OVR: {player.get('OVR', '-')}",
        font=("Consolas", 12, "bold"),
        bg="#1e1e1e",
        fg="#4dabf7"
    ).pack(side="left", padx=(0, 20))
    
    tk.Label(
        ratings_frame,
        text=f"POT: {player.get('POT', '-')}",
        font=("Consolas", 12, "bold"),
        bg="#1e1e1e",
        fg="#9775fa"
    ).pack(side="left")
    
    # Separator
    ttk.Separator(popup, orient="horizontal").pack(fill="x", padx=20, pady=10)
    
    # Percentile rankings
    percentile_frame = tk.Frame(popup, bg="#1e1e1e")
    percentile_frame.pack(fill="both", expand=True, padx=20, pady=10)
    
    tk.Label(
        percentile_frame,
        text="Percentile Rankings (League-Wide)",
        font=("Consolas", 12, "bold"),
        bg="#1e1e1e",
        fg="#d4d4d4"
    ).pack(anchor="w", pady=(0, 10))
    
    # Get percentiles
    calc = get_percentile_calculator()
    
    if player_type == "batter":
        percentiles = calc.get_batter_percentiles(player)
    else:
        percentiles = calc.get_pitcher_percentiles(player)
    
    # Scrollable frame for percentiles
    canvas = tk.Canvas(percentile_frame, bg="#1e1e1e", highlightthickness=0)
    scrollbar = ttk.Scrollbar(percentile_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg="#1e1e1e")
    
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
            row = tk.Frame(scrollable_frame, bg="#1e1e1e")
            row.pack(fill="x", pady=2)
            
            # Metric name
            tk.Label(
                row,
                text=f"{data['label']:>10}",
                font=("Consolas", 10),
                bg="#1e1e1e",
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
                bg="#1e1e1e",
                fg="#d4d4d4",
                width=8
            ).pack(side="left")
            
            # Percentile
            tk.Label(
                row,
                text=f"{data['percentile']:>3}th",
                font=("Consolas", 10),
                bg="#1e1e1e",
                fg="#d4d4d4",
                width=6
            ).pack(side="left", padx=5)
            
            # Bar
            tier = data["tier"]
            tk.Label(
                row,
                text=data["bar"],
                font=("Consolas", 10),
                bg="#1e1e1e",
                fg=tier["color"],
                width=22
            ).pack(side="left")
            
            # Tier icon and label
            tk.Label(
                row,
                text=f"{tier['icon']} {tier['label']}",
                font=("Consolas", 10),
                bg="#1e1e1e",
                fg=tier["color"],
                width=14
            ).pack(side="left")
    else:
        tk.Label(
            scrollable_frame,
            text="No percentile data available.\nLoad player data and try again.",
            font=("Consolas", 11),
            bg="#1e1e1e",
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
