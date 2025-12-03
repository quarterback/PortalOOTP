import tkinter as tk
from tkinter import ttk
from .style import on_treeview_motion, on_leave, sort_treeview
from .widgets import (
    make_treeview_open_link_handler,
    load_player_url_template,
)
from .tooltips import add_button_tooltip
from trade_value import parse_number, parse_years_left, get_contract_status, parse_salary
from team_parser import calculate_surplus_value, get_surplus_tier

player_url_template = load_player_url_template()

# Age definitions for trade matching
# These thresholds align with typical MLB trade deadline evaluations:
# - Prospects (≤25): Young players still developing, valued for future potential
# - Tweeners (26): Players in transition, evaluate case-by-case
# - Veterans (≥27): Established players, valued primarily for current production
PROSPECT_MAX_AGE = 25
VETERAN_MIN_AGE = 27

# Minimum potential gap to identify high-upside prospects
# A gap of 15+ (e.g., 3.5 OVR vs 5.0 POT) indicates significant upside
POTENTIAL_GAP_THRESHOLD = 15

# Display thresholds for highlighting high-value entries
HIGH_VALUE_WAR_THRESHOLD = 2.0  # WAR threshold for highlighting veterans
HIGH_POTENTIAL_GAP_THRESHOLD = 2.0  # Star gap threshold for highlighting prospects
HIGH_SURPLUS_THRESHOLD = 5.0  # Surplus value threshold for highlighting


def add_trade_finder_tab(notebook, font):
    trade_finder_frame = ttk.Frame(notebook)
    notebook.add(trade_finder_frame, text="Trade Finder")
    
    # Data storage
    all_pitchers = []
    all_batters = []
    
    # Create a notebook within the tab for different trade finder sections
    inner_notebook = ttk.Notebook(trade_finder_frame)
    inner_notebook.pack(fill="both", expand=True, padx=5, pady=5)
    
    # ========================================================================
    # Tab 1: Original Trade Finder (Veterans + Prospects)
    # ========================================================================
    original_frame = ttk.Frame(inner_notebook)
    inner_notebook.add(original_frame, text="📤 Veterans & Prospects")
    
    # Main container with two panels
    main_container = tk.Frame(original_frame, bg="#1e1e1e")
    main_container.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Left panel - Expiring Veterans (Sell High)
    left_frame = tk.Frame(main_container, bg="#1e1e1e", relief="ridge", bd=2)
    left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
    
    left_header = tk.Frame(left_frame, bg="#1e1e1e")
    left_header.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        left_header,
        text="📤 Expiring Veterans (Sell High)",
        font=(font[0], font[1] + 2, "bold"),
        bg="#1e1e1e",
        fg="#00ff7f"
    ).pack(side="left")
    
    tk.Label(
        left_header,
        text="Age 27+, YL ≤ 1, Producing Well",
        font=(font[0], font[1] - 1),
        bg="#1e1e1e",
        fg="#888888"
    ).pack(side="left", padx=(10, 0))
    
    # Veterans filter controls
    vet_filter_frame = tk.Frame(left_frame, bg="#1e1e1e")
    vet_filter_frame.pack(fill="x", padx=5, pady=2)
    
    tk.Label(vet_filter_frame, text="Position:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left")
    vet_pos_var = tk.StringVar(value="All")
    vet_pos_combo = ttk.Combobox(
        vet_filter_frame,
        textvariable=vet_pos_var,
        values=["All", "SP", "RP", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"],
        state="readonly",
        width=8
    )
    vet_pos_combo.pack(side="left", padx=5)
    
    tk.Label(vet_filter_frame, text="Min WAR:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left", padx=(10, 0))
    vet_war_var = tk.StringVar(value="0.5")
    vet_war_entry = tk.Entry(vet_filter_frame, textvariable=vet_war_var, width=5, bg="#000000", fg="#d4d4d4", font=font)
    vet_war_entry.pack(side="left", padx=5)
    
    # Veterans table
    vet_table_frame = tk.Frame(left_frame, bg="#1e1e1e")
    vet_table_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    vet_vsb = ttk.Scrollbar(vet_table_frame, orient="vertical")
    vet_vsb.pack(side="right", fill="y")
    
    vet_hsb = ttk.Scrollbar(vet_table_frame, orient="horizontal")
    vet_hsb.pack(side="bottom", fill="x")
    
    vet_cols = ("Name", "POS", "Age", "Team", "YL", "WAR", "wRC+/ERA+", "Score")
    vet_table = ttk.Treeview(
        vet_table_frame,
        columns=vet_cols,
        show="headings",
        yscrollcommand=vet_vsb.set,
        xscrollcommand=vet_hsb.set,
        height=15
    )
    vet_table.pack(side="left", fill="both", expand=True)
    vet_vsb.config(command=vet_table.yview)
    vet_hsb.config(command=vet_table.xview)
    
    vet_col_widths = {
        "Name": 140, "POS": 45, "Age": 40, "Team": 55,
        "YL": 35, "WAR": 50, "wRC+/ERA+": 80, "Score": 60
    }
    for col in vet_cols:
        vet_table.heading(col, text=col, command=lambda c=col: sort_treeview(vet_table, c, False))
        vet_table.column(col, width=vet_col_widths.get(col, 80), minwidth=30, anchor="center", stretch=True)
    
    vet_table.tag_configure("hover", background="#333")
    vet_table.tag_configure("high_value", background="#2d4a2d")  # Green tint for high value
    vet_table._prev_hover = None
    vet_table.bind("<Motion>", on_treeview_motion)
    vet_table.bind("<Leave>", on_leave)
    
    vet_id_map = {}
    
    # Right panel - High-Upside Prospects (Buy Low)
    right_frame = tk.Frame(main_container, bg="#1e1e1e", relief="ridge", bd=2)
    right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
    
    right_header = tk.Frame(right_frame, bg="#1e1e1e")
    right_header.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        right_header,
        text="📥 High-Upside Prospects (Buy Low)",
        font=(font[0], font[1] + 2, "bold"),
        bg="#1e1e1e",
        fg="#00ff7f"
    ).pack(side="left")
    
    tk.Label(
        right_header,
        text="Age ≤ 25, POT - OVR ≥ 15",
        font=(font[0], font[1] - 1),
        bg="#1e1e1e",
        fg="#888888"
    ).pack(side="left", padx=(10, 0))
    
    # Prospects filter controls
    pros_filter_frame = tk.Frame(right_frame, bg="#1e1e1e")
    pros_filter_frame.pack(fill="x", padx=5, pady=2)
    
    tk.Label(pros_filter_frame, text="Position:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left")
    pros_pos_var = tk.StringVar(value="All")
    pros_pos_combo = ttk.Combobox(
        pros_filter_frame,
        textvariable=pros_pos_var,
        values=["All", "SP", "RP", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"],
        state="readonly",
        width=8
    )
    pros_pos_combo.pack(side="left", padx=5)
    
    tk.Label(pros_filter_frame, text="Min Gap:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left", padx=(10, 0))
    pros_gap_var = tk.StringVar(value="15")
    pros_gap_entry = tk.Entry(pros_filter_frame, textvariable=pros_gap_var, width=5, bg="#000000", fg="#d4d4d4", font=font)
    pros_gap_entry.pack(side="left", padx=5)
    
    # Prospects table
    pros_table_frame = tk.Frame(right_frame, bg="#1e1e1e")
    pros_table_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    pros_vsb = ttk.Scrollbar(pros_table_frame, orient="vertical")
    pros_vsb.pack(side="right", fill="y")
    
    pros_hsb = ttk.Scrollbar(pros_table_frame, orient="horizontal")
    pros_hsb.pack(side="bottom", fill="x")
    
    pros_cols = ("Name", "POS", "Age", "Team", "OVR", "POT", "Gap", "Score")
    pros_table = ttk.Treeview(
        pros_table_frame,
        columns=pros_cols,
        show="headings",
        yscrollcommand=pros_vsb.set,
        xscrollcommand=pros_hsb.set,
        height=15
    )
    pros_table.pack(side="left", fill="both", expand=True)
    pros_vsb.config(command=pros_table.yview)
    pros_hsb.config(command=pros_table.xview)
    
    pros_col_widths = {
        "Name": 140, "POS": 45, "Age": 40, "Team": 55,
        "OVR": 45, "POT": 45, "Gap": 40, "Score": 60
    }
    for col in pros_cols:
        pros_table.heading(col, text=col, command=lambda c=col: sort_treeview(pros_table, c, False))
        pros_table.column(col, width=pros_col_widths.get(col, 80), minwidth=30, anchor="center", stretch=True)
    
    pros_table.tag_configure("hover", background="#333")
    pros_table.tag_configure("high_potential", background="#4a2d4a")  # Purple tint for high potential
    pros_table._prev_hover = None
    pros_table.bind("<Motion>", on_treeview_motion)
    pros_table.bind("<Leave>", on_leave)
    
    pros_id_map = {}
    
    def parse_star_rating(val):
        """Convert star rating string to numeric value"""
        if not val:
            return 0.0
        val = str(val).strip()
        if "Stars" in val:
            try:
                return float(val.split()[0])
            except:
                return 0.0
        try:
            return float(val)
        except:
            return 0.0
    
    def get_expiring_veterans():
        """Find veterans with expiring contracts who are producing well"""
        try:
            min_war = float(vet_war_var.get())
        except ValueError:
            min_war = 0.5
        
        pos_filter = vet_pos_var.get()
        veterans = []
        
        # Process pitchers
        for p in all_pitchers:
            try:
                age = int(p.get("Age", 0))
            except (ValueError, TypeError):
                continue
            
            if age < VETERAN_MIN_AGE:
                continue
            
            # Check years left using enhanced parsing
            yl_data = parse_years_left(p.get("YL", ""))
            yl = yl_data.get("years", 99)
            status = yl_data.get("status", "unknown")
            
            # Expiring = YL <= 1 AND not pre-arb (auto renewal)
            if yl > 1 or status == "pre_arb":
                continue
            
            # Check position filter
            pos = p.get("POS", "")
            if pos_filter != "All" and pos != pos_filter:
                continue
            
            # Get WAR and ERA+
            war = parse_number(p.get("WAR (Pitcher)", p.get("WAR", 0)))
            era_plus = parse_number(p.get("ERA+", 0))
            
            if war < min_war:
                continue
            
            # Get contract status for display
            contract_status, _, _ = get_contract_status(p)
            
            score = p.get("Scores", {}).get("total", 0)
            
            veterans.append({
                "player": p,
                "type": "pitcher",
                "name": p.get("Name", ""),
                "pos": pos,
                "age": age,
                "team": p.get("ORG", ""),
                "yl": yl,
                "status": contract_status,
                "war": war,
                "metric": era_plus,  # ERA+ for pitchers
                "metric_label": "ERA+",
                "score": score
            })
        
        # Process batters
        for b in all_batters:
            try:
                age = int(b.get("Age", 0))
            except (ValueError, TypeError):
                continue
            
            if age < VETERAN_MIN_AGE:
                continue
            
            # Check years left using enhanced parsing
            yl_data = parse_years_left(b.get("YL", ""))
            yl = yl_data.get("years", 99)
            status = yl_data.get("status", "unknown")
            
            # Expiring = YL <= 1 AND not pre-arb (auto renewal)
            if yl > 1 or status == "pre_arb":
                continue
            
            # Check position filter
            pos = b.get("POS", "")
            if pos_filter != "All" and pos != pos_filter:
                continue
            
            # Get WAR and wRC+
            war = parse_number(b.get("WAR (Batter)", b.get("WAR", 0)))
            wrc_plus = parse_number(b.get("wRC+", 0))
            
            if war < min_war:
                continue
            
            # Get contract status for display
            contract_status, _, _ = get_contract_status(b)
            
            score = b.get("Scores", {}).get("total", 0)
            
            veterans.append({
                "player": b,
                "type": "batter",
                "name": b.get("Name", ""),
                "pos": pos,
                "age": age,
                "team": b.get("ORG", ""),
                "yl": yl,
                "status": contract_status,
                "war": war,
                "metric": wrc_plus,  # wRC+ for batters
                "metric_label": "wRC+",
                "score": score
            })
        
        # Sort by WAR descending
        veterans.sort(key=lambda x: x["war"], reverse=True)
        return veterans
    
    def get_high_upside_prospects():
        """Find young players with high potential gap"""
        try:
            min_gap = float(pros_gap_var.get())
        except ValueError:
            min_gap = POTENTIAL_GAP_THRESHOLD
        
        pos_filter = pros_pos_var.get()
        prospects = []
        
        # Process pitchers
        for p in all_pitchers:
            try:
                age = int(p.get("Age", 0))
            except (ValueError, TypeError):
                continue
            
            if age > PROSPECT_MAX_AGE:
                continue
            
            # Check position filter
            pos = p.get("POS", "")
            if pos_filter != "All" and pos != pos_filter:
                continue
            
            # Get OVR and POT ratings
            ovr = parse_star_rating(p.get("OVR", "0"))
            pot = parse_star_rating(p.get("POT", "0"))
            gap = pot - ovr
            
            if gap < min_gap:
                continue
            
            score = p.get("Scores", {}).get("total", 0)
            
            prospects.append({
                "player": p,
                "type": "pitcher",
                "name": p.get("Name", ""),
                "pos": pos,
                "age": age,
                "team": p.get("ORG", ""),
                "ovr": ovr,
                "pot": pot,
                "gap": gap,
                "score": score
            })
        
        # Process batters
        for b in all_batters:
            try:
                age = int(b.get("Age", 0))
            except (ValueError, TypeError):
                continue
            
            if age > PROSPECT_MAX_AGE:
                continue
            
            # Check position filter
            pos = b.get("POS", "")
            if pos_filter != "All" and pos != pos_filter:
                continue
            
            # Get OVR and POT ratings
            ovr = parse_star_rating(b.get("OVR", "0"))
            pot = parse_star_rating(b.get("POT", "0"))
            gap = pot - ovr
            
            if gap < min_gap:
                continue
            
            score = b.get("Scores", {}).get("total", 0)
            
            prospects.append({
                "player": b,
                "type": "batter",
                "name": b.get("Name", ""),
                "pos": pos,
                "age": age,
                "team": b.get("ORG", ""),
                "ovr": ovr,
                "pot": pot,
                "gap": gap,
                "score": score
            })
        
        # Sort by gap descending, then by potential
        prospects.sort(key=lambda x: (x["gap"], x["pot"]), reverse=True)
        return prospects
    
    def update_veterans_table():
        """Update the veterans table with current filter settings"""
        vet_table.delete(*vet_table.get_children())
        vet_id_map.clear()
        
        veterans = get_expiring_veterans()
        
        for vet in veterans:
            tags = []
            if vet["war"] >= HIGH_VALUE_WAR_THRESHOLD:
                tags.append("high_value")
            
            values = (
                vet["name"],
                vet["pos"],
                vet["age"],
                vet["team"],
                vet["yl"],
                round(vet["war"], 1),
                round(vet["metric"], 0) if vet["metric"] else "-",
                round(vet["score"], 1)
            )
            
            iid = vet_table.insert("", "end", values=values, tags=tags)
            player_id = vet["player"].get("ID", "")
            if player_id:
                vet_id_map[iid] = player_id
        
        make_treeview_open_link_handler(vet_table, vet_id_map, lambda pid: player_url_template.format(pid=pid))
    
    def update_prospects_table():
        """Update the prospects table with current filter settings"""
        pros_table.delete(*pros_table.get_children())
        pros_id_map.clear()
        
        prospects = get_high_upside_prospects()
        
        for pros in prospects:
            tags = []
            if pros["gap"] >= HIGH_POTENTIAL_GAP_THRESHOLD:
                tags.append("high_potential")
            
            values = (
                pros["name"],
                pros["pos"],
                pros["age"],
                pros["team"],
                f"{pros['ovr']:.1f}",
                f"{pros['pot']:.1f}",
                f"{pros['gap']:.1f}",
                round(pros["score"], 1)
            )
            
            iid = pros_table.insert("", "end", values=values, tags=tags)
            player_id = pros["player"].get("ID", "")
            if player_id:
                pros_id_map[iid] = player_id
        
        make_treeview_open_link_handler(pros_table, pros_id_map, lambda pid: player_url_template.format(pid=pid))
    
    def update_all_tables():
        """Update both tables"""
        update_veterans_table()
        update_prospects_table()
    
    # Bind filter changes
    vet_pos_combo.bind("<<ComboboxSelected>>", lambda e: update_veterans_table())
    pros_pos_combo.bind("<<ComboboxSelected>>", lambda e: update_prospects_table())
    
    # Add update buttons
    vet_update_btn = ttk.Button(vet_filter_frame, text="Update", command=update_veterans_table)
    vet_update_btn.pack(side="left", padx=10)
    
    pros_update_btn = ttk.Button(pros_filter_frame, text="Update", command=update_prospects_table)
    pros_update_btn.pack(side="left", padx=10)
    
    # ========================================================================
    # Tab 2: Surplus Value Trade Finder
    # ========================================================================
    surplus_frame = ttk.Frame(inner_notebook)
    inner_notebook.add(surplus_frame, text="💰 Surplus Value")
    
    # Surplus value container
    surplus_container = tk.Frame(surplus_frame, bg="#1e1e1e")
    surplus_container.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Header with explanation
    surplus_header = tk.Frame(surplus_container, bg="#1e1e1e")
    surplus_header.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        surplus_header,
        text="💰 Surplus Value Trade Finder",
        font=(font[0], font[1] + 2, "bold"),
        bg="#1e1e1e",
        fg="#00ff7f"
    ).pack(side="left")
    
    tk.Label(
        surplus_header,
        text="Players providing more value than their salary (WAR × $8M/WAR - Salary)",
        font=(font[0], font[1] - 1),
        bg="#1e1e1e",
        fg="#888888"
    ).pack(side="left", padx=(10, 0))
    
    # Surplus filter controls
    surplus_filter_frame = tk.Frame(surplus_container, bg="#1e1e1e")
    surplus_filter_frame.pack(fill="x", padx=5, pady=2)
    
    tk.Label(surplus_filter_frame, text="Position:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left")
    surplus_pos_var = tk.StringVar(value="All")
    surplus_pos_combo = ttk.Combobox(
        surplus_filter_frame,
        textvariable=surplus_pos_var,
        values=["All", "SP", "RP", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"],
        state="readonly",
        width=8
    )
    surplus_pos_combo.pack(side="left", padx=5)
    
    tk.Label(surplus_filter_frame, text="Min Surplus ($M):", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left", padx=(10, 0))
    surplus_min_var = tk.StringVar(value="0")
    surplus_min_entry = tk.Entry(surplus_filter_frame, textvariable=surplus_min_var, width=5, bg="#000000", fg="#d4d4d4", font=font)
    surplus_min_entry.pack(side="left", padx=5)
    
    tk.Label(surplus_filter_frame, text="Max Age:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left", padx=(10, 0))
    surplus_age_var = tk.StringVar(value="35")
    surplus_age_entry = tk.Entry(surplus_filter_frame, textvariable=surplus_age_var, width=4, bg="#000000", fg="#d4d4d4", font=font)
    surplus_age_entry.pack(side="left", padx=5)
    
    # Surplus value table
    surplus_table_frame = tk.Frame(surplus_container, bg="#1e1e1e")
    surplus_table_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    surplus_vsb = ttk.Scrollbar(surplus_table_frame, orient="vertical")
    surplus_vsb.pack(side="right", fill="y")
    
    surplus_hsb = ttk.Scrollbar(surplus_table_frame, orient="horizontal")
    surplus_hsb.pack(side="bottom", fill="x")
    
    surplus_cols = ("Name", "POS", "Age", "Team", "OVR", "WAR", "Salary", "Surplus", "Tier")
    surplus_table = ttk.Treeview(
        surplus_table_frame,
        columns=surplus_cols,
        show="headings",
        yscrollcommand=surplus_vsb.set,
        xscrollcommand=surplus_hsb.set,
        height=20
    )
    surplus_table.pack(side="left", fill="both", expand=True)
    surplus_vsb.config(command=surplus_table.yview)
    surplus_hsb.config(command=surplus_table.xview)
    
    surplus_col_widths = {
        "Name": 150, "POS": 45, "Age": 40, "Team": 55,
        "OVR": 50, "WAR": 50, "Salary": 70, "Surplus": 70, "Tier": 80
    }
    for col in surplus_cols:
        surplus_table.heading(col, text=col, command=lambda c=col: sort_treeview(surplus_table, c, False))
        surplus_table.column(col, width=surplus_col_widths.get(col, 80), minwidth=30, anchor="center", stretch=True)
    
    surplus_table.tag_configure("hover", background="#333")
    surplus_table.tag_configure("high_surplus", background="#2d4a2d")  # Green tint for high surplus
    surplus_table.tag_configure("excellent_surplus", background="#1a5a1a")  # Darker green for excellent
    surplus_table._prev_hover = None
    surplus_table.bind("<Motion>", on_treeview_motion)
    surplus_table.bind("<Leave>", on_leave)
    
    surplus_id_map = {}
    
    def get_surplus_value_players():
        """Find players with positive surplus value"""
        try:
            min_surplus = float(surplus_min_var.get())
        except ValueError:
            min_surplus = 0.0
        
        try:
            max_age = int(surplus_age_var.get())
        except ValueError:
            max_age = 35
        
        pos_filter = surplus_pos_var.get()
        players_with_surplus = []
        
        # Process pitchers
        for p in all_pitchers:
            try:
                age = int(p.get("Age", 0))
            except (ValueError, TypeError):
                continue
            
            if age > max_age:
                continue
            
            pos = p.get("POS", "")
            if pos_filter != "All" and pos != pos_filter:
                continue
            
            # Get WAR and salary
            war = parse_number(p.get("WAR (Pitcher)", p.get("WAR", 0)))
            salary = parse_salary(p.get("SLR", 0))
            
            # Calculate surplus
            surplus = calculate_surplus_value(war, salary)
            
            if surplus < min_surplus:
                continue
            
            surplus_tier = get_surplus_tier(surplus)
            ovr = parse_star_rating_local(p.get("OVR", "0"))
            
            players_with_surplus.append({
                "player": p,
                "type": "pitcher",
                "name": p.get("Name", ""),
                "pos": pos,
                "age": age,
                "team": p.get("ORG", ""),
                "ovr": ovr,
                "war": war,
                "salary": salary,
                "surplus": surplus,
                "surplus_tier": surplus_tier,
            })
        
        # Process batters
        for b in all_batters:
            try:
                age = int(b.get("Age", 0))
            except (ValueError, TypeError):
                continue
            
            if age > max_age:
                continue
            
            pos = b.get("POS", "")
            if pos_filter != "All" and pos != pos_filter:
                continue
            
            # Get WAR and salary
            war = parse_number(b.get("WAR (Batter)", b.get("WAR", 0)))
            salary = parse_salary(b.get("SLR", 0))
            
            # Calculate surplus
            surplus = calculate_surplus_value(war, salary)
            
            if surplus < min_surplus:
                continue
            
            surplus_tier = get_surplus_tier(surplus)
            ovr = parse_star_rating_local(b.get("OVR", "0"))
            
            players_with_surplus.append({
                "player": b,
                "type": "batter",
                "name": b.get("Name", ""),
                "pos": pos,
                "age": age,
                "team": b.get("ORG", ""),
                "ovr": ovr,
                "war": war,
                "salary": salary,
                "surplus": surplus,
                "surplus_tier": surplus_tier,
            })
        
        # Sort by surplus descending
        players_with_surplus.sort(key=lambda x: x["surplus"], reverse=True)
        return players_with_surplus
    
    def parse_star_rating_local(val):
        """Convert star rating string to numeric value"""
        if not val:
            return 0.0
        val = str(val).strip()
        if "Stars" in val:
            try:
                return float(val.split()[0])
            except (ValueError, IndexError):
                return 0.0
        try:
            return float(val)
        except ValueError:
            return 0.0
    
    def update_surplus_table():
        """Update the surplus value table"""
        surplus_table.delete(*surplus_table.get_children())
        surplus_id_map.clear()
        
        players = get_surplus_value_players()
        
        for player_data in players:
            tags = []
            if player_data["surplus"] >= 10:
                tags.append("excellent_surplus")
            elif player_data["surplus"] >= HIGH_SURPLUS_THRESHOLD:
                tags.append("high_surplus")
            
            values = (
                player_data["name"],
                player_data["pos"],
                player_data["age"],
                player_data["team"],
                f"{player_data['ovr']:.1f}",
                f"{player_data['war']:.1f}",
                f"${player_data['salary']:.1f}M",
                f"+${player_data['surplus']:.1f}M" if player_data['surplus'] >= 0 else f"-${abs(player_data['surplus']):.1f}M",
                f"{player_data['surplus_tier']['icon']} {player_data['surplus_tier']['tier']}"
            )
            
            iid = surplus_table.insert("", "end", values=values, tags=tags)
            player_id = player_data["player"].get("ID", "")
            if player_id:
                surplus_id_map[iid] = player_id
        
        make_treeview_open_link_handler(surplus_table, surplus_id_map, lambda pid: player_url_template.format(pid=pid))
    
    # Bind surplus filter changes
    surplus_pos_combo.bind("<<ComboboxSelected>>", lambda e: update_surplus_table())
    
    surplus_update_btn = ttk.Button(surplus_filter_frame, text="Update", command=update_surplus_table)
    surplus_update_btn.pack(side="left", padx=10)
    
    def update_all_with_surplus():
        """Update all tables including surplus"""
        update_all_tables()
        update_surplus_table()
    
    class TradeFinderTab:
        def refresh(self, pitchers, batters):
            all_pitchers.clear()
            all_batters.clear()
            all_pitchers.extend(pitchers)
            all_batters.extend(batters)
            update_all_with_surplus()
    
    return TradeFinderTab()
