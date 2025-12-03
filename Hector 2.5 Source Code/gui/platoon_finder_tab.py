import tkinter as tk
from tkinter import ttk
from .style import on_treeview_motion, on_leave, sort_treeview
from .widgets import (
    make_treeview_open_link_handler,
    load_player_url_template,
    bind_player_card_right_click,
)
from .tooltips import add_button_tooltip

player_url_template = load_player_url_template()

# OVR range for platoon candidates (not stars, not scrubs)
PLATOON_OVR_MIN = 40
PLATOON_OVR_MAX = 55

# DH candidate thresholds
DH_BAT_MIN = 50  # Minimum batting ratings
DH_DEF_MAX = 40  # Maximum defensive ratings


def parse_number(value):
    """Parse numeric value, handling '-' and empty strings"""
    if not value or value == "-" or value == "":
        return 0.0
    try:
        val = str(value).replace(",", "").strip()
        # Handle star ratings
        if "Stars" in val:
            return float(val.split()[0])
        return float(val)
    except (ValueError, AttributeError):
        return 0.0


def parse_star_rating(val):
    """Convert star rating string to numeric value (0-80 or 0-10 scale)"""
    if not val:
        return 0.0
    val = str(val).strip()
    if "Stars" in val:
        try:
            return float(val.split()[0]) * 10  # Convert 1-5 stars to 10-50 scale
        except:
            return 0.0
    try:
        return float(val)
    except:
        return 0.0


def add_platoon_finder_tab(notebook, font):
    """
    Platoon Finder Tab - Identify platoon opportunities
    
    Features:
    - Platoon partner matching (L vs R batters at same position)
    - DH candidates (good bat, poor defense)
    - Switch hitters (platoon-proof)
    """
    platoon_frame = ttk.Frame(notebook)
    notebook.add(platoon_frame, text="Platoon Finder")
    
    # Data storage
    all_batters = []
    
    # Main container with notebook for sections
    main_container = tk.Frame(platoon_frame, bg="#1e1e1e")
    main_container.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Create inner notebook for sections
    sections_notebook = ttk.Notebook(main_container)
    sections_notebook.pack(fill="both", expand=True)
    
    # ========== Section 1: Platoon Opportunities ==========
    platoon_section = tk.Frame(sections_notebook, bg="#1e1e1e")
    sections_notebook.add(platoon_section, text="⚾ Platoon Pairs")
    
    # Platoon header and filters
    platoon_header = tk.Frame(platoon_section, bg="#1e1e1e")
    platoon_header.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        platoon_header,
        text="⚾ Platoon Opportunities",
        font=(font[0], font[1] + 2, "bold"),
        bg="#1e1e1e",
        fg="#00ff7f"
    ).pack(side="left")
    
    tk.Label(
        platoon_header,
        text="Match L-bat and R-bat players at the same position",
        font=(font[0], font[1] - 1),
        bg="#1e1e1e",
        fg="#888888"
    ).pack(side="left", padx=(10, 0))
    
    # Platoon filters
    platoon_filter_frame = tk.Frame(platoon_section, bg="#1e1e1e")
    platoon_filter_frame.pack(fill="x", padx=5, pady=2)
    
    tk.Label(platoon_filter_frame, text="Position:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left")
    platoon_pos_var = tk.StringVar(value="All")
    platoon_pos_combo = ttk.Combobox(
        platoon_filter_frame,
        textvariable=platoon_pos_var,
        values=["All", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"],
        state="readonly",
        width=8
    )
    platoon_pos_combo.pack(side="left", padx=5)
    
    tk.Label(platoon_filter_frame, text="Team:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left", padx=(10, 0))
    platoon_team_var = tk.StringVar(value="All")
    platoon_team_combo = ttk.Combobox(
        platoon_filter_frame,
        textvariable=platoon_team_var,
        values=["All"],  # Will be populated with team names
        state="readonly",
        width=10
    )
    platoon_team_combo.pack(side="left", padx=5)
    
    tk.Label(platoon_filter_frame, text="Min OVR:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left", padx=(10, 0))
    platoon_min_ovr_var = tk.StringVar(value="30")
    platoon_min_ovr_entry = tk.Entry(platoon_filter_frame, textvariable=platoon_min_ovr_var, width=5, bg="#000000", fg="#d4d4d4", font=font)
    platoon_min_ovr_entry.pack(side="left", padx=5)
    
    tk.Label(platoon_filter_frame, text="Max OVR:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left", padx=(10, 0))
    platoon_max_ovr_var = tk.StringVar(value="60")
    platoon_max_ovr_entry = tk.Entry(platoon_filter_frame, textvariable=platoon_max_ovr_var, width=5, bg="#000000", fg="#d4d4d4", font=font)
    platoon_max_ovr_entry.pack(side="left", padx=5)
    
    platoon_update_btn = ttk.Button(platoon_filter_frame, text="Find Platoons", command=lambda: update_platoon_table())
    platoon_update_btn.pack(side="left", padx=10)
    
    # Platoon table
    platoon_table_frame = tk.Frame(platoon_section, bg="#1e1e1e")
    platoon_table_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    platoon_vsb = ttk.Scrollbar(platoon_table_frame, orient="vertical")
    platoon_vsb.pack(side="right", fill="y")
    
    platoon_hsb = ttk.Scrollbar(platoon_table_frame, orient="horizontal")
    platoon_hsb.pack(side="bottom", fill="x")
    
    platoon_cols = ("Position", "L-Bat Player", "L-Team", "L-OVR", "R-Bat Player", "R-Team", "R-OVR", "Combined Value")
    platoon_table = ttk.Treeview(
        platoon_table_frame,
        columns=platoon_cols,
        show="headings",
        yscrollcommand=platoon_vsb.set,
        xscrollcommand=platoon_hsb.set,
        height=12
    )
    platoon_table.pack(side="left", fill="both", expand=True)
    platoon_vsb.config(command=platoon_table.yview)
    platoon_hsb.config(command=platoon_table.xview)
    
    platoon_col_widths = {
        "Position": 70, "L-Bat Player": 130, "L-Team": 55, "L-OVR": 50,
        "R-Bat Player": 130, "R-Team": 55, "R-OVR": 50, "Combined Value": 100
    }
    for col in platoon_cols:
        platoon_table.heading(col, text=col, command=lambda c=col: sort_treeview(platoon_table, c, False))
        platoon_table.column(col, width=platoon_col_widths.get(col, 80), minwidth=30, anchor="center", stretch=True)
    
    platoon_table.tag_configure("hover", background="#333")
    platoon_table.tag_configure("same_team", background="#2d4a2d")  # Green for same team
    platoon_table._prev_hover = None
    platoon_table.bind("<Motion>", on_treeview_motion)
    platoon_table.bind("<Leave>", on_leave)
    
    # ========== Section 2: DH Candidates ==========
    dh_section = tk.Frame(sections_notebook, bg="#1e1e1e")
    sections_notebook.add(dh_section, text="🎯 DH Candidates")
    
    # DH header
    dh_header = tk.Frame(dh_section, bg="#1e1e1e")
    dh_header.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        dh_header,
        text="🎯 DH Candidates",
        font=(font[0], font[1] + 2, "bold"),
        bg="#1e1e1e",
        fg="#00ff7f"
    ).pack(side="left")
    
    tk.Label(
        dh_header,
        text="Good batting, poor defense - ideal for DH role",
        font=(font[0], font[1] - 1),
        bg="#1e1e1e",
        fg="#888888"
    ).pack(side="left", padx=(10, 0))
    
    # DH filters
    dh_filter_frame = tk.Frame(dh_section, bg="#1e1e1e")
    dh_filter_frame.pack(fill="x", padx=5, pady=2)
    
    tk.Label(dh_filter_frame, text="Min Bat Rating:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left")
    dh_min_bat_var = tk.StringVar(value="50")
    dh_min_bat_entry = tk.Entry(dh_filter_frame, textvariable=dh_min_bat_var, width=5, bg="#000000", fg="#d4d4d4", font=font)
    dh_min_bat_entry.pack(side="left", padx=5)
    
    tk.Label(dh_filter_frame, text="Max Def Rating:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left", padx=(10, 0))
    dh_max_def_var = tk.StringVar(value="40")
    dh_max_def_entry = tk.Entry(dh_filter_frame, textvariable=dh_max_def_var, width=5, bg="#000000", fg="#d4d4d4", font=font)
    dh_max_def_entry.pack(side="left", padx=5)
    
    dh_update_btn = ttk.Button(dh_filter_frame, text="Find DH Candidates", command=lambda: update_dh_table())
    dh_update_btn.pack(side="left", padx=10)
    
    # DH table
    dh_table_frame = tk.Frame(dh_section, bg="#1e1e1e")
    dh_table_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    dh_vsb = ttk.Scrollbar(dh_table_frame, orient="vertical")
    dh_vsb.pack(side="right", fill="y")
    
    dh_hsb = ttk.Scrollbar(dh_table_frame, orient="horizontal")
    dh_hsb.pack(side="bottom", fill="x")
    
    dh_cols = ("Name", "Age", "Team", "POS", "CON", "POW", "EYE", "Avg Bat", "Avg Def", "Why DH?")
    dh_table = ttk.Treeview(
        dh_table_frame,
        columns=dh_cols,
        show="headings",
        yscrollcommand=dh_vsb.set,
        xscrollcommand=dh_hsb.set,
        height=12
    )
    dh_table.pack(side="left", fill="both", expand=True)
    dh_vsb.config(command=dh_table.yview)
    dh_hsb.config(command=dh_table.xview)
    
    dh_col_widths = {
        "Name": 130, "Age": 40, "Team": 55, "POS": 45,
        "CON": 45, "POW": 45, "EYE": 45, "Avg Bat": 60, "Avg Def": 60, "Why DH?": 180
    }
    for col in dh_cols:
        dh_table.heading(col, text=col, command=lambda c=col: sort_treeview(dh_table, c, False))
        dh_table.column(col, width=dh_col_widths.get(col, 80), minwidth=30, anchor="center", stretch=True)
    
    dh_table.tag_configure("hover", background="#333")
    dh_table.tag_configure("strong_bat", background="#2d4a2d")  # Green for strong bat
    dh_table._prev_hover = None
    dh_table.bind("<Motion>", on_treeview_motion)
    dh_table.bind("<Leave>", on_leave)
    
    dh_id_map = {}
    dh_player_data_map = {}  # Maps iid -> player dict for right-click
    
    # Bind right-click for player card popup (DH table - all batters)
    bind_player_card_right_click(dh_table, dh_player_data_map, lambda p: (p, "batter"))
    
    # ========== Section 3: Switch Hitters ==========
    switch_section = tk.Frame(sections_notebook, bg="#1e1e1e")
    sections_notebook.add(switch_section, text="🔄 Switch Hitters")
    
    # Switch header
    switch_header = tk.Frame(switch_section, bg="#1e1e1e")
    switch_header.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        switch_header,
        text="🔄 Switch Hitters (Platoon-Proof)",
        font=(font[0], font[1] + 2, "bold"),
        bg="#1e1e1e",
        fg="#00ff7f"
    ).pack(side="left")
    
    tk.Label(
        switch_header,
        text="Switch hitters have extra value - no platoon disadvantage",
        font=(font[0], font[1] - 1),
        bg="#1e1e1e",
        fg="#888888"
    ).pack(side="left", padx=(10, 0))
    
    # Switch filters
    switch_filter_frame = tk.Frame(switch_section, bg="#1e1e1e")
    switch_filter_frame.pack(fill="x", padx=5, pady=2)
    
    tk.Label(switch_filter_frame, text="Position:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left")
    switch_pos_var = tk.StringVar(value="All")
    switch_pos_combo = ttk.Combobox(
        switch_filter_frame,
        textvariable=switch_pos_var,
        values=["All", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"],
        state="readonly",
        width=8
    )
    switch_pos_combo.pack(side="left", padx=5)
    
    switch_update_btn = ttk.Button(switch_filter_frame, text="Update", command=lambda: update_switch_table())
    switch_update_btn.pack(side="left", padx=10)
    
    # Switch table
    switch_table_frame = tk.Frame(switch_section, bg="#1e1e1e")
    switch_table_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    switch_vsb = ttk.Scrollbar(switch_table_frame, orient="vertical")
    switch_vsb.pack(side="right", fill="y")
    
    switch_hsb = ttk.Scrollbar(switch_table_frame, orient="horizontal")
    switch_hsb.pack(side="bottom", fill="x")
    
    switch_cols = ("Name", "POS", "Age", "Team", "OVR", "POT", "CON", "POW", "EYE", "Score", "Value")
    switch_table = ttk.Treeview(
        switch_table_frame,
        columns=switch_cols,
        show="headings",
        yscrollcommand=switch_vsb.set,
        xscrollcommand=switch_hsb.set,
        height=12
    )
    switch_table.pack(side="left", fill="both", expand=True)
    switch_vsb.config(command=switch_table.yview)
    switch_hsb.config(command=switch_table.xview)
    
    switch_col_widths = {
        "Name": 130, "POS": 45, "Age": 40, "Team": 55,
        "OVR": 50, "POT": 50, "CON": 45, "POW": 45, "EYE": 45, "Score": 60, "Value": 100
    }
    for col in switch_cols:
        switch_table.heading(col, text=col, command=lambda c=col: sort_treeview(switch_table, c, False))
        switch_table.column(col, width=switch_col_widths.get(col, 80), minwidth=30, anchor="center", stretch=True)
    
    switch_table.tag_configure("hover", background="#333")
    switch_table.tag_configure("high_ovr", background="#2d4a2d")  # Green for high OVR
    switch_table._prev_hover = None
    switch_table.bind("<Motion>", on_treeview_motion)
    switch_table.bind("<Leave>", on_leave)
    
    switch_id_map = {}
    switch_player_data_map = {}  # Maps iid -> player dict for right-click
    
    # Bind right-click for player card popup (switch hitters - all batters)
    bind_player_card_right_click(switch_table, switch_player_data_map, lambda p: (p, "batter"))
    
    def get_teams():
        """Get unique team names from batters"""
        teams = set()
        for b in all_batters:
            team = b.get("ORG", "")
            if team:
                teams.add(team)
        return sorted(teams)
    
    def find_platoon_pairs():
        """Find pairs of L-bat and R-bat players at same position"""
        try:
            min_ovr = float(platoon_min_ovr_var.get())
            max_ovr = float(platoon_max_ovr_var.get())
        except ValueError:
            min_ovr = 30
            max_ovr = 60
        
        pos_filter = platoon_pos_var.get()
        team_filter = platoon_team_var.get()
        
        # Group players by position and handedness
        left_batters = {}  # {pos: [players]}
        right_batters = {}  # {pos: [players]}
        
        for b in all_batters:
            bats = b.get("B", "").upper()
            pos = b.get("POS", "")
            team = b.get("ORG", "")
            
            if bats == "S":  # Skip switch hitters
                continue
            
            if pos_filter != "All" and pos != pos_filter:
                continue
            
            ovr = parse_star_rating(b.get("OVR", "0"))
            if ovr < min_ovr or ovr > max_ovr:
                continue
            
            player_data = {
                "player": b,
                "name": b.get("Name", ""),
                "pos": pos,
                "team": team,
                "ovr": ovr,
                "score": b.get("Scores", {}).get("total", 0)
            }
            
            if bats == "L":
                left_batters.setdefault(pos, []).append(player_data)
            elif bats == "R":
                right_batters.setdefault(pos, []).append(player_data)
        
        # Find matching pairs
        pairs = []
        for pos in left_batters:
            if pos not in right_batters:
                continue
            
            for l_player in left_batters[pos]:
                for r_player in right_batters[pos]:
                    # Apply team filter if set
                    if team_filter != "All":
                        if l_player["team"] != team_filter and r_player["team"] != team_filter:
                            continue
                    
                    combined_value = (l_player["score"] + r_player["score"]) / 2
                    same_team = l_player["team"] == r_player["team"]
                    
                    pairs.append({
                        "pos": pos,
                        "l_player": l_player,
                        "r_player": r_player,
                        "combined_value": combined_value,
                        "same_team": same_team
                    })
        
        # Sort by combined value
        pairs.sort(key=lambda x: x["combined_value"], reverse=True)
        return pairs
    
    def find_dh_candidates():
        """Find players with good bat but poor defense"""
        try:
            min_bat = float(dh_min_bat_var.get())
            max_def = float(dh_max_def_var.get())
        except ValueError:
            min_bat = 50
            max_def = 40
        
        candidates = []
        
        for b in all_batters:
            con = parse_number(b.get("CON", 0))
            gap = parse_number(b.get("GAP", 0))
            pow_ = parse_number(b.get("POW", 0))
            eye = parse_number(b.get("EYE", 0))
            
            avg_bat = (con + gap + pow_ + eye) / 4
            
            if avg_bat < min_bat:
                continue
            
            # Get defensive ratings based on position
            pos = b.get("POS", "")
            def_ratings = []
            
            if pos == "C":
                def_ratings = [
                    parse_number(b.get("C ABI", 0)),
                    parse_number(b.get("C ARM", 0)),
                    parse_number(b.get("C FRM", 0))
                ]
            elif pos in ["1B", "2B", "3B", "SS"]:
                def_ratings = [
                    parse_number(b.get("IF RNG", 0)),
                    parse_number(b.get("IF ERR", 0)),
                    parse_number(b.get("IF ARM", 0))
                ]
            elif pos in ["LF", "CF", "RF"]:
                def_ratings = [
                    parse_number(b.get("OF RNG", 0)),
                    parse_number(b.get("OF ERR", 0)),
                    parse_number(b.get("OF ARM", 0))
                ]
            else:
                continue
            
            avg_def = sum(def_ratings) / len(def_ratings) if def_ratings else 0
            
            if avg_def > max_def:
                continue
            
            # Determine why they're a DH candidate
            reasons = []
            if avg_bat >= 60:
                reasons.append("Strong bat")
            elif avg_bat >= 50:
                reasons.append("Solid bat")
            if avg_def < 30:
                reasons.append("Poor defense")
            elif avg_def < 40:
                reasons.append("Below avg defense")
            
            candidates.append({
                "player": b,
                "name": b.get("Name", ""),
                "age": b.get("Age", ""),
                "team": b.get("ORG", ""),
                "pos": pos,
                "con": con,
                "pow": pow_,
                "eye": eye,
                "avg_bat": avg_bat,
                "avg_def": avg_def,
                "why": ", ".join(reasons)
            })
        
        # Sort by batting average descending
        candidates.sort(key=lambda x: x["avg_bat"], reverse=True)
        return candidates
    
    def find_switch_hitters():
        """Find all switch hitters"""
        pos_filter = switch_pos_var.get()
        
        switch_hitters = []
        
        for b in all_batters:
            bats = b.get("B", "").upper()
            if bats != "S":
                continue
            
            pos = b.get("POS", "")
            if pos_filter != "All" and pos != pos_filter:
                continue
            
            ovr = parse_star_rating(b.get("OVR", "0"))
            pot = parse_star_rating(b.get("POT", "0"))
            score = b.get("Scores", {}).get("total", 0)
            
            # Calculate value assessment
            if ovr >= 50 or pot >= 60:
                value = "High Value"
            elif ovr >= 40 or pot >= 50:
                value = "Solid Value"
            else:
                value = "Depth Piece"
            
            switch_hitters.append({
                "player": b,
                "name": b.get("Name", ""),
                "pos": pos,
                "age": b.get("Age", ""),
                "team": b.get("ORG", ""),
                "ovr": ovr,
                "pot": pot,
                "con": parse_number(b.get("CON", 0)),
                "pow": parse_number(b.get("POW", 0)),
                "eye": parse_number(b.get("EYE", 0)),
                "score": score,
                "value": value
            })
        
        # Sort by score descending
        switch_hitters.sort(key=lambda x: x["score"], reverse=True)
        return switch_hitters
    
    def update_platoon_table():
        """Update the platoon pairs table"""
        platoon_table.delete(*platoon_table.get_children())
        
        pairs = find_platoon_pairs()
        
        for pair in pairs:
            tags = []
            if pair["same_team"]:
                tags.append("same_team")
            
            values = (
                pair["pos"],
                pair["l_player"]["name"],
                pair["l_player"]["team"],
                round(pair["l_player"]["ovr"], 1),
                pair["r_player"]["name"],
                pair["r_player"]["team"],
                round(pair["r_player"]["ovr"], 1),
                round(pair["combined_value"], 1)
            )
            
            platoon_table.insert("", "end", values=values, tags=tags)
    
    def update_dh_table():
        """Update the DH candidates table"""
        dh_table.delete(*dh_table.get_children())
        dh_id_map.clear()
        dh_player_data_map.clear()
        
        candidates = find_dh_candidates()
        
        for c in candidates:
            tags = []
            if c["avg_bat"] >= 55:
                tags.append("strong_bat")
            
            values = (
                c["name"],
                c["age"],
                c["team"],
                c["pos"],
                round(c["con"], 0),
                round(c["pow"], 0),
                round(c["eye"], 0),
                round(c["avg_bat"], 1),
                round(c["avg_def"], 1),
                c["why"]
            )
            
            iid = dh_table.insert("", "end", values=values, tags=tags)
            player_id = c["player"].get("ID", "")
            if player_id:
                dh_id_map[iid] = player_id
            dh_player_data_map[iid] = c["player"]
        
        make_treeview_open_link_handler(dh_table, dh_id_map, lambda pid: player_url_template.format(pid=pid))
    
    def update_switch_table():
        """Update the switch hitters table"""
        switch_table.delete(*switch_table.get_children())
        switch_id_map.clear()
        switch_player_data_map.clear()
        
        switch_hitters = find_switch_hitters()
        
        for s in switch_hitters:
            tags = []
            if s["ovr"] >= 45:
                tags.append("high_ovr")
            
            values = (
                s["name"],
                s["pos"],
                s["age"],
                s["team"],
                round(s["ovr"], 1),
                round(s["pot"], 1),
                round(s["con"], 0),
                round(s["pow"], 0),
                round(s["eye"], 0),
                round(s["score"], 1),
                s["value"]
            )
            
            iid = switch_table.insert("", "end", values=values, tags=tags)
            player_id = s["player"].get("ID", "")
            if player_id:
                switch_id_map[iid] = player_id
            switch_player_data_map[iid] = s["player"]
        
        make_treeview_open_link_handler(switch_table, switch_id_map, lambda pid: player_url_template.format(pid=pid))
    
    def update_all_tables():
        """Update all tables"""
        # Update team filter options
        teams = get_teams()
        platoon_team_combo["values"] = ["All"] + teams
        
        update_platoon_table()
        update_dh_table()
        update_switch_table()
    
    # Bind filter changes
    platoon_pos_combo.bind("<<ComboboxSelected>>", lambda e: update_platoon_table())
    platoon_team_combo.bind("<<ComboboxSelected>>", lambda e: update_platoon_table())
    switch_pos_combo.bind("<<ComboboxSelected>>", lambda e: update_switch_table())
    
    class PlatoonFinderTab:
        def refresh(self, pitchers, batters):
            all_batters.clear()
            all_batters.extend(batters)
            update_all_tables()
    
    return PlatoonFinderTab()
