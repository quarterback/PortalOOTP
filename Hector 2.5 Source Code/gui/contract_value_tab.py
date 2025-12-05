import tkinter as tk
from tkinter import ttk
from .style import on_treeview_motion, on_leave, sort_treeview
from .widgets import (
    make_treeview_open_link_handler,
    load_player_url_template,
    bind_player_card_right_click,
)
from .tooltips import add_button_tooltip
from trade_value import (
    calculate_dollars_per_war,
    calculate_surplus_value,
    get_contract_category,
    calculate_trade_value,
    parse_number,
    parse_salary,
    parse_years_left,
    calculate_aav,
    calculate_total_commitment,
    get_contract_status,
    get_extension_analysis,
)

player_url_template = load_player_url_template()


def add_contract_value_tab(notebook, font):
    """
    Enhanced Contract Value Tab - Evaluate whether players provide good value relative to salary
    
    Features:
    - Enhanced $/WAR calculation using AAV
    - Surplus Value calculation
    - Contract status (Pre-Arb, Arbitration, FA Soon, Locked Up)
    - Contract category classification (Surplus, Fair Value, Albatross, Arb Target, Extension)
    - Extension Watch section for players with extensions
    - Sortable and filterable table
    """
    contract_frame = ttk.Frame(notebook)
    notebook.add(contract_frame, text="Contract Value")
    
    # Data storage
    all_pitchers = []
    all_batters = []
    
    # Main container with notebook for sub-tabs
    main_container = tk.Frame(contract_frame, bg="#2d2d2d")
    main_container.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Create sub-notebook for Contract Analysis and Extension Watch
    sub_notebook = ttk.Notebook(main_container)
    sub_notebook.pack(fill="both", expand=True)
    
    # ==================== CONTRACT ANALYSIS TAB ====================
    analysis_frame = tk.Frame(sub_notebook, bg="#2d2d2d")
    sub_notebook.add(analysis_frame, text="📊 Contract Analysis")
    
    # Header
    header_frame = tk.Frame(analysis_frame, bg="#2d2d2d")
    header_frame.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        header_frame,
        text="💵 Contract Value Analysis",
        font=(font[0], font[1] + 2, "bold"),
        bg="#2d2d2d",
        fg="#00ff7f"
    ).pack(side="left")
    
    tk.Label(
        header_frame,
        text="Evaluate contract efficiency with AAV and contract status",
        font=(font[0], font[1] - 1),
        bg="#2d2d2d",
        fg="#888888"
    ).pack(side="left", padx=(10, 0))
    
    # Filter controls
    filter_frame = tk.Frame(analysis_frame, bg="#2d2d2d")
    filter_frame.pack(fill="x", padx=5, pady=5)
    
    # Player type filter
    tk.Label(filter_frame, text="Type:", bg="#2d2d2d", fg="#d4d4d4", font=font).pack(side="left")
    type_var = tk.StringVar(value="All")
    type_combo = ttk.Combobox(
        filter_frame,
        textvariable=type_var,
        values=["All", "Batters", "Pitchers"],
        state="readonly",
        width=10
    )
    type_combo.pack(side="left", padx=5)
    
    # Position filter
    tk.Label(filter_frame, text="Position:", bg="#2d2d2d", fg="#d4d4d4", font=font).pack(side="left", padx=(10, 0))
    pos_var = tk.StringVar(value="All")
    pos_combo = ttk.Combobox(
        filter_frame,
        textvariable=pos_var,
        values=["All", "SP", "RP", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"],
        state="readonly",
        width=8
    )
    pos_combo.pack(side="left", padx=5)
    
    # Category filter - updated with new categories
    tk.Label(filter_frame, text="Category:", bg="#2d2d2d", fg="#d4d4d4", font=font).pack(side="left", padx=(10, 0))
    category_var = tk.StringVar(value="All")
    category_combo = ttk.Combobox(
        filter_frame,
        textvariable=category_var,
        values=["All", "💰 Surplus", "✅ Fair Value", "🚨 Albatross", "🎯 Arb Target", "📋 Extension"],
        state="readonly",
        width=14
    )
    category_combo.pack(side="left", padx=5)
    
    # Contract Status filter
    tk.Label(filter_frame, text="Status:", bg="#2d2d2d", fg="#d4d4d4", font=font).pack(side="left", padx=(10, 0))
    status_var = tk.StringVar(value="All")
    status_combo = ttk.Combobox(
        filter_frame,
        textvariable=status_var,
        values=["All", "Pre-Arb", "Arbitration", "FA Soon", "Locked Up", "Signed"],
        state="readonly",
        width=12
    )
    status_combo.pack(side="left", padx=5)
    
    # Min WAR filter
    tk.Label(filter_frame, text="Min WAR:", bg="#2d2d2d", fg="#d4d4d4", font=font).pack(side="left", padx=(10, 0))
    min_war_var = tk.StringVar(value="0")
    min_war_entry = tk.Entry(filter_frame, textvariable=min_war_var, width=5, bg="#000000", fg="#d4d4d4", font=font)
    min_war_entry.pack(side="left", padx=5)
    
    # Update button
    update_btn = ttk.Button(filter_frame, text="Update", command=lambda: update_table())
    update_btn.pack(side="left", padx=10)
    
    # Table frame
    table_frame = tk.Frame(analysis_frame, bg="#2d2d2d")
    table_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    vsb = ttk.Scrollbar(table_frame, orient="vertical")
    vsb.pack(side="right", fill="y")
    
    hsb = ttk.Scrollbar(table_frame, orient="horizontal")
    hsb.pack(side="bottom", fill="x")
    
    # Updated columns with AAV, Status, and Total Commitment
    cols = ("Name", "POS", "Age", "Team", "WAR", "AAV", "Status", "YL", "Total $", "$/WAR", "Surplus", "Category", "Trade Value")
    table = ttk.Treeview(
        table_frame,
        columns=cols,
        show="headings",
        yscrollcommand=vsb.set,
        xscrollcommand=hsb.set,
        height=18
    )
    table.pack(side="left", fill="both", expand=True)
    vsb.config(command=table.yview)
    hsb.config(command=table.xview)
    
    col_widths = {
        "Name": 130, "POS": 40, "Age": 35, "Team": 50,
        "WAR": 45, "AAV": 60, "Status": 75, "YL": 35, "Total $": 70,
        "$/WAR": 60, "Surplus": 70, "Category": 90, "Trade Value": 80
    }
    for col in cols:
        table.heading(col, text=col, command=lambda c=col: sort_treeview(table, c, False))
        table.column(col, width=col_widths.get(col, 80), minwidth=30, anchor="center", stretch=True)
    
    # Configure tags for category and status colors
    table.tag_configure("hover", background="#333")
    table.tag_configure("surplus", background="#2d4a2d")  # Green tint
    table.tag_configure("fair_value", background="#4a4a2d")  # Yellow tint
    table.tag_configure("albatross", background="#4a2d2d")  # Red tint
    table.tag_configure("arb_target", background="#2d3a4a")  # Blue tint
    table.tag_configure("extension", background="#3d2d4a")  # Purple tint
    
    table._prev_hover = None
    table.bind("<Motion>", on_treeview_motion)
    table.bind("<Leave>", on_leave)
    
    id_map = {}
    player_data_map = {}  # Maps iid -> player dict for right-click
    
    # Player type detection for right-click
    PITCHER_POSITIONS = {"SP", "RP", "CL", "P"}
    def get_player_type_from_data(player_data):
        ptype = player_data.get("type", "batter")
        return ptype
    
    # Bind right-click for player card popup
    bind_player_card_right_click(table, player_data_map, lambda p: (p["player"], p["type"]))
    
    def get_tag_for_category(category):
        """Get row tag based on category"""
        if "Surplus" in category:
            return "surplus"
        elif "Albatross" in category:
            return "albatross"
        elif "Arb Target" in category:
            return "arb_target"
        elif "Extension" in category:
            return "extension"
        else:
            return "fair_value"
    
    def get_filtered_players():
        """Get players matching current filters"""
        type_filter = type_var.get()
        pos_filter = pos_var.get()
        category_filter = category_var.get()
        status_filter = status_var.get()
        
        try:
            min_war = float(min_war_var.get())
        except ValueError:
            min_war = 0
        
        players = []
        
        # Process batters
        if type_filter in ["All", "Batters"]:
            for b in all_batters:
                pos = b.get("POS", "")
                if pos_filter != "All" and pos != pos_filter:
                    continue
                
                war = parse_number(b.get("WAR (Batter)", b.get("WAR", 0)))
                if war < min_war:
                    continue
                
                # Parse YL once and reuse
                yl_data = parse_years_left(b.get("YL", ""))
                years_left = yl_data.get("years", 0)
                
                # Get enhanced contract data
                category_name, category_icon, category_color = get_contract_category(b, "batter")
                full_category = f"{category_icon} {category_name}"
                
                if category_filter != "All" and category_icon not in category_filter:
                    continue
                
                # Get contract status
                contract_status, status_key, status_color = get_contract_status(b)
                
                if status_filter != "All" and status_filter != contract_status:
                    continue
                
                dollars_per_war, dpw_display = calculate_dollars_per_war(b, "batter")
                surplus, surplus_display = calculate_surplus_value(b, "batter")
                trade_value_data = calculate_trade_value(b, "batter")
                
                # Get AAV and total commitment
                aav = calculate_aav(b)
                commitment = calculate_total_commitment(b)
                
                players.append({
                    "player": b,
                    "type": "batter",
                    "name": b.get("Name", ""),
                    "pos": pos,
                    "age": b.get("Age", ""),
                    "team": b.get("ORG", ""),
                    "war": war,
                    "aav": aav,
                    "contract_status": contract_status,
                    "yl": years_left,
                    "total_commitment": commitment["total_value"],
                    "dpw_display": dpw_display,
                    "dpw_value": dollars_per_war,
                    "surplus_display": surplus_display,
                    "surplus_value": surplus,
                    "category": full_category,
                    "category_name": category_name,
                    "trade_value": trade_value_data["trade_value"],
                    "trade_tier": trade_value_data["tier_icon"]
                })
        
        # Process pitchers
        if type_filter in ["All", "Pitchers"]:
            for p in all_pitchers:
                pos = p.get("POS", "")
                if pos == "CL":
                    pos = "RP"  # Treat CL as RP for filtering
                if pos_filter != "All" and pos != pos_filter:
                    continue
                
                war = parse_number(p.get("WAR (Pitcher)", p.get("WAR", 0)))
                if war < min_war:
                    continue
                
                # Parse YL once and reuse
                yl_data = parse_years_left(p.get("YL", ""))
                years_left = yl_data.get("years", 0)
                
                category_name, category_icon, category_color = get_contract_category(p, "pitcher")
                full_category = f"{category_icon} {category_name}"
                
                if category_filter != "All" and category_icon not in category_filter:
                    continue
                
                # Get contract status
                contract_status, status_key, status_color = get_contract_status(p)
                
                if status_filter != "All" and status_filter != contract_status:
                    continue
                
                dollars_per_war, dpw_display = calculate_dollars_per_war(p, "pitcher")
                surplus, surplus_display = calculate_surplus_value(p, "pitcher")
                trade_value_data = calculate_trade_value(p, "pitcher")
                
                # Get AAV and total commitment
                aav = calculate_aav(p)
                commitment = calculate_total_commitment(p)
                
                players.append({
                    "player": p,
                    "type": "pitcher",
                    "name": p.get("Name", ""),
                    "pos": p.get("POS", ""),
                    "age": p.get("Age", ""),
                    "team": p.get("ORG", ""),
                    "war": war,
                    "aav": aav,
                    "contract_status": contract_status,
                    "yl": years_left,
                    "total_commitment": commitment["total_value"],
                    "dpw_display": dpw_display,
                    "dpw_value": dollars_per_war,
                    "surplus_display": surplus_display,
                    "surplus_value": surplus,
                    "category": full_category,
                    "category_name": category_name,
                    "trade_value": trade_value_data["trade_value"],
                    "trade_tier": trade_value_data["tier_icon"]
                })
        
        # Sort by surplus value descending
        players.sort(key=lambda x: x["surplus_value"], reverse=True)
        return players
    
    def update_table():
        """Update the table with current filter settings"""
        table.delete(*table.get_children())
        id_map.clear()
        player_data_map.clear()
        
        players = get_filtered_players()
        
        for p in players:
            tag = get_tag_for_category(p["category"])
            
            values = (
                p["name"],
                p["pos"],
                p["age"],
                p["team"],
                round(p["war"], 1),
                f"${p['aav']:.1f}M" if p["aav"] > 0 else "-",
                p["contract_status"],
                int(p["yl"]) if p["yl"] > 0 else "-",
                f"${p['total_commitment']:.1f}M" if p["total_commitment"] > 0 else "-",
                p["dpw_display"],
                p["surplus_display"],
                p["category"],
                f"{p['trade_tier']} {p['trade_value']}"
            )
            
            iid = table.insert("", "end", values=values, tags=(tag,))
            player_id = p["player"].get("ID", "")
            if player_id:
                id_map[iid] = player_id
            player_data_map[iid] = p
        
        make_treeview_open_link_handler(table, id_map, lambda pid: player_url_template.format(pid=pid))
    
    # Bind filter changes
    type_combo.bind("<<ComboboxSelected>>", lambda e: update_table())
    pos_combo.bind("<<ComboboxSelected>>", lambda e: update_table())
    category_combo.bind("<<ComboboxSelected>>", lambda e: update_table())
    status_combo.bind("<<ComboboxSelected>>", lambda e: update_table())
    
    # Legend frame
    legend_frame = tk.Frame(analysis_frame, bg="#2d2d2d")
    legend_frame.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        legend_frame,
        text="Legend:",
        font=(font[0], font[1], "bold"),
        bg="#2d2d2d",
        fg="#d4d4d4"
    ).pack(side="left")
    
    legend_items = [
        ("💰 Surplus", "#51cf66", "High WAR, low AAV"),
        ("✅ Fair Value", "#ffd43b", "Normal AAV"),
        ("🚨 Albatross", "#ff6b6b", "High AAV, low WAR"),
        ("🎯 Arb Target", "#4dabf7", "Arb status, good stats"),
        ("📋 Extension", "#9775fa", "Has extension"),
    ]
    
    for label, color, desc in legend_items:
        tk.Label(
            legend_frame,
            text=f"  {label}",
            font=font,
            bg="#2d2d2d",
            fg=color
        ).pack(side="left", padx=(5, 0))
        tk.Label(
            legend_frame,
            text=f"({desc})",
            font=(font[0], font[1] - 2),
            bg="#2d2d2d",
            fg="#666666"
        ).pack(side="left")
    
    # ==================== EXTENSION WATCH TAB ====================
    extension_frame = tk.Frame(sub_notebook, bg="#2d2d2d")
    sub_notebook.add(extension_frame, text="📋 Extension Watch")
    
    # Extension header
    ext_header_frame = tk.Frame(extension_frame, bg="#2d2d2d")
    ext_header_frame.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        ext_header_frame,
        text="📋 Extension Watch",
        font=(font[0], font[1] + 2, "bold"),
        bg="#2d2d2d",
        fg="#9775fa"
    ).pack(side="left")
    
    tk.Label(
        ext_header_frame,
        text="Players with pending/accepted extensions - evaluate deal quality",
        font=(font[0], font[1] - 1),
        bg="#2d2d2d",
        fg="#888888"
    ).pack(side="left", padx=(10, 0))
    
    # Extension filter controls
    ext_filter_frame = tk.Frame(extension_frame, bg="#2d2d2d")
    ext_filter_frame.pack(fill="x", padx=5, pady=5)
    
    # Grade filter
    tk.Label(ext_filter_frame, text="Grade:", bg="#2d2d2d", fg="#d4d4d4", font=font).pack(side="left")
    ext_grade_var = tk.StringVar(value="All")
    ext_grade_combo = ttk.Combobox(
        ext_filter_frame,
        textvariable=ext_grade_var,
        values=["All", "💎 Steal", "✅ Fair", "⚠️ Risky", "🚨 Overpay"],
        state="readonly",
        width=12
    )
    ext_grade_combo.pack(side="left", padx=5)
    
    # Type filter
    tk.Label(ext_filter_frame, text="Type:", bg="#2d2d2d", fg="#d4d4d4", font=font).pack(side="left", padx=(10, 0))
    ext_type_var = tk.StringVar(value="All")
    ext_type_combo = ttk.Combobox(
        ext_filter_frame,
        textvariable=ext_type_var,
        values=["All", "Batters", "Pitchers"],
        state="readonly",
        width=10
    )
    ext_type_combo.pack(side="left", padx=5)
    
    # Update button
    ext_update_btn = ttk.Button(ext_filter_frame, text="Update", command=lambda: update_extension_table())
    ext_update_btn.pack(side="left", padx=10)
    
    # Extension table frame
    ext_table_frame = tk.Frame(extension_frame, bg="#2d2d2d")
    ext_table_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    ext_vsb = ttk.Scrollbar(ext_table_frame, orient="vertical")
    ext_vsb.pack(side="right", fill="y")
    
    ext_hsb = ttk.Scrollbar(ext_table_frame, orient="horizontal")
    ext_hsb.pack(side="bottom", fill="x")
    
    # Extension table columns
    ext_cols = ("Name", "POS", "Age", "Team", "OVR", "Current AAV", "Ext AAV", "Total Years", "Total $", "Grade", "Red Flags")
    ext_table = ttk.Treeview(
        ext_table_frame,
        columns=ext_cols,
        show="headings",
        yscrollcommand=ext_vsb.set,
        xscrollcommand=ext_hsb.set,
        height=18
    )
    ext_table.pack(side="left", fill="both", expand=True)
    ext_vsb.config(command=ext_table.yview)
    ext_hsb.config(command=ext_table.xview)
    
    ext_col_widths = {
        "Name": 130, "POS": 40, "Age": 35, "Team": 50, "OVR": 45,
        "Current AAV": 80, "Ext AAV": 80, "Total Years": 70, "Total $": 80,
        "Grade": 75, "Red Flags": 180
    }
    for col in ext_cols:
        ext_table.heading(col, text=col, command=lambda c=col: sort_treeview(ext_table, c, False))
        ext_table.column(col, width=ext_col_widths.get(col, 80), minwidth=30, anchor="center", stretch=True)
    
    # Configure tags for extension grades
    ext_table.tag_configure("hover", background="#333")
    ext_table.tag_configure("steal", background="#2d4a2d")  # Green
    ext_table.tag_configure("fair", background="#4a4a2d")   # Yellow
    ext_table.tag_configure("risky", background="#4a3a2d")  # Orange
    ext_table.tag_configure("overpay", background="#4a2d2d")  # Red
    
    ext_table._prev_hover = None
    ext_table.bind("<Motion>", on_treeview_motion)
    ext_table.bind("<Leave>", on_leave)
    
    ext_id_map = {}
    ext_player_data_map = {}  # Maps iid -> player data for right-click
    
    # Bind right-click for player card popup (extension table)
    bind_player_card_right_click(ext_table, ext_player_data_map, lambda p: (p["player"], p["type"]))
    
    def get_players_with_extensions():
        """Get all players with extensions"""
        grade_filter = ext_grade_var.get()
        type_filter = ext_type_var.get()
        
        players = []
        
        def process_player(p, player_type):
            extension = get_extension_analysis(p, player_type)
            if not extension.get("has_extension", False):
                return None
            
            grade = extension.get("grade", "")
            grade_icon = extension.get("grade_icon", "")
            
            # Apply grade filter
            if grade_filter != "All" and grade_icon not in grade_filter:
                return None
            
            # Get current AAV
            aav = calculate_aav(p)
            
            return {
                "player": p,
                "type": player_type,
                "name": p.get("Name", ""),
                "pos": p.get("POS", ""),
                "age": p.get("Age", ""),
                "team": p.get("ORG", ""),
                "ovr": p.get("OVR", ""),
                "current_aav": aav,
                "extension_aav": extension.get("extension_aav", 0),
                "total_years": extension.get("total_years", 0),
                "total_commitment": extension.get("total_commitment", 0),
                "grade": grade,
                "grade_icon": grade_icon,
                "red_flags": extension.get("red_flags", [])
            }
        
        # Process batters
        if type_filter in ["All", "Batters"]:
            for b in all_batters:
                result = process_player(b, "batter")
                if result:
                    players.append(result)
        
        # Process pitchers
        if type_filter in ["All", "Pitchers"]:
            for p in all_pitchers:
                result = process_player(p, "pitcher")
                if result:
                    players.append(result)
        
        # Sort by extension AAV descending
        players.sort(key=lambda x: x["extension_aav"], reverse=True)
        return players
    
    def update_extension_table():
        """Update the extension watch table"""
        ext_table.delete(*ext_table.get_children())
        ext_id_map.clear()
        ext_player_data_map.clear()
        
        players = get_players_with_extensions()
        
        for p in players:
            tag = p["grade"]  # Use grade as tag
            
            red_flags_str = "; ".join(p["red_flags"]) if p["red_flags"] else "-"
            
            values = (
                p["name"],
                p["pos"],
                p["age"],
                p["team"],
                p["ovr"],
                f"${p['current_aav']:.1f}M" if p["current_aav"] > 0 else "-",
                f"${p['extension_aav']:.1f}M" if p["extension_aav"] > 0 else "-",
                int(p["total_years"]) if p["total_years"] > 0 else "-",
                f"${p['total_commitment']:.1f}M" if p["total_commitment"] > 0 else "-",
                f"{p['grade_icon']} {p['grade'].title()}",
                red_flags_str
            )
            
            iid = ext_table.insert("", "end", values=values, tags=(tag,))
            player_id = p["player"].get("ID", "")
            if player_id:
                ext_id_map[iid] = player_id
            ext_player_data_map[iid] = p
        
        make_treeview_open_link_handler(ext_table, ext_id_map, lambda pid: player_url_template.format(pid=pid))
    
    # Bind extension filter changes
    ext_grade_combo.bind("<<ComboboxSelected>>", lambda e: update_extension_table())
    ext_type_combo.bind("<<ComboboxSelected>>", lambda e: update_extension_table())
    
    # Extension legend frame
    ext_legend_frame = tk.Frame(extension_frame, bg="#2d2d2d")
    ext_legend_frame.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        ext_legend_frame,
        text="Extension Grades:",
        font=(font[0], font[1], "bold"),
        bg="#2d2d2d",
        fg="#d4d4d4"
    ).pack(side="left")
    
    ext_legend_items = [
        ("💎 Steal", "#51cf66", "AAV well below market"),
        ("✅ Fair", "#ffd43b", "AAV appropriate for production"),
        ("⚠️ Risky", "#ff922b", "High AAV with concerns"),
        ("🚨 Overpay", "#ff6b6b", "AAV exceeds value"),
    ]
    
    for label, color, desc in ext_legend_items:
        tk.Label(
            ext_legend_frame,
            text=f"  {label}",
            font=font,
            bg="#2d2d2d",
            fg=color
        ).pack(side="left", padx=(8, 0))
        tk.Label(
            ext_legend_frame,
            text=f"({desc})",
            font=(font[0], font[1] - 2),
            bg="#2d2d2d",
            fg="#666666"
        ).pack(side="left")
    
    class ContractValueTab:
        def refresh(self, pitchers, batters):
            all_pitchers.clear()
            all_batters.clear()
            all_pitchers.extend(pitchers)
            all_batters.extend(batters)
            update_table()
            update_extension_table()
    
    return ContractValueTab()
