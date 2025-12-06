# Autocontract Generator Tab
# GUI for generating realistic competing contract offers for free agents

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .style import on_treeview_motion, on_leave, sort_treeview
from auto_contract import (
    TeamArchetype,
    generate_contract_offers,
    parse_player_from_dict,
    calculate_market_dollar_per_war
)
from gui.core import parse_players_from_html

# Theme colors
DARK_BG = "#2d2d2d"
NEON_GREEN = "#29ff9e"


def add_auto_contract_tab(notebook, font):
    """Add the Autocontract Generator tab to the notebook"""
    auto_contract_frame = ttk.Frame(notebook)
    notebook.add(auto_contract_frame, text="Autocontract")
    
    # Data storage
    free_agents = []
    all_players = []  # For market calculation
    market_dollar_per_war = [8.0]  # Mutable reference
    selected_free_agent = [None]  # Currently selected player
    
    # Main container
    main_container = tk.Frame(auto_contract_frame, bg=DARK_BG)
    main_container.pack(fill="both", expand=True, padx=5, pady=5)
    
    # ==================================================
    # LEFT SIDE: Free Agent Pool & Settings
    # ==================================================
    left_panel = tk.Frame(main_container, bg=DARK_BG, relief="ridge", bd=2)
    left_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))
    
    # Free Agent Pool Header
    fa_header = tk.Frame(left_panel, bg=DARK_BG)
    fa_header.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        fa_header,
        text="Free Agent Pool",
        font=(font[0], font[1] + 2, "bold"),
        bg=DARK_BG,
        fg=NEON_GREEN
    ).pack(side="left")
    
    # Load button
    def load_free_agents():
        """Load free agents from Free Agents.html"""
        file_path = "Free Agents.html"
        try:
            players = parse_players_from_html(file_path)
            free_agents.clear()
            free_agents.extend(players)
            
            # Update treeview
            update_free_agents_tree()
            
            messagebox.showinfo(
                "Success",
                f"Loaded {len(free_agents)} free agents from Free Agents.html"
            )
        except FileNotFoundError:
            messagebox.showerror(
                "File Not Found",
                "Could not find 'Free Agents.html' in the current directory.\n\n"
                "Please export free agents from OOTP using the same process as Player List.html"
            )
        except Exception as e:
            messagebox.showerror(
                "Load Error",
                f"Error loading Free Agents.html:\n\n{str(e)}"
            )
    
    load_btn = ttk.Button(fa_header, text="Load Free Agents.html", command=load_free_agents)
    load_btn.pack(side="right", padx=5)
    
    # Free Agents Treeview
    fa_tree_frame = tk.Frame(left_panel, bg=DARK_BG)
    fa_tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    fa_vsb = ttk.Scrollbar(fa_tree_frame, orient="vertical")
    fa_vsb.pack(side="right", fill="y")
    
    fa_hsb = ttk.Scrollbar(fa_tree_frame, orient="horizontal")
    fa_hsb.pack(side="bottom", fill="x")
    
    fa_cols = ("Name", "Age", "POS", "WAR", "Stat+", "OVR")
    fa_tree = ttk.Treeview(
        fa_tree_frame,
        columns=fa_cols,
        show="headings",
        yscrollcommand=fa_vsb.set,
        xscrollcommand=fa_hsb.set,
        height=15
    )
    fa_tree.pack(side="left", fill="both", expand=True)
    fa_vsb.config(command=fa_tree.yview)
    fa_hsb.config(command=fa_tree.xview)
    
    # Configure columns
    fa_tree.heading("Name", text="Name", command=lambda: sort_treeview(fa_tree, "Name", False))
    fa_tree.heading("Age", text="Age", command=lambda: sort_treeview(fa_tree, "Age", False))
    fa_tree.heading("POS", text="POS", command=lambda: sort_treeview(fa_tree, "POS", False))
    fa_tree.heading("WAR", text="WAR", command=lambda: sort_treeview(fa_tree, "WAR", False))
    fa_tree.heading("Stat+", text="Stat+", command=lambda: sort_treeview(fa_tree, "Stat+", False))
    fa_tree.heading("OVR", text="OVR", command=lambda: sort_treeview(fa_tree, "OVR", False))
    
    fa_tree.column("Name", width=150, minwidth=100)
    fa_tree.column("Age", width=50, minwidth=40, anchor="center")
    fa_tree.column("POS", width=50, minwidth=40, anchor="center")
    fa_tree.column("WAR", width=60, minwidth=50, anchor="center")
    fa_tree.column("Stat+", width=60, minwidth=50, anchor="center")
    fa_tree.column("OVR", width=60, minwidth=50, anchor="center")
    
    fa_tree.tag_configure("hover", background="#333")
    fa_tree._prev_hover = None
    fa_tree.bind("<Motion>", on_treeview_motion)
    fa_tree.bind("<Leave>", on_leave)
    
    def update_free_agents_tree():
        """Update the free agents treeview"""
        fa_tree.delete(*fa_tree.get_children())
        
        for player in free_agents:
            name = player.get("Name", "")
            age = player.get("Age", "")
            pos = player.get("POS", "")
            
            # Get WAR based on position
            player_type = "pitcher" if pos.upper() in ["SP", "RP", "CL", "P"] else "batter"
            if player_type == "pitcher":
                war = player.get("WAR (Pitcher)", player.get("WAR", "-"))
                stat_plus = player.get("ERA+", "-")
            else:
                war = player.get("WAR (Batter)", player.get("WAR", "-"))
                stat_plus = player.get("wRC+", "-")
            
            ovr = player.get("OVR", "-")
            
            fa_tree.insert("", "end", values=(name, age, pos, war, stat_plus, ovr), tags=(name,))
    
    def on_free_agent_select(event):
        """Handle free agent selection"""
        selection = fa_tree.selection()
        if not selection:
            return
        
        # Get selected player
        item = fa_tree.item(selection[0])
        name = item['values'][0]
        
        # Find player in data
        for player in free_agents:
            if player.get("Name") == name:
                selected_free_agent[0] = player
                update_selected_player_info()
                generate_contracts()
                break
    
    fa_tree.bind("<<TreeviewSelect>>", on_free_agent_select)
    
    # ==================================================
    # SETTINGS PANELS
    # ==================================================
    
    # Market Settings Panel
    market_frame = tk.Frame(left_panel, bg=DARK_BG, relief="ridge", bd=2)
    market_frame.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        market_frame,
        text="Market Settings",
        font=(font[0], font[1] + 1, "bold"),
        bg=DARK_BG,
        fg=NEON_GREEN
    ).pack(anchor="w", padx=5, pady=(5, 2))
    
    # $/WAR Baseline
    war_frame = tk.Frame(market_frame, bg=DARK_BG)
    war_frame.pack(fill="x", padx=5, pady=2)
    
    tk.Label(war_frame, text="$/WAR Baseline:", bg=DARK_BG, fg="#d4d4d4", font=font).pack(side="left")
    dollar_per_war_var = tk.StringVar(value="8.0")
    dollar_per_war_entry = tk.Entry(
        war_frame,
        textvariable=dollar_per_war_var,
        width=8,
        bg="#000000",
        fg="#d4d4d4",
        font=font
    )
    dollar_per_war_entry.pack(side="left", padx=5)
    tk.Label(war_frame, text="(millions)", bg=DARK_BG, fg="#888888", font=(font[0], font[1] - 1)).pack(side="left")
    
    # Eye Test Weight
    eye_test_frame = tk.Frame(market_frame, bg=DARK_BG)
    eye_test_frame.pack(fill="x", padx=5, pady=2)
    
    tk.Label(eye_test_frame, text="Eye Test Weight:", bg=DARK_BG, fg="#d4d4d4", font=font).pack(side="left")
    eye_test_var = tk.DoubleVar(value=15.0)
    eye_test_scale = tk.Scale(
        eye_test_frame,
        from_=0,
        to=30,
        orient="horizontal",
        variable=eye_test_var,
        bg=DARK_BG,
        fg="#d4d4d4",
        highlightthickness=0,
        troughcolor="#000000",
        length=200
    )
    eye_test_scale.pack(side="left", padx=5)
    eye_test_label = tk.Label(eye_test_frame, text="15%", bg=DARK_BG, fg=NEON_GREEN, font=font)
    eye_test_label.pack(side="left")
    
    def update_eye_test_label(*args):
        eye_test_label.config(text=f"{int(eye_test_var.get())}%")
    
    eye_test_var.trace("w", update_eye_test_label)
    
    # Market Randomness
    randomness_frame = tk.Frame(market_frame, bg=DARK_BG)
    randomness_frame.pack(fill="x", padx=5, pady=2)
    
    tk.Label(randomness_frame, text="Market Randomness:", bg=DARK_BG, fg="#d4d4d4", font=font).pack(side="left")
    randomness_var = tk.DoubleVar(value=15.0)
    randomness_scale = tk.Scale(
        randomness_frame,
        from_=10,
        to=30,
        orient="horizontal",
        variable=randomness_var,
        bg=DARK_BG,
        fg="#d4d4d4",
        highlightthickness=0,
        troughcolor="#000000",
        length=200
    )
    randomness_scale.pack(side="left", padx=5)
    randomness_label = tk.Label(randomness_frame, text="15%", bg=DARK_BG, fg=NEON_GREEN, font=font)
    randomness_label.pack(side="left")
    
    def update_randomness_label(*args):
        randomness_label.config(text=f"{int(randomness_var.get())}%")
    
    randomness_var.trace("w", update_randomness_label)
    
    # Hometown Discount
    hometown_frame = tk.Frame(market_frame, bg=DARK_BG)
    hometown_frame.pack(fill="x", padx=5, pady=2)
    
    hometown_var = tk.BooleanVar(value=True)
    hometown_check = tk.Checkbutton(
        hometown_frame,
        text="Hometown Discount:",
        variable=hometown_var,
        bg=DARK_BG,
        fg="#d4d4d4",
        selectcolor=DARK_BG,
        activebackground=DARK_BG,
        activeforeground=NEON_GREEN,
        font=font
    )
    hometown_check.pack(side="left")
    
    hometown_pct_var = tk.StringVar(value="10")
    hometown_pct_entry = tk.Entry(
        hometown_frame,
        textvariable=hometown_pct_var,
        width=5,
        bg="#000000",
        fg="#d4d4d4",
        font=font
    )
    hometown_pct_entry.pack(side="left", padx=5)
    tk.Label(hometown_frame, text="%", bg=DARK_BG, fg="#d4d4d4", font=font).pack(side="left")
    
    # Generation Settings Panel
    gen_frame = tk.Frame(left_panel, bg=DARK_BG, relief="ridge", bd=2)
    gen_frame.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        gen_frame,
        text="Generation Settings",
        font=(font[0], font[1] + 1, "bold"),
        bg=DARK_BG,
        fg=NEON_GREEN
    ).pack(anchor="w", padx=5, pady=(5, 2))
    
    # Number of Bidding Teams
    teams_frame = tk.Frame(gen_frame, bg=DARK_BG)
    teams_frame.pack(fill="x", padx=5, pady=2)
    
    tk.Label(teams_frame, text="Number of Bidding Teams:", bg=DARK_BG, fg="#d4d4d4", font=font).pack(side="left")
    num_teams_var = tk.StringVar(value="5")
    num_teams_combo = ttk.Combobox(
        teams_frame,
        textvariable=num_teams_var,
        values=["1", "2", "3", "4", "5", "6", "7", "8"],
        state="readonly",
        width=5
    )
    num_teams_combo.pack(side="left", padx=5)
    
    # Team Archetypes
    archetypes_label = tk.Label(
        gen_frame,
        text="Team Archetypes:",
        bg=DARK_BG,
        fg="#d4d4d4",
        font=font
    )
    archetypes_label.pack(anchor="w", padx=5, pady=(5, 2))
    
    archetype_vars = {}
    archetype_checks_frame = tk.Frame(gen_frame, bg=DARK_BG)
    archetype_checks_frame.pack(fill="x", padx=10, pady=2)
    
    for archetype in TeamArchetype:
        var = tk.BooleanVar(value=True)
        archetype_vars[archetype] = var
        check = tk.Checkbutton(
            archetype_checks_frame,
            text=archetype.value.title(),
            variable=var,
            bg=DARK_BG,
            fg="#d4d4d4",
            selectcolor=DARK_BG,
            activebackground=DARK_BG,
            activeforeground=NEON_GREEN,
            font=font
        )
        check.pack(anchor="w")
    
    # International Mode
    international_var = tk.BooleanVar(value=False)
    international_check = tk.Checkbutton(
        gen_frame,
        text="International Mode (manual WAR input)",
        variable=international_var,
        bg=DARK_BG,
        fg="#d4d4d4",
        selectcolor=DARK_BG,
        activebackground=DARK_BG,
        activeforeground=NEON_GREEN,
        font=font
    )
    international_check.pack(anchor="w", padx=5, pady=5)
    
    # International WAR input (hidden by default)
    intl_war_frame = tk.Frame(gen_frame, bg=DARK_BG)
    
    tk.Label(intl_war_frame, text="Projected WAR:", bg=DARK_BG, fg="#d4d4d4", font=font).pack(side="left", padx=5)
    intl_war_var = tk.StringVar(value="2.0")
    intl_war_entry = tk.Entry(
        intl_war_frame,
        textvariable=intl_war_var,
        width=8,
        bg="#000000",
        fg="#d4d4d4",
        font=font
    )
    intl_war_entry.pack(side="left", padx=5)
    
    def toggle_international_mode(*args):
        """Show/hide international WAR input"""
        if international_var.get():
            intl_war_frame.pack(fill="x", padx=10, pady=2)
        else:
            intl_war_frame.pack_forget()
    
    international_var.trace("w", toggle_international_mode)
    
    # ==================================================
    # RIGHT SIDE: Selected Player Info & Generated Contracts
    # ==================================================
    right_panel = tk.Frame(main_container, bg=DARK_BG, relief="ridge", bd=2)
    right_panel.pack(side="right", fill="both", expand=True)
    
    # Selected Player Info
    player_info_frame = tk.Frame(right_panel, bg=DARK_BG, relief="ridge", bd=2)
    player_info_frame.pack(fill="x", padx=5, pady=5)
    
    tk.Label(
        player_info_frame,
        text="Selected Player",
        font=(font[0], font[1] + 1, "bold"),
        bg=DARK_BG,
        fg=NEON_GREEN
    ).pack(anchor="w", padx=5, pady=(5, 2))
    
    player_info_label = tk.Label(
        player_info_frame,
        text="Select a free agent from the list",
        font=font,
        bg=DARK_BG,
        fg="#d4d4d4",
        justify="left",
        anchor="w"
    )
    player_info_label.pack(fill="x", padx=10, pady=5)
    
    def update_selected_player_info():
        """Update the selected player info display"""
        if not selected_free_agent[0]:
            player_info_label.config(text="Select a free agent from the list")
            return
        
        player = selected_free_agent[0]
        name = player.get("Name", "Unknown")
        age = player.get("Age", "?")
        pos = player.get("POS", "?")
        
        player_type = "pitcher" if pos.upper() in ["SP", "RP", "CL", "P"] else "batter"
        if player_type == "pitcher":
            war = player.get("WAR (Pitcher)", player.get("WAR", "-"))
            stat_plus = player.get("ERA+", "-")
            stat_name = "ERA+"
        else:
            war = player.get("WAR (Batter)", player.get("WAR", "-"))
            stat_plus = player.get("wRC+", "-")
            stat_name = "wRC+"
        
        ovr = player.get("OVR", "-")
        
        info_text = (
            f"{name} - {pos}, Age {age}\n"
            f"WAR: {war} | {stat_name}: {stat_plus} | OVR: {ovr}"
        )
        
        player_info_label.config(text=info_text)
    
    # Generated Contracts Panel
    contracts_frame = tk.Frame(right_panel, bg=DARK_BG)
    contracts_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    tk.Label(
        contracts_frame,
        text="Generated Contract Offers",
        font=(font[0], font[1] + 1, "bold"),
        bg=DARK_BG,
        fg=NEON_GREEN
    ).pack(anchor="w", padx=5, pady=(5, 2))
    
    # Contracts Treeview
    contracts_tree_frame = tk.Frame(contracts_frame, bg=DARK_BG)
    contracts_tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    contracts_vsb = ttk.Scrollbar(contracts_tree_frame, orient="vertical")
    contracts_vsb.pack(side="right", fill="y")
    
    contracts_hsb = ttk.Scrollbar(contracts_tree_frame, orient="horizontal")
    contracts_hsb.pack(side="bottom", fill="x")
    
    contracts_cols = ("Team", "Years", "AAV", "Total Value", "Notes")
    contracts_tree = ttk.Treeview(
        contracts_tree_frame,
        columns=contracts_cols,
        show="headings",
        yscrollcommand=contracts_vsb.set,
        xscrollcommand=contracts_hsb.set,
        height=15
    )
    contracts_tree.pack(side="left", fill="both", expand=True)
    contracts_vsb.config(command=contracts_tree.yview)
    contracts_hsb.config(command=contracts_tree.xview)
    
    # Configure columns
    contracts_tree.heading("Team", text="Team Archetype")
    contracts_tree.heading("Years", text="Years")
    contracts_tree.heading("AAV", text="AAV (millions)")
    contracts_tree.heading("Total Value", text="Total Value")
    contracts_tree.heading("Notes", text="Notes")
    
    contracts_tree.column("Team", width=120, minwidth=100)
    contracts_tree.column("Years", width=60, minwidth=50, anchor="center")
    contracts_tree.column("AAV", width=100, minwidth=80, anchor="center")
    contracts_tree.column("Total Value", width=100, minwidth=80, anchor="center")
    contracts_tree.column("Notes", width=200, minwidth=150)
    
    contracts_tree.tag_configure("hover", background="#333")
    contracts_tree.tag_configure("hometown", foreground="#ffd700")  # Gold color for hometown
    contracts_tree._prev_hover = None
    contracts_tree.bind("<Motion>", on_treeview_motion)
    contracts_tree.bind("<Leave>", on_leave)
    
    def generate_contracts():
        """Generate contract offers for the selected player"""
        contracts_tree.delete(*contracts_tree.get_children())
        
        if not selected_free_agent[0]:
            return
        
        player = selected_free_agent[0]
        
        # Get settings
        try:
            dollar_per_war = float(dollar_per_war_var.get())
        except ValueError:
            dollar_per_war = 8.0
        
        eye_test_weight = eye_test_var.get() / 100.0
        market_randomness = randomness_var.get() / 100.0
        
        try:
            hometown_discount_pct = float(hometown_pct_var.get()) / 100.0
        except ValueError:
            hometown_discount_pct = 0.10
        
        try:
            num_bidding_teams = int(num_teams_var.get())
        except ValueError:
            num_bidding_teams = 5
        
        # Get selected archetypes
        selected_archetypes = [
            archetype for archetype, var in archetype_vars.items()
            if var.get()
        ]
        
        if not selected_archetypes:
            messagebox.showwarning(
                "No Archetypes",
                "Please select at least one team archetype to generate offers."
            )
            return
        
        # Parse player
        is_international = international_var.get()
        projected_war = None
        if is_international:
            try:
                projected_war = float(intl_war_var.get())
            except ValueError:
                projected_war = 2.0
        
        player_input = parse_player_from_dict(
            player,
            is_international=is_international,
            projected_war=projected_war
        )
        
        # Generate offers
        offers = generate_contract_offers(
            player_input=player_input,
            dollar_per_war=dollar_per_war,
            eye_test_weight=eye_test_weight,
            market_randomness=market_randomness,
            hometown_discount_pct=hometown_discount_pct if hometown_var.get() else 0.0,
            num_bidding_teams=num_bidding_teams,
            team_archetypes=selected_archetypes
        )
        
        # Display offers
        for offer in offers:
            team_name = offer.team_archetype.value.title()
            if offer.hometown_discount:
                team_name = "🏠 " + team_name + " (Hometown)"
            
            aav_str = f"${offer.aav:.2f}M"
            total_str = f"${offer.total_value:.2f}M"
            
            tags = ()
            if offer.hometown_discount:
                tags = ("hometown",)
            
            contracts_tree.insert(
                "",
                "end",
                values=(team_name, offer.years, aav_str, total_str, offer.notes),
                tags=tags
            )
    
    # Generate button
    generate_btn = ttk.Button(
        gen_frame,
        text="Generate Contracts",
        command=generate_contracts
    )
    generate_btn.pack(fill="x", padx=5, pady=10)
    
    # Auto-calculate $/WAR button
    def calculate_market_rate():
        """Calculate $/WAR from loaded Player List data"""
        if not all_players:
            messagebox.showinfo(
                "No Data",
                "Player List data is not loaded.\n\n"
                "The $/WAR baseline will be calculated automatically when you reload Player List.html"
            )
            return
        
        rate = calculate_market_dollar_per_war(all_players)
        market_dollar_per_war[0] = rate
        dollar_per_war_var.set(f"{rate:.2f}")
        
        messagebox.showinfo(
            "Market Rate Calculated",
            f"Calculated $/WAR baseline: ${rate:.2f}M\n\n"
            f"Based on {len(all_players)} players in Player List.html"
        )
    
    calc_market_btn = ttk.Button(
        market_frame,
        text="Auto-Calculate from Player List",
        command=calculate_market_rate
    )
    calc_market_btn.pack(fill="x", padx=5, pady=5)
    
    # Tab refresh class
    class AutoContractTab:
        def refresh(self, pitchers, batters):
            """Refresh with new player data"""
            all_players.clear()
            all_players.extend(pitchers)
            all_players.extend(batters)
            
            # Auto-calculate market rate
            if all_players:
                rate = calculate_market_dollar_per_war(all_players)
                market_dollar_per_war[0] = rate
                dollar_per_war_var.set(f"{rate:.2f}")
    
    return AutoContractTab()
