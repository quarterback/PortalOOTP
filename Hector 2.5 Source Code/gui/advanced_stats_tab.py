# Advanced Stats Tab
# UI for stats-based player evaluation using advanced metrics

import tkinter as tk
from tkinter import ttk
from .style import on_treeview_motion, on_leave, sort_treeview
from .widgets import make_treeview_open_link_handler, load_player_url_template, bind_player_card_right_click
from advanced_stats import (
    add_advanced_stats_to_players,
    STAT_RANGES,
    BABIP_LUCKY_THRESHOLD,
    BABIP_UNLUCKY_THRESHOLD,
)

player_url_template = load_player_url_template()

# Indicator categories for filtering
INDICATOR_CATEGORIES = {
    "all": {
        "name": "All Players",
        "icon": "📊",
        "color": "#d4d4d4",
        "description": "Show all players"
    },
    "undervalued": {
        "name": "Undervalued",
        "icon": "💎",
        "color": "#51cf66",
        "description": "High stats, low OVR - may be underrated"
    },
    "regression_down": {
        "name": "Regression Risk",
        "icon": "📉",
        "color": "#ff6b6b",
        "description": "Lucky stats, likely to decline"
    },
    "regression_up": {
        "name": "Bounce Back",
        "icon": "📈",
        "color": "#4dabf7",
        "description": "Unlucky stats, likely to improve"
    },
    "breakout": {
        "name": "Breakout Candidates",
        "icon": "🚀",
        "color": "#ffd43b",
        "description": "Young with strong underlying metrics"
    },
}


def add_advanced_stats_tab(notebook, font):
    """Add the Advanced Stats tab to the notebook."""
    
    advanced_frame = ttk.Frame(notebook)
    notebook.add(advanced_frame, text="Advanced Stats")
    
    # Data storage
    all_pitchers = []
    all_batters = []
    current_player_type = {"value": "batter"}
    id_map = {}
    player_data_map = {}
    
    # Header
    header_frame = tk.Frame(advanced_frame, bg="#2d2d2d")
    header_frame.pack(fill="x", padx=10, pady=5)
    
    tk.Label(
        header_frame,
        text="📊 Advanced Stats Evaluation",
        font=(font[0], font[1] + 4, "bold"),
        bg="#2d2d2d",
        fg="#00ff7f"
    ).pack(side="left")
    
    tk.Label(
        header_frame,
        text="Stats-based player analysis with expected metrics",
        font=(font[0], font[1] - 1),
        bg="#2d2d2d",
        fg="#888888"
    ).pack(side="left", padx=(20, 0))
    
    # Controls frame
    controls_frame = tk.Frame(advanced_frame, bg="#2d2d2d")
    controls_frame.pack(fill="x", padx=10, pady=5)
    
    # Player type toggle
    tk.Label(controls_frame, text="Player Type:", bg="#2d2d2d", fg="#d4d4d4", font=font).pack(side="left")
    player_type_var = tk.StringVar(value="Batters")
    player_type_combo = ttk.Combobox(
        controls_frame,
        textvariable=player_type_var,
        values=["Batters", "Pitchers"],
        state="readonly",
        width=10
    )
    player_type_combo.pack(side="left", padx=5)
    
    # Indicator filter
    tk.Label(controls_frame, text="Filter:", bg="#2d2d2d", fg="#d4d4d4", font=font).pack(side="left", padx=(15, 0))
    indicator_var = tk.StringVar(value="All Players")
    indicator_options = [f"{info['icon']} {info['name']}" for info in INDICATOR_CATEGORIES.values()]
    indicator_combo = ttk.Combobox(
        controls_frame,
        textvariable=indicator_var,
        values=indicator_options,
        state="readonly",
        width=20
    )
    indicator_combo.set("📊 All Players")
    indicator_combo.pack(side="left", padx=5)
    
    # Position filter
    tk.Label(controls_frame, text="Position:", bg="#2d2d2d", fg="#d4d4d4", font=font).pack(side="left", padx=(15, 0))
    pos_var = tk.StringVar(value="All")
    pos_combo = ttk.Combobox(
        controls_frame,
        textvariable=pos_var,
        values=["All", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"],
        state="readonly",
        width=8
    )
    pos_combo.pack(side="left", padx=5)
    
    # Team filter
    tk.Label(controls_frame, text="Team:", bg="#2d2d2d", fg="#d4d4d4", font=font).pack(side="left", padx=(15, 0))
    team_var = tk.StringVar(value="All")
    team_combo = ttk.Combobox(
        controls_frame,
        textvariable=team_var,
        values=["All"],
        state="readonly",
        width=8
    )
    team_combo.pack(side="left", padx=5)
    
    # Age range filter
    tk.Label(controls_frame, text="Age:", bg="#2d2d2d", fg="#d4d4d4", font=font).pack(side="left", padx=(15, 0))
    min_age_var = tk.StringVar(value="18")
    max_age_var = tk.StringVar(value="45")
    tk.Entry(controls_frame, textvariable=min_age_var, width=3, bg="#000000", fg="#d4d4d4", font=font).pack(side="left", padx=2)
    tk.Label(controls_frame, text="-", bg="#2d2d2d", fg="#d4d4d4", font=font).pack(side="left")
    tk.Entry(controls_frame, textvariable=max_age_var, width=3, bg="#000000", fg="#d4d4d4", font=font).pack(side="left", padx=2)
    
    # Summary
    summary_var = tk.StringVar(value="")
    summary_label = tk.Label(
        controls_frame,
        textvariable=summary_var,
        font=font,
        bg="#2d2d2d",
        fg="#888888"
    )
    summary_label.pack(side="right", padx=10)
    
    # Main content area
    content_frame = tk.Frame(advanced_frame, bg="#2d2d2d")
    content_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
    # Left sidebar with indicator cards
    sidebar_frame = tk.Frame(content_frame, bg="#2d2d2d", width=180)
    sidebar_frame.pack(side="left", fill="y", padx=(0, 10))
    sidebar_frame.pack_propagate(False)
    
    tk.Label(
        sidebar_frame,
        text="Player Categories",
        font=(font[0], font[1] + 1, "bold"),
        bg="#2d2d2d",
        fg="#d4d4d4"
    ).pack(fill="x", pady=(0, 10))
    
    # Category count labels
    category_counts = {}
    
    def create_category_cards():
        """Create category summary cards in sidebar."""
        # Clear existing cards except title
        for widget in sidebar_frame.winfo_children():
            if isinstance(widget, tk.Frame):
                widget.destroy()
        
        for cat_key, cat_info in INDICATOR_CATEGORIES.items():
            count = category_counts.get(cat_key, 0)
            
            card = tk.Frame(sidebar_frame, bg="#2a2a2a", relief="raised", bd=1)
            card.pack(fill="x", pady=3)
            
            header = tk.Frame(card, bg="#2a2a2a")
            header.pack(fill="x", padx=5, pady=3)
            
            tk.Label(
                header,
                text=f"{cat_info['icon']} {cat_info['name']}",
                font=(font[0], font[1] - 1, "bold"),
                bg="#2a2a2a",
                fg=cat_info["color"]
            ).pack(side="left")
            
            tk.Label(
                header,
                text=f"({count})",
                font=(font[0], font[1] - 1),
                bg="#2a2a2a",
                fg="#888888"
            ).pack(side="right")
            
            # Make card clickable
            def on_card_click(event, key=cat_key):
                for opt in indicator_options:
                    if INDICATOR_CATEGORIES[key]["name"] in opt:
                        indicator_combo.set(opt)
                        break
                update_table()
            
            card.bind("<Button-1>", on_card_click)
            for child in card.winfo_children():
                child.bind("<Button-1>", on_card_click)
                for grandchild in child.winfo_children():
                    grandchild.bind("<Button-1>", on_card_click)
    
    # Right side - Results table
    table_container = tk.Frame(content_frame, bg="#2d2d2d")
    table_container.pack(side="right", fill="both", expand=True)
    
    # Create table
    table_frame = tk.Frame(table_container, bg="#2d2d2d")
    table_frame.pack(fill="both", expand=True)
    
    vsb = ttk.Scrollbar(table_frame, orient="vertical")
    vsb.pack(side="right", fill="y")
    
    hsb = ttk.Scrollbar(table_frame, orient="horizontal")
    hsb.pack(side="bottom", fill="x")
    
    # Batter columns
    batter_cols = (
        "Name", "Team", "POS", "Age", "OVR", "POT",
        "xBA", "xSLG", "xWOBA", "xOPS+",
        "Contact+", "Barrel%", "Plate_Skills",
        "Off.Rating", "Power-Speed", "Indicator"
    )
    
    # Pitcher columns  
    pitcher_cols = (
        "Name", "Team", "POS", "Age", "OVR", "POT",
        "Stuff+", "K/BB", "xERA", "Score",
        "Indicator"
    )
    
    table = ttk.Treeview(
        table_frame,
        columns=batter_cols,
        show="headings",
        yscrollcommand=vsb.set,
        xscrollcommand=hsb.set,
        height=22
    )
    table.pack(side="left", fill="both", expand=True)
    
    vsb.config(command=table.yview)
    hsb.config(command=table.xview)
    
    # Column widths
    batter_widths = {
        "Name": 140, "Team": 50, "POS": 40, "Age": 40, "OVR": 45, "POT": 45,
        "xBA": 55, "xSLG": 55, "xWOBA": 60, "xOPS+": 55,
        "Contact+": 65, "Barrel%": 60, "Plate_Skills": 75,
        "Off.Rating": 70, "Power-Speed": 80, "Indicator": 120
    }
    
    pitcher_widths = {
        "Name": 140, "Team": 50, "POS": 40, "Age": 40, "OVR": 45, "POT": 45,
        "Stuff+": 55, "K/BB": 50, "xERA": 50, "Score": 50,
        "Indicator": 120
    }
    
    def setup_batter_columns():
        """Configure table for batter view."""
        table["columns"] = batter_cols
        for col in batter_cols:
            table.heading(col, text=col, command=lambda c=col: sort_treeview(table, c, False))
            table.column(col, width=batter_widths.get(col, 60), minwidth=35, anchor="center", stretch=True)
    
    def setup_pitcher_columns():
        """Configure table for pitcher view."""
        table["columns"] = pitcher_cols
        for col in pitcher_cols:
            table.heading(col, text=col, command=lambda c=col: sort_treeview(table, c, False))
            table.column(col, width=pitcher_widths.get(col, 60), minwidth=35, anchor="center", stretch=True)
    
    # Initialize with batter columns
    setup_batter_columns()
    
    # Configure tags for indicators
    table.tag_configure("undervalued", foreground="#51cf66")
    table.tag_configure("regression_down", foreground="#ff6b6b")
    table.tag_configure("regression_up", foreground="#4dabf7")
    table.tag_configure("breakout", foreground="#ffd43b")
    table.tag_configure("normal", foreground="#d4d4d4")
    table.tag_configure("hover", background="#333")
    table._prev_hover = None
    table.bind("<Motion>", on_treeview_motion)
    table.bind("<Leave>", on_leave)
    
    PITCHER_POSITIONS = {"SP", "RP", "CL", "P"}
    
    def get_player_type_for_card(player):
        pos = player.get("POS", "").upper()
        return "pitcher" if pos in PITCHER_POSITIONS else "batter"
    
    bind_player_card_right_click(table, player_data_map, lambda p: (p, get_player_type_for_card(p)))
    
    def get_indicator_tag(player, player_type):
        """Get the indicator tag for a player."""
        advanced = player.get("advanced_stats", {})
        if not advanced:
            return "normal", "—"
        
        undervalued = advanced.get("Undervalued", {})
        regression = advanced.get("Regression", {})
        breakout = advanced.get("Breakout", {})
        
        # Priority order: undervalued > regression > breakout
        if undervalued.get("undervalued"):
            gap = undervalued.get("gap", 0)
            return "undervalued", f"💎 +{gap:.0f}"
        
        if regression.get("is_regression_candidate"):
            direction = regression.get("direction", "neutral")
            if direction == "down":
                return "regression_down", "📉 Regression"
            elif direction == "up":
                return "regression_up", "📈 Bounce Back"
        
        if breakout.get("is_breakout"):
            gap = breakout.get("upside_gap", 0)
            return "breakout", f"🚀 +{gap:.0f} upside"
        
        return "normal", "—"
    
    def matches_indicator_filter(player, filter_key, player_type):
        """Check if player matches the selected indicator filter."""
        if filter_key == "all":
            return True
        
        advanced = player.get("advanced_stats", {})
        if not advanced:
            return False
        
        undervalued = advanced.get("Undervalued", {})
        regression = advanced.get("Regression", {})
        breakout = advanced.get("Breakout", {})
        
        if filter_key == "undervalued":
            return undervalued.get("undervalued", False)
        elif filter_key == "regression_down":
            return regression.get("is_regression_candidate") and regression.get("direction") == "down"
        elif filter_key == "regression_up":
            return regression.get("is_regression_candidate") and regression.get("direction") == "up"
        elif filter_key == "breakout":
            return breakout.get("is_breakout", False)
        
        return True
    
    def get_filter_key_from_selection():
        """Convert combo selection to filter key."""
        selection = indicator_var.get()
        for key, info in INDICATOR_CATEGORIES.items():
            if info["name"] in selection:
                return key
        return "all"
    
    def update_category_counts(players, player_type):
        """Update category counts for sidebar cards."""
        category_counts.clear()
        category_counts["all"] = len(players)
        
        for key in INDICATOR_CATEGORIES:
            if key == "all":
                continue
            count = sum(1 for p in players if matches_indicator_filter(p, key, player_type))
            category_counts[key] = count
    
    def update_table():
        """Update the table with current filters."""
        table.delete(*table.get_children())
        id_map.clear()
        player_data_map.clear()
        
        is_batter = player_type_var.get() == "Batters"
        current_player_type["value"] = "batter" if is_batter else "pitcher"
        
        if is_batter:
            setup_batter_columns()
            players = all_batters
            # Update position filter options
            pos_combo["values"] = ["All", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"]
        else:
            setup_pitcher_columns()
            players = all_pitchers
            pos_combo["values"] = ["All", "SP", "RP", "CL"]
        
        # Apply filters
        pos_filter = pos_var.get()
        team_filter = team_var.get()
        indicator_filter = get_filter_key_from_selection()
        
        try:
            min_age = int(min_age_var.get())
            max_age = int(max_age_var.get())
        except ValueError:
            min_age = 18
            max_age = 45
        
        filtered_players = []
        for player in players:
            # Position filter
            if pos_filter != "All":
                player_pos = player.get("POS", "")
                if player_pos != pos_filter:
                    continue
            
            # Team filter
            if team_filter != "All":
                player_team = player.get("ORG", "")
                if player_team != team_filter:
                    continue
            
            # Age filter
            try:
                age = int(player.get("Age", 0))
                if not (min_age <= age <= max_age):
                    continue
            except (ValueError, TypeError):
                pass
            
            # Indicator filter
            if not matches_indicator_filter(player, indicator_filter, current_player_type["value"]):
                continue
            
            filtered_players.append(player)
        
        # Update category counts
        update_category_counts(players, current_player_type["value"])
        create_category_cards()
        
        # Sort by Offensive Rating (batters) or Pitcher Score (pitchers)
        if is_batter:
            filtered_players.sort(
                key=lambda p: p.get("advanced_stats", {}).get("Offensive_Rating", 0),
                reverse=True
            )
        else:
            filtered_players.sort(
                key=lambda p: p.get("advanced_stats", {}).get("Pitcher_Score", 0),
                reverse=True
            )
        
        # Populate table
        for player in filtered_players:
            advanced = player.get("advanced_stats", {})
            tag, indicator_text = get_indicator_tag(player, current_player_type["value"])
            
            if is_batter:
                values = (
                    player.get("Name", ""),
                    player.get("ORG", ""),
                    player.get("POS", ""),
                    player.get("Age", ""),
                    player.get("OVR", ""),
                    player.get("POT", ""),
                    f"{advanced.get('xBA', 0):.3f}",
                    f"{advanced.get('xSLG', 0):.3f}",
                    f"{advanced.get('xWOBA', 0):.3f}",
                    f"{advanced.get('xOPS+', 0):.0f}",
                    f"{advanced.get('Contact+', 0):.0f}",
                    f"{advanced.get('Barrel%', 0):.1f}",
                    f"{advanced.get('Plate_Skills', 0):.3f}",
                    f"{advanced.get('Offensive_Rating', 0):.0f}",
                    f"{advanced.get('Power_Speed', 0):.1f}",
                    indicator_text
                )
            else:
                values = (
                    player.get("Name", ""),
                    player.get("ORG", ""),
                    player.get("POS", ""),
                    player.get("Age", ""),
                    player.get("OVR", ""),
                    player.get("POT", ""),
                    f"{advanced.get('Stuff+', 0):.0f}",
                    f"{advanced.get('K/BB', 0):.2f}",
                    f"{advanced.get('xERA', 0):.2f}",
                    f"{advanced.get('Pitcher_Score', 0):.0f}",
                    indicator_text
                )
            
            iid = table.insert("", "end", values=values, tags=(tag,))
            player_id = player.get("ID", "")
            if player_id:
                id_map[iid] = player_id
            player_data_map[iid] = player
        
        summary_var.set(f"Showing {len(filtered_players)} of {len(players)} players")
        
        make_treeview_open_link_handler(table, id_map, lambda pid: player_url_template.format(pid=pid))
    
    def update_team_list():
        """Update the team filter dropdown with available teams."""
        teams = set()
        for player in all_batters + all_pitchers:
            team = player.get("ORG", "")
            if team:
                teams.add(team)
        team_list = ["All"] + sorted(teams)
        team_combo["values"] = team_list
    
    # Bind filter changes
    player_type_combo.bind("<<ComboboxSelected>>", lambda e: update_table())
    indicator_combo.bind("<<ComboboxSelected>>", lambda e: update_table())
    pos_combo.bind("<<ComboboxSelected>>", lambda e: update_table())
    team_combo.bind("<<ComboboxSelected>>", lambda e: update_table())
    
    # Bind age entry changes
    def on_age_change(*args):
        update_table()
    
    min_age_var.trace_add("write", on_age_change)
    max_age_var.trace_add("write", on_age_change)
    
    class AdvancedStatsTab:
        def refresh(self, pitchers, batters):
            all_pitchers.clear()
            all_batters.clear()
            
            # Add advanced stats to all players
            all_pitchers.extend(add_advanced_stats_to_players(list(pitchers), "pitcher"))
            all_batters.extend(add_advanced_stats_to_players(list(batters), "batter"))
            
            update_team_list()
            update_table()
    
    return AdvancedStatsTab()
