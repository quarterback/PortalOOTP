# Trade Builder Tab
# Redesigned Trade Finder with interactive interface for building and evaluating trades
# Features park-adjusted player ratings and multiple trade matching modes

import tkinter as tk
from tkinter import ttk
from .style import on_treeview_motion, on_leave, sort_treeview
from .widgets import (
    make_treeview_open_link_handler,
    load_player_url_template,
)
from .tooltips import add_button_tooltip
from trade_value import parse_number, parse_years_left, get_contract_status, parse_salary
from team_parser import (
    calculate_surplus_value, get_surplus_tier, get_park_factor_context,
    calculate_comprehensive_trade_value, calculate_trade_grade,
    find_hidden_gem_trade_targets
)
from player_utils import parse_star_rating
from batters import calculate_park_adjusted_batter_score, get_park_impact_preview
from pitchers import calculate_park_adjusted_pitcher_score, get_pitcher_park_impact_preview

player_url_template = load_player_url_template()

# Trade mode constants
# Trade mode constants
TRADE_MODE_FAIR = "fair"
TRADE_MODE_BUY_LOW = "buy_low"
TRADE_MODE_FLEECE = "fleece"

# Search results limit
MAX_SEARCH_RESULTS = 50

# Trade mode descriptions
TRADE_MODES = {
    TRADE_MODE_FAIR: {
        "icon": "⚖️",
        "name": "Fair Trade",
        "description": "Returns players of equal value (±10% tolerance)",
        "tolerance": 0.10,
    },
    TRADE_MODE_BUY_LOW: {
        "icon": "📈",
        "name": "Buy Low",
        "description": "Prioritizes undervalued players (seller teams, park-suppressed stats)",
        "tolerance": 0.25,
    },
    TRADE_MODE_FLEECE: {
        "icon": "🎰",
        "name": "Fleece Mode",
        "description": "Returns players where you get significantly more value (for fun)",
        "tolerance": 0.50,
    },
}


def add_trade_builder_tab(notebook, font):
    """Add the redesigned Trade Builder tab with three-panel layout."""
    trade_builder_frame = ttk.Frame(notebook)
    notebook.add(trade_builder_frame, text="🔄 Trade Builder")
    
    # Data storage
    all_pitchers = []
    all_batters = []
    teams_data = {}  # Team data keyed by abbreviation
    
    # Trade state
    your_team_var = tk.StringVar(value="")
    trade_mode_var = tk.StringVar(value=TRADE_MODE_FAIR)
    selected_assets = []  # Players you're trading away
    selected_targets = []  # Players you're receiving
    
    # ID maps for treeview
    assets_id_map = {}
    targets_id_map = {}
    results_id_map = {}
    
    # ========================================================================
    # Main Container with Three Panels
    # ========================================================================
    main_container = tk.PanedWindow(
        trade_builder_frame,
        orient="horizontal",
        bg="#1e1e1e",
        sashwidth=4,
        sashrelief="flat"
    )
    main_container.pack(fill="both", expand=True, padx=5, pady=5)
    
    # ========================================================================
    # Left Panel: Your Trade Assets
    # ========================================================================
    left_panel = tk.Frame(main_container, bg="#1e1e1e", relief="ridge", bd=2)
    main_container.add(left_panel, width=450)
    
    # Left Panel Header
    left_header = tk.Frame(left_panel, bg="#1e1e1e")
    left_header.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        left_header,
        text="📤 Your Trade Assets",
        font=(font[0], font[1] + 2, "bold"),
        bg="#1e1e1e",
        fg="#00ff7f"
    ).pack(side="left")
    
    # Team Selector
    team_selector_frame = tk.Frame(left_panel, bg="#1e1e1e")
    team_selector_frame.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        team_selector_frame,
        text="Select Your Team:",
        bg="#1e1e1e",
        fg="#d4d4d4",
        font=font
    ).pack(side="left", padx=(0, 5))
    
    team_combo = ttk.Combobox(
        team_selector_frame,
        textvariable=your_team_var,
        values=[],
        state="readonly",
        width=20
    )
    team_combo.pack(side="left", padx=5)
    
    # Player List for Your Team (all players from selected team)
    player_list_frame = tk.Frame(left_panel, bg="#1e1e1e")
    player_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Player list with scrollbars
    player_vsb = ttk.Scrollbar(player_list_frame, orient="vertical")
    player_vsb.pack(side="right", fill="y")
    
    player_hsb = ttk.Scrollbar(player_list_frame, orient="horizontal")
    player_hsb.pack(side="bottom", fill="x")
    
    player_cols = ("✓", "Name", "POS", "Age", "OVR", "Salary", "YL", "Surplus", "ParkAdj")
    player_table = ttk.Treeview(
        player_list_frame,
        columns=player_cols,
        show="headings",
        yscrollcommand=player_vsb.set,
        xscrollcommand=player_hsb.set,
        height=12
    )
    player_table.pack(side="left", fill="both", expand=True)
    player_vsb.config(command=player_table.yview)
    player_hsb.config(command=player_table.xview)
    
    player_col_widths = {
        "✓": 25, "Name": 130, "POS": 40, "Age": 35, 
        "OVR": 40, "Salary": 65, "YL": 35, "Surplus": 60, "ParkAdj": 60
    }
    for col in player_cols:
        player_table.heading(col, text=col, command=lambda c=col: sort_treeview(player_table, c, False))
        player_table.column(col, width=player_col_widths.get(col, 60), minwidth=25, anchor="center", stretch=True)
    
    player_table.tag_configure("hover", background="#333")
    player_table.tag_configure("selected_asset", background="#2d4a2d")  # Green for selected
    player_table.tag_configure("hidden_gem", background="#4a3d2d")  # Brown for hidden gems
    player_table._prev_hover = None
    player_table.bind("<Motion>", on_treeview_motion)
    player_table.bind("<Leave>", on_leave)
    
    # Selected Assets Section
    selected_assets_frame = tk.Frame(left_panel, bg="#1e1e1e", relief="groove", bd=1)
    selected_assets_frame.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        selected_assets_frame,
        text="Selected to Trade Away:",
        font=(font[0], font[1], "bold"),
        bg="#1e1e1e",
        fg="#ffd43b"
    ).pack(anchor="w", padx=5, pady=2)
    
    assets_list_frame = tk.Frame(selected_assets_frame, bg="#1e1e1e")
    assets_list_frame.pack(fill="x", padx=5, pady=2)
    
    assets_cols = ("Name", "POS", "Value")
    assets_table = ttk.Treeview(
        assets_list_frame,
        columns=assets_cols,
        show="headings",
        height=4
    )
    assets_table.pack(fill="x")
    
    for col in assets_cols:
        assets_table.heading(col, text=col)
        assets_table.column(col, width=80, anchor="center")
    
    # Running Total
    total_offered_var = tk.StringVar(value="Total Value Offered: 0")
    total_offered_label = tk.Label(
        selected_assets_frame,
        textvariable=total_offered_var,
        font=(font[0], font[1], "bold"),
        bg="#1e1e1e",
        fg="#00ff7f"
    )
    total_offered_label.pack(anchor="w", padx=5, pady=5)
    
    # ========================================================================
    # Right Panel: Trade Targets / Search Results
    # ========================================================================
    right_panel = tk.Frame(main_container, bg="#1e1e1e", relief="ridge", bd=2)
    main_container.add(right_panel, width=500)
    
    # Right Panel Header
    right_header = tk.Frame(right_panel, bg="#1e1e1e")
    right_header.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        right_header,
        text="📥 Trade Targets",
        font=(font[0], font[1] + 2, "bold"),
        bg="#1e1e1e",
        fg="#00ff7f"
    ).pack(side="left")
    
    # Filter Controls
    filter_frame = tk.Frame(right_panel, bg="#1e1e1e")
    filter_frame.pack(fill="x", padx=5, pady=5)
    
    # Position filter
    pos_filter_frame = tk.Frame(filter_frame, bg="#1e1e1e")
    pos_filter_frame.pack(fill="x", pady=2)
    
    tk.Label(
        pos_filter_frame,
        text="Position:",
        bg="#1e1e1e",
        fg="#d4d4d4",
        font=font
    ).pack(side="left")
    
    position_var = tk.StringVar(value="All")
    pos_combo = ttk.Combobox(
        pos_filter_frame,
        textvariable=position_var,
        values=["All", "SP", "RP", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"],
        state="readonly",
        width=8
    )
    pos_combo.pack(side="left", padx=5)
    
    # Age range
    tk.Label(
        pos_filter_frame,
        text="Age:",
        bg="#1e1e1e",
        fg="#d4d4d4",
        font=font
    ).pack(side="left", padx=(10, 0))
    
    min_age_var = tk.StringVar(value="18")
    min_age_entry = tk.Entry(pos_filter_frame, textvariable=min_age_var, width=4, bg="#000000", fg="#d4d4d4", font=font)
    min_age_entry.pack(side="left", padx=2)
    
    tk.Label(pos_filter_frame, text="-", bg="#1e1e1e", fg="#d4d4d4").pack(side="left")
    
    max_age_var = tk.StringVar(value="40")
    max_age_entry = tk.Entry(pos_filter_frame, textvariable=max_age_var, width=4, bg="#000000", fg="#d4d4d4", font=font)
    max_age_entry.pack(side="left", padx=2)
    
    # Team Status filter
    status_filter_frame = tk.Frame(filter_frame, bg="#1e1e1e")
    status_filter_frame.pack(fill="x", pady=2)
    
    tk.Label(
        status_filter_frame,
        text="Team Status:",
        bg="#1e1e1e",
        fg="#d4d4d4",
        font=font
    ).pack(side="left")
    
    team_status_var = tk.StringVar(value="All")
    status_combo = ttk.Combobox(
        status_filter_frame,
        textvariable=team_status_var,
        values=["All", "Sellers", "Buyers", "Neutral"],
        state="readonly",
        width=10
    )
    status_combo.pack(side="left", padx=5)
    
    # Min OVR
    tk.Label(
        status_filter_frame,
        text="Min OVR:",
        bg="#1e1e1e",
        fg="#d4d4d4",
        font=font
    ).pack(side="left", padx=(10, 0))
    
    min_ovr_var = tk.StringVar(value="0")
    min_ovr_entry = tk.Entry(status_filter_frame, textvariable=min_ovr_var, width=4, bg="#000000", fg="#d4d4d4", font=font)
    min_ovr_entry.pack(side="left", padx=2)
    
    # Trade Mode Toggle
    mode_frame = tk.Frame(right_panel, bg="#1e1e1e")
    mode_frame.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        mode_frame,
        text="Trade Mode:",
        font=(font[0], font[1], "bold"),
        bg="#1e1e1e",
        fg="#d4d4d4"
    ).pack(side="left")
    
    for mode_key, mode_info in TRADE_MODES.items():
        rb = tk.Radiobutton(
            mode_frame,
            text=f"{mode_info['icon']} {mode_info['name']}",
            variable=trade_mode_var,
            value=mode_key,
            bg="#1e1e1e",
            fg="#d4d4d4",
            selectcolor="#2a2a2a",
            activebackground="#1e1e1e",
            activeforeground="#00ff7f",
            font=font
        )
        rb.pack(side="left", padx=5)
    
    # Search Button
    search_btn = ttk.Button(mode_frame, text="🔍 Find Matches")
    search_btn.pack(side="right", padx=5)
    
    # Results List
    results_frame = tk.Frame(right_panel, bg="#1e1e1e")
    results_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    results_vsb = ttk.Scrollbar(results_frame, orient="vertical")
    results_vsb.pack(side="right", fill="y")
    
    results_hsb = ttk.Scrollbar(results_frame, orient="horizontal")
    results_hsb.pack(side="bottom", fill="x")
    
    results_cols = ("✓", "Name", "POS", "Team", "Age", "OVR", "Salary", "Surplus", "Match")
    results_table = ttk.Treeview(
        results_frame,
        columns=results_cols,
        show="headings",
        yscrollcommand=results_vsb.set,
        xscrollcommand=results_hsb.set,
        height=10
    )
    results_table.pack(side="left", fill="both", expand=True)
    results_vsb.config(command=results_table.yview)
    results_hsb.config(command=results_table.xview)
    
    results_col_widths = {
        "✓": 25, "Name": 120, "POS": 40, "Team": 50, "Age": 35,
        "OVR": 40, "Salary": 60, "Surplus": 60, "Match": 50
    }
    for col in results_cols:
        results_table.heading(col, text=col, command=lambda c=col: sort_treeview(results_table, c, False))
        results_table.column(col, width=results_col_widths.get(col, 60), minwidth=25, anchor="center", stretch=True)
    
    results_table.tag_configure("hover", background="#333")
    results_table.tag_configure("hidden_gem", background="#4a3d2d")  # Brown for hidden gems
    results_table.tag_configure("good_match", background="#2d4a2d")  # Green for good matches
    results_table.tag_configure("great_match", background="#1a5a1a")  # Darker green for great matches
    results_table._prev_hover = None
    results_table.bind("<Motion>", on_treeview_motion)
    results_table.bind("<Leave>", on_leave)
    
    # Selected Targets Section
    selected_targets_frame = tk.Frame(right_panel, bg="#1e1e1e", relief="groove", bd=1)
    selected_targets_frame.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        selected_targets_frame,
        text="Selected to Receive:",
        font=(font[0], font[1], "bold"),
        bg="#1e1e1e",
        fg="#4dabf7"
    ).pack(anchor="w", padx=5, pady=2)
    
    targets_list_frame = tk.Frame(selected_targets_frame, bg="#1e1e1e")
    targets_list_frame.pack(fill="x", padx=5, pady=2)
    
    targets_cols = ("Name", "POS", "Value")
    targets_table = ttk.Treeview(
        targets_list_frame,
        columns=targets_cols,
        show="headings",
        height=4
    )
    targets_table.pack(fill="x")
    
    for col in targets_cols:
        targets_table.heading(col, text=col)
        targets_table.column(col, width=80, anchor="center")
    
    total_received_var = tk.StringVar(value="Total Value Received: 0")
    total_received_label = tk.Label(
        selected_targets_frame,
        textvariable=total_received_var,
        font=(font[0], font[1], "bold"),
        bg="#1e1e1e",
        fg="#4dabf7"
    )
    total_received_label.pack(anchor="w", padx=5, pady=5)
    
    # ========================================================================
    # Bottom Panel: Trade Summary
    # ========================================================================
    bottom_panel = tk.Frame(trade_builder_frame, bg="#1e1e1e", relief="ridge", bd=2)
    bottom_panel.pack(fill="x", padx=5, pady=5)
    
    # Trade Summary Header
    summary_header = tk.Frame(bottom_panel, bg="#1e1e1e")
    summary_header.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        summary_header,
        text="📊 Trade Summary",
        font=(font[0], font[1] + 2, "bold"),
        bg="#1e1e1e",
        fg="#00ff7f"
    ).pack(side="left")
    
    # Side-by-side comparison
    comparison_frame = tk.Frame(bottom_panel, bg="#1e1e1e")
    comparison_frame.pack(fill="x", padx=5, pady=5)
    
    # Left side: Players you're trading away
    trade_away_frame = tk.Frame(comparison_frame, bg="#1e1e1e")
    trade_away_frame.pack(side="left", fill="both", expand=True)
    
    trade_away_header = tk.Label(
        trade_away_frame,
        text="Trading Away",
        font=(font[0], font[1], "bold"),
        bg="#1e1e1e",
        fg="#ff6b6b"
    )
    trade_away_header.pack(anchor="w")
    
    trade_away_list = tk.Label(
        trade_away_frame,
        text="(No players selected)",
        bg="#1e1e1e",
        fg="#d4d4d4",
        font=font,
        justify="left",
        anchor="w"
    )
    trade_away_list.pack(anchor="w")
    
    # Separator
    tk.Label(comparison_frame, text="  ⟷  ", bg="#1e1e1e", fg="#d4d4d4", font=(font[0], font[1] + 4)).pack(side="left")
    
    # Right side: Players you're receiving
    receive_frame = tk.Frame(comparison_frame, bg="#1e1e1e")
    receive_frame.pack(side="left", fill="both", expand=True)
    
    receive_header = tk.Label(
        receive_frame,
        text="Receiving",
        font=(font[0], font[1], "bold"),
        bg="#1e1e1e",
        fg="#51cf66"
    )
    receive_header.pack(anchor="w")
    
    receive_list = tk.Label(
        receive_frame,
        text="(No players selected)",
        bg="#1e1e1e",
        fg="#d4d4d4",
        font=font,
        justify="left",
        anchor="w"
    )
    receive_list.pack(anchor="w")
    
    # Trade Grade
    grade_frame = tk.Frame(bottom_panel, bg="#1e1e1e")
    grade_frame.pack(fill="x", padx=5, pady=5)
    
    grade_label = tk.Label(
        grade_frame,
        text="Trade Grade: --",
        font=(font[0], font[1] + 4, "bold"),
        bg="#1e1e1e",
        fg="#d4d4d4"
    )
    grade_label.pack(side="left", padx=5)
    
    grade_description = tk.Label(
        grade_frame,
        text="",
        font=font,
        bg="#1e1e1e",
        fg="#888888"
    )
    grade_description.pack(side="left", padx=10)
    
    # Park Factor Impact Preview
    park_impact_frame = tk.Frame(bottom_panel, bg="#1e1e1e")
    park_impact_frame.pack(fill="x", padx=5, pady=5)
    
    park_impact_label = tk.Label(
        park_impact_frame,
        text="Park Factor Impact:",
        font=(font[0], font[1], "bold"),
        bg="#1e1e1e",
        fg="#ffd43b"
    )
    park_impact_label.pack(side="left")
    
    park_impact_details = tk.Label(
        park_impact_frame,
        text="(Select players to see park impact preview)",
        font=font,
        bg="#1e1e1e",
        fg="#888888"
    )
    park_impact_details.pack(side="left", padx=10)
    
    # Clear Trade Button
    clear_btn = ttk.Button(grade_frame, text="🗑️ Clear Trade")
    clear_btn.pack(side="right", padx=5)
    
    # ========================================================================
    # Helper Functions
    # ========================================================================
    
    def get_player_trade_value(player, player_type):
        """Calculate comprehensive trade value for a player."""
        return calculate_comprehensive_trade_value(player, teams_data, player_type)
    
    def get_all_teams():
        """Get list of all teams from players."""
        teams = set()
        for p in all_pitchers:
            team = p.get("ORG", "")
            if team:
                teams.add(team)
        for b in all_batters:
            team = b.get("ORG", "")
            if team:
                teams.add(team)
        return sorted(list(teams))
    
    def update_team_dropdown():
        """Update team dropdown with available teams."""
        teams = get_all_teams()
        team_combo['values'] = teams
        if teams and not your_team_var.get():
            your_team_var.set(teams[0])
    
    def get_players_for_team(team_abbr):
        """Get all players (pitchers and batters) for a team."""
        players = []
        
        for p in all_pitchers:
            if p.get("ORG", "") == team_abbr:
                player_data = p.copy()
                player_data["_type"] = "pitcher"
                players.append(player_data)
        
        for b in all_batters:
            if b.get("ORG", "") == team_abbr:
                player_data = b.copy()
                player_data["_type"] = "batter"
                players.append(player_data)
        
        return players
    
    def update_player_list():
        """Update the player list for the selected team."""
        player_table.delete(*player_table.get_children())
        assets_id_map.clear()
        
        team = your_team_var.get()
        if not team:
            return
        
        players = get_players_for_team(team)
        team_info = teams_data.get(team, {})
        
        for player in players:
            player_type = player.get("_type", "batter")
            
            # Calculate trade value
            trade_val = get_player_trade_value(player, player_type)
            
            # Get park adjustment
            if player_type == "batter":
                park_adj = calculate_park_adjusted_batter_score(player, team_info)
            else:
                park_adj = calculate_park_adjusted_pitcher_score(player, team_info)
            
            # Check if player is in selected assets
            is_selected = any(
                a.get("Name") == player.get("Name") and a.get("ORG") == player.get("ORG")
                for a in selected_assets
            )
            
            # Get basic info
            name = player.get("Name", "")
            pos = player.get("POS", "")
            try:
                age = int(player.get("Age", 0))
            except (ValueError, TypeError):
                age = 0
            
            ovr = parse_star_rating(player.get("OVR", "0"))
            salary = parse_salary(player.get("SLR", 0))
            
            yl_data = parse_years_left(player.get("YL", ""))
            yl = yl_data.get("years", 0)
            
            surplus = trade_val.get("base_surplus_value", 0)
            park_bonus = park_adj.get("park_adjustment_bonus", 0)
            
            # Format values
            check = "☑" if is_selected else "☐"
            salary_str = f"${salary:.1f}M" if salary > 0 else "-"
            surplus_str = f"+${surplus:.1f}M" if surplus >= 0 else f"-${abs(surplus):.1f}M"
            park_str = f"+{park_bonus:.1f}" if park_bonus > 0 else f"{park_bonus:.1f}" if park_bonus < 0 else "0"
            
            values = (
                check,
                name,
                pos,
                age,
                f"{ovr:.1f}",
                salary_str,
                yl,
                surplus_str,
                park_str
            )
            
            tags = []
            if is_selected:
                tags.append("selected_asset")
            if park_adj.get("is_hidden_gem", False):
                tags.append("hidden_gem")
            
            iid = player_table.insert("", "end", values=values, tags=tags if tags else ())
            assets_id_map[iid] = player
    
    def toggle_player_selection(event):
        """Toggle player selection when clicked."""
        region = player_table.identify_region(event.x, event.y)
        if region != "cell":
            return
        
        item = player_table.identify_row(event.y)
        if not item:
            return
        
        player = assets_id_map.get(item)
        if not player:
            return
        
        # Check if already selected
        is_selected = any(
            a.get("Name") == player.get("Name") and a.get("ORG") == player.get("ORG")
            for a in selected_assets
        )
        
        if is_selected:
            # Remove from selected
            selected_assets[:] = [
                a for a in selected_assets
                if not (a.get("Name") == player.get("Name") and a.get("ORG") == player.get("ORG"))
            ]
        else:
            # Add to selected
            selected_assets.append(player)
        
        update_player_list()
        update_selected_assets_display()
        update_trade_summary()
    
    def update_selected_assets_display():
        """Update the selected assets display."""
        assets_table.delete(*assets_table.get_children())
        
        total_value = 0
        
        for player in selected_assets:
            player_type = player.get("_type", "batter")
            trade_val = get_player_trade_value(player, player_type)
            value = trade_val.get("total_trade_value", 0)
            total_value += value
            
            values = (
                player.get("Name", ""),
                player.get("POS", ""),
                f"{value:.1f}"
            )
            assets_table.insert("", "end", values=values)
        
        total_offered_var.set(f"Total Value Offered: {total_value:.1f}")
    
    def find_matching_players():
        """Find players matching the trade criteria."""
        results_table.delete(*results_table.get_children())
        results_id_map.clear()
        
        # Get filter values
        pos_filter = position_var.get()
        status_filter = team_status_var.get().lower()
        trade_mode = trade_mode_var.get()
        your_team = your_team_var.get()
        
        try:
            min_age = int(min_age_var.get())
        except ValueError:
            min_age = 18
        
        try:
            max_age = int(max_age_var.get())
        except ValueError:
            max_age = 40
        
        try:
            min_ovr = float(min_ovr_var.get())
        except ValueError:
            min_ovr = 0
        
        # Calculate total offered value
        total_offered = sum(
            get_player_trade_value(p, p.get("_type", "batter")).get("total_trade_value", 0)
            for p in selected_assets
        )
        
        # Get mode tolerance
        mode_info = TRADE_MODES.get(trade_mode, TRADE_MODES[TRADE_MODE_FAIR])
        tolerance = mode_info.get("tolerance", 0.10)
        
        # Combine all players
        all_players = []
        for p in all_pitchers:
            player_data = p.copy()
            player_data["_type"] = "pitcher"
            all_players.append(player_data)
        
        for b in all_batters:
            player_data = b.copy()
            player_data["_type"] = "batter"
            all_players.append(player_data)
        
        # Filter and score players
        matching_players = []
        
        for player in all_players:
            # Skip players from your team
            if player.get("ORG", "") == your_team:
                continue
            
            # Skip players already in selected assets
            if any(
                a.get("Name") == player.get("Name") and a.get("ORG") == player.get("ORG")
                for a in selected_assets
            ):
                continue
            
            # Position filter
            pos = player.get("POS", "")
            if pos_filter != "All" and pos != pos_filter:
                continue
            
            # Age filter
            try:
                age = int(player.get("Age", 0))
            except (ValueError, TypeError):
                age = 0
            
            if not (min_age <= age <= max_age):
                continue
            
            # OVR filter
            ovr = parse_star_rating(player.get("OVR", "0"))
            if ovr < min_ovr:
                continue
            
            # Team status filter
            team_abbr = player.get("ORG", "")
            team_info = teams_data.get(team_abbr, {})
            team_status = team_info.get("status", "neutral")
            
            if status_filter == "sellers" and team_status != "seller":
                continue
            elif status_filter == "buyers" and team_status != "buyer":
                continue
            elif status_filter == "neutral" and team_status != "neutral":
                continue
            
            # Calculate player value
            player_type = player.get("_type", "batter")
            trade_val = get_player_trade_value(player, player_type)
            player_value = trade_val.get("total_trade_value", 0)
            
            # Check if value matches based on mode
            if total_offered > 0:
                if trade_mode == TRADE_MODE_FAIR:
                    # Fair trade: within ±tolerance of offered value
                    min_val = total_offered * (1 - tolerance)
                    max_val = total_offered * (1 + tolerance)
                    if not (min_val <= player_value <= max_val):
                        continue
                    match_score = 100 - abs(player_value - total_offered) / total_offered * 100
                
                elif trade_mode == TRADE_MODE_BUY_LOW:
                    # Buy low: prioritize undervalued players
                    # Include players valued lower than offered, or hidden gems
                    is_hidden_gem = trade_val.get("is_hidden_gem", False)
                    if player_value > total_offered * (1 + tolerance) and not is_hidden_gem:
                        continue
                    
                    # Score based on surplus value and hidden gem status
                    surplus = trade_val.get("base_surplus_value", 0)
                    match_score = 50 + min(25, surplus * 2)
                    if is_hidden_gem:
                        match_score += 25
                    if team_status == "seller":
                        match_score += 10
                
                elif trade_mode == TRADE_MODE_FLEECE:
                    # Fleece mode: return players where you get significantly more value
                    if player_value < total_offered * 1.20:
                        continue
                    match_score = min(100, (player_value / total_offered - 1) * 100)
                
                else:
                    match_score = 50
            else:
                # No assets selected, show all matching players
                match_score = 50
            
            # Get park adjustment info
            if player_type == "batter":
                park_adj = calculate_park_adjusted_batter_score(player, team_info)
            else:
                park_adj = calculate_park_adjusted_pitcher_score(player, team_info)
            
            matching_players.append({
                "player": player,
                "value": player_value,
                "match_score": match_score,
                "is_hidden_gem": trade_val.get("is_hidden_gem", False) or park_adj.get("is_hidden_gem", False),
                "surplus": trade_val.get("base_surplus_value", 0),
                "team_status": team_status,
            })
        
        # Sort by match score
        matching_players.sort(key=lambda x: x["match_score"], reverse=True)
        
        # Display results
        for mp in matching_players[:MAX_SEARCH_RESULTS]:
            player = mp["player"]
            
            # Check if in selected targets
            is_selected = any(
                t.get("Name") == player.get("Name") and t.get("ORG") == player.get("ORG")
                for t in selected_targets
            )
            
            check = "☑" if is_selected else "☐"
            name = player.get("Name", "")
            pos = player.get("POS", "")
            team = player.get("ORG", "")
            
            try:
                age = int(player.get("Age", 0))
            except (ValueError, TypeError):
                age = 0
            
            ovr = parse_star_rating(player.get("OVR", "0"))
            salary = parse_salary(player.get("SLR", 0))
            
            salary_str = f"${salary:.1f}M" if salary > 0 else "-"
            surplus = mp["surplus"]
            surplus_str = f"+${surplus:.1f}M" if surplus >= 0 else f"-${abs(surplus):.1f}M"
            match_str = f"{mp['match_score']:.0f}%"
            
            values = (
                check,
                name,
                pos,
                team,
                age,
                f"{ovr:.1f}",
                salary_str,
                surplus_str,
                match_str
            )
            
            tags = []
            if is_selected:
                tags.append("good_match")
            if mp["is_hidden_gem"]:
                tags.append("hidden_gem")
            elif mp["match_score"] >= 80:
                tags.append("great_match")
            elif mp["match_score"] >= 60:
                tags.append("good_match")
            
            iid = results_table.insert("", "end", values=values, tags=tags if tags else ())
            results_id_map[iid] = player
    
    def toggle_target_selection(event):
        """Toggle target player selection when clicked."""
        region = results_table.identify_region(event.x, event.y)
        if region != "cell":
            return
        
        item = results_table.identify_row(event.y)
        if not item:
            return
        
        player = results_id_map.get(item)
        if not player:
            return
        
        # Check if already selected
        is_selected = any(
            t.get("Name") == player.get("Name") and t.get("ORG") == player.get("ORG")
            for t in selected_targets
        )
        
        if is_selected:
            # Remove from selected
            selected_targets[:] = [
                t for t in selected_targets
                if not (t.get("Name") == player.get("Name") and t.get("ORG") == player.get("ORG"))
            ]
        else:
            # Add to selected
            selected_targets.append(player)
        
        find_matching_players()  # Refresh to update checkmarks
        update_selected_targets_display()
        update_trade_summary()
    
    def update_selected_targets_display():
        """Update the selected targets display."""
        targets_table.delete(*targets_table.get_children())
        
        total_value = 0
        
        for player in selected_targets:
            player_type = player.get("_type", "batter")
            trade_val = get_player_trade_value(player, player_type)
            value = trade_val.get("total_trade_value", 0)
            total_value += value
            
            values = (
                player.get("Name", ""),
                player.get("POS", ""),
                f"{value:.1f}"
            )
            targets_table.insert("", "end", values=values)
        
        total_received_var.set(f"Total Value Received: {total_value:.1f}")
    
    def update_trade_summary():
        """Update the trade summary panel."""
        # Update trade away list
        if selected_assets:
            names = [f"• {p.get('Name', '')} ({p.get('POS', '')})" for p in selected_assets]
            trade_away_list.config(text="\n".join(names))
        else:
            trade_away_list.config(text="(No players selected)")
        
        # Update receive list
        if selected_targets:
            names = [f"• {p.get('Name', '')} ({p.get('POS', '')})" for p in selected_targets]
            receive_list.config(text="\n".join(names))
        else:
            receive_list.config(text="(No players selected)")
        
        # Calculate trade grade
        total_offered = sum(
            get_player_trade_value(p, p.get("_type", "batter")).get("total_trade_value", 0)
            for p in selected_assets
        )
        
        total_received = sum(
            get_player_trade_value(p, p.get("_type", "batter")).get("total_trade_value", 0)
            for p in selected_targets
        )
        
        if total_offered > 0 and total_received > 0:
            grade_info = calculate_trade_grade(total_offered, total_received)
            grade_label.config(
                text=f"Trade Grade: {grade_info['grade']} ({grade_info['differential_pct']})",
                fg=grade_info['color']
            )
            grade_description.config(text=grade_info['description'])
        else:
            grade_label.config(text="Trade Grade: --", fg="#d4d4d4")
            grade_description.config(text="Select players on both sides to see grade")
        
        # Update park impact preview
        update_park_impact_preview()
    
    def update_park_impact_preview():
        """Update the park factor impact preview."""
        if not selected_targets:
            park_impact_details.config(text="(Select players to see park impact preview)")
            return
        
        your_team = your_team_var.get()
        your_team_info = teams_data.get(your_team, {})
        
        impact_parts = []
        
        for player in selected_targets[:3]:  # Show first 3 players
            player_type = player.get("_type", "batter")
            old_team = player.get("ORG", "")
            old_team_info = teams_data.get(old_team, {})
            
            if player_type == "batter":
                impact = get_park_impact_preview(player, old_team_info, your_team_info)
            else:
                impact = get_pitcher_park_impact_preview(player, old_team_info, your_team_info)
            
            if impact.get("impact_level") != "minimal":
                name = player.get("Name", "").split()[-1]  # Last name
                impact_parts.append(f"{name}: {impact.get('description', '')}")
        
        if impact_parts:
            park_impact_details.config(text=" | ".join(impact_parts))
        else:
            park_impact_details.config(text="No significant park impact for selected players")
    
    def clear_trade():
        """Clear all trade selections."""
        selected_assets.clear()
        selected_targets.clear()
        update_player_list()
        update_selected_assets_display()
        update_selected_targets_display()
        results_table.delete(*results_table.get_children())
        results_id_map.clear()
        update_trade_summary()
    
    # ========================================================================
    # Event Bindings
    # ========================================================================
    
    player_table.bind("<Button-1>", toggle_player_selection)
    results_table.bind("<Button-1>", toggle_target_selection)
    
    team_combo.bind("<<ComboboxSelected>>", lambda e: update_player_list())
    search_btn.config(command=find_matching_players)
    clear_btn.config(command=clear_trade)
    
    # Set up double-click handlers for opening player pages
    make_treeview_open_link_handler(
        player_table, 
        {}, 
        lambda pid: player_url_template.format(pid=pid)
    )
    make_treeview_open_link_handler(
        results_table, 
        {}, 
        lambda pid: player_url_template.format(pid=pid)
    )
    
    # ========================================================================
    # Tab Controller Class
    # ========================================================================
    
    class TradeBuilderTab:
        def refresh(self, pitchers, batters, teams_by_abbr=None):
            all_pitchers.clear()
            all_batters.clear()
            teams_data.clear()
            
            all_pitchers.extend(pitchers)
            all_batters.extend(batters)
            
            if teams_by_abbr:
                teams_data.update(teams_by_abbr)
            
            update_team_dropdown()
            update_player_list()
            clear_trade()
    
    return TradeBuilderTab()
