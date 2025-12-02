# Roster Builder Tab
# UI for building hypothetical rosters and evaluating team composition

import tkinter as tk
from tkinter import ttk
from .style import on_treeview_motion, on_leave, sort_treeview
from .widgets import make_treeview_open_link_handler, load_player_url_template
from roster_builder import (
    RosterBuilder, LINEUP_SLOTS, BENCH_COUNT, ROTATION_COUNT, BULLPEN_COUNT,
    find_trade_targets_by_position, get_availability_tier
)
from archetypes import ARCHETYPES, find_players_by_archetype
from trade_value import parse_salary

player_url_template = load_player_url_template()


def add_roster_builder_tab(notebook, font):
    roster_frame = ttk.Frame(notebook)
    notebook.add(roster_frame, text="Roster Builder")
    
    # Data storage
    all_pitchers = []
    all_batters = []
    roster_builder = RosterBuilder()
    
    # Header
    header_frame = tk.Frame(roster_frame, bg="#1e1e1e")
    header_frame.pack(fill="x", padx=10, pady=5)
    
    tk.Label(
        header_frame,
        text="📋 Roster Builder Sandbox",
        font=(font[0], font[1] + 4, "bold"),
        bg="#1e1e1e",
        fg="#00ff7f"
    ).pack(side="left")
    
    tk.Label(
        header_frame,
        text="Build hypothetical rosters from any team",
        font=(font[0], font[1] - 1),
        bg="#1e1e1e",
        fg="#888888"
    ).pack(side="left", padx=(20, 0))
    
    # Clear roster button
    clear_btn = ttk.Button(header_frame, text="Clear Roster", command=lambda: clear_roster())
    clear_btn.pack(side="right", padx=5)
    
    # Main layout - 3 columns
    main_container = tk.Frame(roster_frame, bg="#1e1e1e")
    main_container.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Left panel - Player Pool
    left_frame = tk.Frame(main_container, bg="#1e1e1e", width=450)
    left_frame.pack(side="left", fill="both", expand=True, padx=5)
    left_frame.pack_propagate(False)
    
    tk.Label(
        left_frame,
        text="Player Pool",
        font=(font[0], font[1] + 1, "bold"),
        bg="#1e1e1e",
        fg="#d4d4d4"
    ).pack(fill="x", pady=(0, 5))
    
    # Pool filters
    pool_filter_frame = tk.Frame(left_frame, bg="#1e1e1e")
    pool_filter_frame.pack(fill="x", pady=5)
    
    # Search
    tk.Label(pool_filter_frame, text="Search:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left")
    search_var = tk.StringVar()
    search_entry = tk.Entry(
        pool_filter_frame, textvariable=search_var, width=15,
        bg="#000000", fg="#d4d4d4", insertbackground="#00ff7f",
        highlightthickness=0, relief="flat", font=font
    )
    search_entry.pack(side="left", padx=5)
    
    # Position filter
    tk.Label(pool_filter_frame, text="Pos:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left", padx=(10, 0))
    pos_var = tk.StringVar(value="All")
    pos_combo = ttk.Combobox(
        pool_filter_frame,
        textvariable=pos_var,
        values=["All", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH", "SP", "RP"],
        state="readonly",
        width=6
    )
    pos_combo.pack(side="left", padx=5)
    
    # Team filter
    tk.Label(pool_filter_frame, text="Team:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left", padx=(10, 0))
    team_var = tk.StringVar(value="All")
    team_combo = ttk.Combobox(
        pool_filter_frame,
        textvariable=team_var,
        values=["All"],
        state="readonly",
        width=8
    )
    team_combo.pack(side="left", padx=5)
    
    # Player pool table
    pool_table_frame = tk.Frame(left_frame, bg="#1e1e1e")
    pool_table_frame.pack(fill="both", expand=True)
    
    pool_vsb = ttk.Scrollbar(pool_table_frame, orient="vertical")
    pool_vsb.pack(side="right", fill="y")
    
    pool_cols = ("Name", "Team", "POS", "Age", "OVR", "WAR")
    pool_table = ttk.Treeview(
        pool_table_frame,
        columns=pool_cols,
        show="headings",
        yscrollcommand=pool_vsb.set,
        height=15
    )
    pool_table.pack(side="left", fill="both", expand=True)
    pool_vsb.config(command=pool_table.yview)
    
    pool_col_widths = {"Name": 120, "Team": 50, "POS": 40, "Age": 35, "OVR": 40, "WAR": 40}
    for col in pool_cols:
        pool_table.heading(col, text=col, command=lambda c=col: sort_treeview(pool_table, c, False))
        pool_table.column(col, width=pool_col_widths.get(col, 60), minwidth=30, anchor="center", stretch=True)
    
    pool_table.tag_configure("hover", background="#333")
    pool_table.tag_configure("on_roster", background="#2d4a2d")
    pool_table._prev_hover = None
    pool_table.bind("<Motion>", on_treeview_motion)
    pool_table.bind("<Leave>", on_leave)
    
    pool_id_map = {}
    
    # Add to roster buttons
    add_btn_frame = tk.Frame(left_frame, bg="#1e1e1e")
    add_btn_frame.pack(fill="x", pady=5)
    
    def add_selected_to_lineup():
        selected = pool_table.selection()
        if selected:
            item = pool_table.item(selected[0])
            name = item["values"][0]
            pos = item["values"][2]
            player = find_player_by_name(name)
            if player:
                # Determine slot based on position
                if pos in LINEUP_SLOTS:
                    roster_builder.add_to_lineup(player, pos)
                elif pos == "SP":
                    roster_builder.add_to_rotation(player)
                elif pos in ["RP", "CL"]:
                    roster_builder.add_to_bullpen(player)
                update_roster_display()
                update_pool_table()
    
    def add_selected_to_bench():
        selected = pool_table.selection()
        if selected:
            item = pool_table.item(selected[0])
            name = item["values"][0]
            player = find_player_by_name(name)
            if player:
                pos = player.get("POS", "")
                if pos in ["SP", "RP", "CL", "P"]:
                    roster_builder.add_to_bullpen(player)
                else:
                    roster_builder.add_to_bench(player)
                update_roster_display()
                update_pool_table()
    
    ttk.Button(add_btn_frame, text="Add to Lineup/Rotation", command=add_selected_to_lineup).pack(side="left", padx=5)
    ttk.Button(add_btn_frame, text="Add to Bench/Bullpen", command=add_selected_to_bench).pack(side="left", padx=5)
    
    # Center panel - Your Roster
    center_frame = tk.Frame(main_container, bg="#1e1e1e", width=350)
    center_frame.pack(side="left", fill="both", padx=5)
    center_frame.pack_propagate(False)
    
    tk.Label(
        center_frame,
        text="Your Roster",
        font=(font[0], font[1] + 1, "bold"),
        bg="#1e1e1e",
        fg="#d4d4d4"
    ).pack(fill="x", pady=(0, 5))
    
    # Roster display frame with scrolling
    roster_canvas = tk.Canvas(center_frame, bg="#1e1e1e", highlightthickness=0)
    roster_scrollbar = ttk.Scrollbar(center_frame, orient="vertical", command=roster_canvas.yview)
    roster_display_frame = tk.Frame(roster_canvas, bg="#1e1e1e")
    
    roster_canvas.configure(yscrollcommand=roster_scrollbar.set)
    
    roster_scrollbar.pack(side="right", fill="y")
    roster_canvas.pack(side="left", fill="both", expand=True)
    roster_canvas.create_window((0, 0), window=roster_display_frame, anchor="nw")
    
    def on_frame_configure(event):
        roster_canvas.configure(scrollregion=roster_canvas.bbox("all"))
    
    roster_display_frame.bind("<Configure>", on_frame_configure)
    
    # Roster slot widgets (will be populated)
    roster_slot_vars = {}
    roster_slot_labels = {}
    
    def create_roster_slots():
        """Create roster slot display widgets"""
        # Clear existing
        for widget in roster_display_frame.winfo_children():
            widget.destroy()
        roster_slot_vars.clear()
        roster_slot_labels.clear()
        
        # Lineup section
        lineup_header = tk.Label(
            roster_display_frame,
            text="LINEUP",
            font=(font[0], font[1], "bold"),
            bg="#2a2a2a",
            fg="#00ff7f"
        )
        lineup_header.pack(fill="x", pady=(0, 5))
        
        for pos in LINEUP_SLOTS:
            slot_frame = tk.Frame(roster_display_frame, bg="#1e1e1e")
            slot_frame.pack(fill="x", pady=2)
            
            tk.Label(
                slot_frame,
                text=f"{pos}:",
                width=4,
                font=font,
                bg="#1e1e1e",
                fg="#888888",
                anchor="e"
            ).pack(side="left")
            
            slot_var = tk.StringVar(value="")
            roster_slot_vars[pos] = slot_var
            
            slot_label = tk.Label(
                slot_frame,
                textvariable=slot_var,
                font=font,
                bg="#2a2a2a",
                fg="#d4d4d4",
                anchor="w",
                width=25
            )
            slot_label.pack(side="left", padx=5, fill="x", expand=True)
            roster_slot_labels[pos] = slot_label
            
            # Remove button
            remove_btn = tk.Label(
                slot_frame,
                text="✕",
                font=font,
                bg="#2a2a2a",
                fg="#ff6b6b",
                cursor="hand2"
            )
            remove_btn.pack(side="right", padx=2)
            
            def make_remove_handler(p):
                def handler(e):
                    player = roster_builder.lineup.get(p)
                    if player:
                        roster_builder.remove_player(player)
                        update_roster_display()
                        update_pool_table()
                return handler
            
            remove_btn.bind("<Button-1>", make_remove_handler(pos))
        
        # Bench section
        tk.Label(
            roster_display_frame,
            text=f"BENCH ({BENCH_COUNT})",
            font=(font[0], font[1], "bold"),
            bg="#2a2a2a",
            fg="#00ff7f"
        ).pack(fill="x", pady=(15, 5))
        
        for i in range(BENCH_COUNT):
            slot_key = f"BN{i+1}"
            slot_frame = tk.Frame(roster_display_frame, bg="#1e1e1e")
            slot_frame.pack(fill="x", pady=2)
            
            tk.Label(
                slot_frame,
                text=f"BN:",
                width=4,
                font=font,
                bg="#1e1e1e",
                fg="#888888",
                anchor="e"
            ).pack(side="left")
            
            slot_var = tk.StringVar(value="")
            roster_slot_vars[slot_key] = slot_var
            
            slot_label = tk.Label(
                slot_frame,
                textvariable=slot_var,
                font=font,
                bg="#2a2a2a",
                fg="#d4d4d4",
                anchor="w",
                width=25
            )
            slot_label.pack(side="left", padx=5, fill="x", expand=True)
            roster_slot_labels[slot_key] = slot_label
        
        # Rotation section
        tk.Label(
            roster_display_frame,
            text=f"ROTATION ({ROTATION_COUNT})",
            font=(font[0], font[1], "bold"),
            bg="#2a2a2a",
            fg="#00ff7f"
        ).pack(fill="x", pady=(15, 5))
        
        for i in range(ROTATION_COUNT):
            slot_key = f"SP{i+1}"
            slot_frame = tk.Frame(roster_display_frame, bg="#1e1e1e")
            slot_frame.pack(fill="x", pady=2)
            
            tk.Label(
                slot_frame,
                text=f"SP{i+1}:",
                width=4,
                font=font,
                bg="#1e1e1e",
                fg="#888888",
                anchor="e"
            ).pack(side="left")
            
            slot_var = tk.StringVar(value="")
            roster_slot_vars[slot_key] = slot_var
            
            slot_label = tk.Label(
                slot_frame,
                textvariable=slot_var,
                font=font,
                bg="#2a2a2a",
                fg="#d4d4d4",
                anchor="w",
                width=25
            )
            slot_label.pack(side="left", padx=5, fill="x", expand=True)
            roster_slot_labels[slot_key] = slot_label
        
        # Bullpen section
        tk.Label(
            roster_display_frame,
            text=f"BULLPEN ({BULLPEN_COUNT})",
            font=(font[0], font[1], "bold"),
            bg="#2a2a2a",
            fg="#00ff7f"
        ).pack(fill="x", pady=(15, 5))
        
        for i in range(BULLPEN_COUNT):
            slot_key = f"RP{i+1}"
            slot_frame = tk.Frame(roster_display_frame, bg="#1e1e1e")
            slot_frame.pack(fill="x", pady=2)
            
            tk.Label(
                slot_frame,
                text=f"RP{i+1}:",
                width=4,
                font=font,
                bg="#1e1e1e",
                fg="#888888",
                anchor="e"
            ).pack(side="left")
            
            slot_var = tk.StringVar(value="")
            roster_slot_vars[slot_key] = slot_var
            
            slot_label = tk.Label(
                slot_frame,
                textvariable=slot_var,
                font=font,
                bg="#2a2a2a",
                fg="#d4d4d4",
                anchor="w",
                width=25
            )
            slot_label.pack(side="left", padx=5, fill="x", expand=True)
            roster_slot_labels[slot_key] = slot_label
    
    # Right panel - Team Summary
    right_frame = tk.Frame(main_container, bg="#1e1e1e", width=280)
    right_frame.pack(side="right", fill="both", padx=5)
    right_frame.pack_propagate(False)
    
    tk.Label(
        right_frame,
        text="Team Summary",
        font=(font[0], font[1] + 1, "bold"),
        bg="#1e1e1e",
        fg="#d4d4d4"
    ).pack(fill="x", pady=(0, 5))
    
    # Summary stats
    summary_frame = tk.Frame(right_frame, bg="#2a2a2a", relief="raised", bd=1)
    summary_frame.pack(fill="x", pady=5)
    
    summary_vars = {
        "total_war": tk.StringVar(value="0"),
        "total_salary": tk.StringVar(value="$0M"),
        "avg_age": tk.StringVar(value="0"),
        "avg_ovr": tk.StringVar(value="0"),
        "archetype": tk.StringVar(value="-"),
    }
    
    stats = [
        ("Total WAR:", "total_war"),
        ("Total Salary:", "total_salary"),
        ("Avg Age:", "avg_age"),
        ("Avg OVR:", "avg_ovr"),
        ("Archetype Fit:", "archetype"),
    ]
    
    for label_text, var_key in stats:
        row = tk.Frame(summary_frame, bg="#2a2a2a")
        row.pack(fill="x", padx=10, pady=3)
        
        tk.Label(
            row, text=label_text, font=font,
            bg="#2a2a2a", fg="#888888", anchor="w", width=14
        ).pack(side="left")
        
        tk.Label(
            row, textvariable=summary_vars[var_key], font=(font[0], font[1], "bold"),
            bg="#2a2a2a", fg="#00ff7f", anchor="e"
        ).pack(side="right")
    
    # Position grades
    tk.Label(
        right_frame,
        text="Position Grades",
        font=(font[0], font[1], "bold"),
        bg="#1e1e1e",
        fg="#d4d4d4"
    ).pack(fill="x", pady=(15, 5))
    
    grades_frame = tk.Frame(right_frame, bg="#2a2a2a", relief="raised", bd=1)
    grades_frame.pack(fill="x", pady=5)
    
    grade_vars = {}
    position_groups = ["C", "1B", "2B", "3B", "SS", "OF", "SP", "RP"]
    
    for i, pos in enumerate(position_groups):
        row = i // 4
        col = i % 4
        
        if i % 4 == 0:
            grade_row = tk.Frame(grades_frame, bg="#2a2a2a")
            grade_row.pack(fill="x", padx=5, pady=3)
        
        cell = tk.Frame(grade_row, bg="#2a2a2a")
        cell.pack(side="left", padx=5)
        
        tk.Label(cell, text=f"{pos}:", font=font, bg="#2a2a2a", fg="#888888").pack(side="left")
        
        grade_var = tk.StringVar(value="-")
        grade_vars[pos] = grade_var
        
        tk.Label(cell, textvariable=grade_var, font=(font[0], font[1], "bold"), bg="#2a2a2a", fg="#d4d4d4").pack(side="left", padx=3)
    
    # Helper functions
    def find_player_by_name(name):
        """Find a player by name from all players"""
        for p in all_batters:
            if p.get("Name", "") == name:
                return p
        for p in all_pitchers:
            if p.get("Name", "") == name:
                return p
        return None
    
    def get_war(player, player_type="batter"):
        """Get WAR for a player"""
        if player_type == "pitcher":
            val = player.get("WAR (Pitcher)", player.get("WAR", 0))
        else:
            val = player.get("WAR (Batter)", player.get("WAR", 0))
        try:
            return float(str(val).replace("-", "0"))
        except:
            return 0
    
    def get_ovr(player):
        """Get OVR for a player"""
        ovr = player.get("OVR", "0")
        if "Stars" in str(ovr):
            try:
                return float(str(ovr).split()[0])
            except:
                return 0
        try:
            return float(ovr)
        except:
            return 0
    
    def update_pool_table():
        """Update the player pool table"""
        pool_table.delete(*pool_table.get_children())
        pool_id_map.clear()
        
        pos_filter = pos_var.get()
        team_filter = team_var.get()
        search_filter = search_var.get().lower()
        
        # Combine batters and pitchers
        all_players = []
        
        for b in all_batters:
            pos = b.get("POS", "")
            if pos_filter != "All" and pos != pos_filter:
                continue
            team = b.get("ORG", "")
            if team_filter != "All" and team != team_filter:
                continue
            if search_filter and search_filter not in b.get("Name", "").lower():
                continue
            all_players.append((b, "batter"))
        
        for p in all_pitchers:
            pos = p.get("POS", "")
            if pos_filter == "RP" and pos not in ["RP", "CL"]:
                continue
            elif pos_filter != "All" and pos_filter != "RP" and pos != pos_filter:
                continue
            team = p.get("ORG", "")
            if team_filter != "All" and team != team_filter:
                continue
            if search_filter and search_filter not in p.get("Name", "").lower():
                continue
            all_players.append((p, "pitcher"))
        
        # Sort by OVR
        all_players.sort(key=lambda x: get_ovr(x[0]), reverse=True)
        
        for player, ptype in all_players:
            tags = []
            if roster_builder.is_player_on_roster(player):
                tags.append("on_roster")
            
            war = get_war(player, ptype)
            ovr = get_ovr(player)
            
            values = (
                player.get("Name", ""),
                player.get("ORG", ""),
                player.get("POS", ""),
                player.get("Age", ""),
                f"{ovr:.1f}",
                f"{war:.1f}"
            )
            
            iid = pool_table.insert("", "end", values=values, tags=tags)
            player_id = player.get("ID", "")
            if player_id:
                pool_id_map[iid] = player_id
        
        make_treeview_open_link_handler(pool_table, pool_id_map, lambda pid: player_url_template.format(pid=pid))
    
    def update_roster_display():
        """Update the roster display slots and summary"""
        # Update lineup slots
        for pos in LINEUP_SLOTS:
            player = roster_builder.lineup.get(pos)
            if player:
                roster_slot_vars[pos].set(f"{player.get('Name', '')} ({get_ovr(player):.1f})")
            else:
                roster_slot_vars[pos].set("")
        
        # Update bench
        for i in range(BENCH_COUNT):
            slot_key = f"BN{i+1}"
            if i < len(roster_builder.bench):
                player = roster_builder.bench[i]
                roster_slot_vars[slot_key].set(f"{player.get('Name', '')} ({get_ovr(player):.1f})")
            else:
                roster_slot_vars[slot_key].set("")
        
        # Update rotation
        for i in range(ROTATION_COUNT):
            slot_key = f"SP{i+1}"
            if i < len(roster_builder.rotation):
                player = roster_builder.rotation[i]
                roster_slot_vars[slot_key].set(f"{player.get('Name', '')} ({get_ovr(player):.1f})")
            else:
                roster_slot_vars[slot_key].set("")
        
        # Update bullpen
        for i in range(BULLPEN_COUNT):
            slot_key = f"RP{i+1}"
            if i < len(roster_builder.bullpen):
                player = roster_builder.bullpen[i]
                roster_slot_vars[slot_key].set(f"{player.get('Name', '')} ({get_ovr(player):.1f})")
            else:
                roster_slot_vars[slot_key].set("")
        
        # Update summary
        summary = roster_builder.get_roster_summary()
        
        summary_vars["total_war"].set(f"{summary['total_war']}")
        summary_vars["total_salary"].set(f"${summary['total_salary']:.1f}M")
        summary_vars["avg_age"].set(f"{summary['avg_age']:.1f}")
        summary_vars["avg_ovr"].set(f"{summary['avg_ovr']:.1f}")
        
        archetype = summary.get("archetype_fit")
        if archetype:
            summary_vars["archetype"].set(f"{archetype['icon']} {archetype['name']}")
        else:
            summary_vars["archetype"].set("-")
        
        # Update position grades
        for pos, grade_info in summary.get("position_grades", {}).items():
            if pos in grade_vars:
                grade_vars[pos].set(grade_info.get("grade", "-"))
    
    def clear_roster():
        """Clear the entire roster"""
        roster_builder.clear_roster()
        update_roster_display()
        update_pool_table()
    
    def update_team_filter():
        """Update team filter options"""
        teams = set()
        for b in all_batters:
            teams.add(b.get("ORG", ""))
        for p in all_pitchers:
            teams.add(p.get("ORG", ""))
        teams.discard("")
        
        sorted_teams = sorted(teams)
        team_combo["values"] = ["All"] + sorted_teams
    
    # Bind filter changes
    pos_combo.bind("<<ComboboxSelected>>", lambda e: update_pool_table())
    team_combo.bind("<<ComboboxSelected>>", lambda e: update_pool_table())
    search_var.trace_add("write", lambda *_: update_pool_table())
    
    # Double-click to add
    def on_pool_double_click(event):
        add_selected_to_lineup()
    
    pool_table.bind("<Double-1>", on_pool_double_click)
    
    class RosterBuilderTab:
        def refresh(self, pitchers, batters):
            all_pitchers.clear()
            all_batters.clear()
            all_pitchers.extend(pitchers)
            all_batters.extend(batters)
            roster_builder.set_player_pools(batters, pitchers)
            update_team_filter()
            create_roster_slots()
            update_pool_table()
            update_roster_display()
    
    return RosterBuilderTab()
