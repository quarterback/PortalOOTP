# Hidden Gems Tab
# UI for finding overlooked players who deserve a second look

import tkinter as tk
from tkinter import ttk
from .style import on_treeview_motion, on_leave, sort_treeview
from .widgets import make_treeview_open_link_handler, load_player_url_template
from hidden_gems import find_all_hidden_gems, HIDDEN_GEM_CATEGORIES, get_hidden_gems_summary

player_url_template = load_player_url_template()


def add_hidden_gems_tab(notebook, font):
    hidden_gems_frame = ttk.Frame(notebook)
    notebook.add(hidden_gems_frame, text="Hidden Gems")
    
    # Data storage
    all_pitchers = []
    all_batters = []
    current_category = {"value": "all"}
    hidden_gems_data = {}
    
    # Header
    header_frame = tk.Frame(hidden_gems_frame, bg="#1e1e1e")
    header_frame.pack(fill="x", padx=10, pady=5)
    
    tk.Label(
        header_frame,
        text="💎 Hidden Gems Finder",
        font=(font[0], font[1] + 4, "bold"),
        bg="#1e1e1e",
        fg="#00ff7f"
    ).pack(side="left")
    
    tk.Label(
        header_frame,
        text="Find overlooked players across the league",
        font=(font[0], font[1] - 1),
        bg="#1e1e1e",
        fg="#888888"
    ).pack(side="left", padx=(20, 0))
    
    # Category filter frame
    filter_frame = tk.Frame(hidden_gems_frame, bg="#1e1e1e")
    filter_frame.pack(fill="x", padx=10, pady=5)
    
    tk.Label(filter_frame, text="Category:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left")
    
    category_var = tk.StringVar(value="all")
    category_options = ["All Categories"]
    category_map = {"All Categories": "all"}
    
    for key, info in HIDDEN_GEM_CATEGORIES.items():
        label = f"{info['icon']} {info['name']}"
        category_options.append(label)
        category_map[label] = key
    
    category_combo = ttk.Combobox(
        filter_frame,
        textvariable=category_var,
        values=category_options,
        state="readonly",
        width=25
    )
    category_combo.set("All Categories")
    category_combo.pack(side="left", padx=5)
    
    # Position filter
    tk.Label(filter_frame, text="Position:", bg="#1e1e1e", fg="#d4d4d4", font=font).pack(side="left", padx=(15, 0))
    pos_var = tk.StringVar(value="All")
    pos_combo = ttk.Combobox(
        filter_frame,
        textvariable=pos_var,
        values=["All", "SP", "RP", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"],
        state="readonly",
        width=8
    )
    pos_combo.pack(side="left", padx=5)
    
    # Summary label
    summary_var = tk.StringVar(value="")
    summary_label = tk.Label(
        filter_frame,
        textvariable=summary_var,
        font=font,
        bg="#1e1e1e",
        fg="#888888"
    )
    summary_label.pack(side="right", padx=10)
    
    # Main container with category cards and table
    main_container = tk.Frame(hidden_gems_frame, bg="#1e1e1e")
    main_container.pack(fill="both", expand=True, padx=10, pady=5)
    
    # Left side - Category summary cards
    cards_frame = tk.Frame(main_container, bg="#1e1e1e", width=200)
    cards_frame.pack(side="left", fill="y", padx=(0, 10))
    cards_frame.pack_propagate(False)
    
    tk.Label(
        cards_frame,
        text="Categories",
        font=(font[0], font[1] + 1, "bold"),
        bg="#1e1e1e",
        fg="#d4d4d4"
    ).pack(fill="x", pady=(0, 10))
    
    # Category cards will be populated dynamically
    card_labels = {}
    
    def create_category_cards():
        """Create category summary cards"""
        # Clear existing cards
        for widget in cards_frame.winfo_children():
            if widget.cget("text") != "Categories":
                widget.destroy()
        
        summary = get_hidden_gems_summary(hidden_gems_data)
        
        for key, info in HIDDEN_GEM_CATEGORIES.items():
            count = summary.get(key, {}).get("count", 0)
            
            card = tk.Frame(cards_frame, bg="#2a2a2a", relief="raised", bd=1)
            card.pack(fill="x", pady=3)
            
            # Header with icon and name
            header = tk.Frame(card, bg="#2a2a2a")
            header.pack(fill="x", padx=5, pady=3)
            
            tk.Label(
                header,
                text=f"{info['icon']} {info['name']}",
                font=(font[0], font[1], "bold"),
                bg="#2a2a2a",
                fg=info["color"]
            ).pack(side="left")
            
            tk.Label(
                header,
                text=f"({count})",
                font=font,
                bg="#2a2a2a",
                fg="#888888"
            ).pack(side="right")
            
            # Description
            tk.Label(
                card,
                text=info["description"],
                font=(font[0], font[1] - 2),
                bg="#2a2a2a",
                fg="#888888",
                wraplength=180,
                justify="left"
            ).pack(fill="x", padx=5, pady=(0, 5))
            
            # Make card clickable
            def on_card_click(event, cat_key=key):
                for label in category_options:
                    if category_map.get(label) == cat_key:
                        category_combo.set(label)
                        break
                update_table()
            
            card.bind("<Button-1>", on_card_click)
            for child in card.winfo_children():
                child.bind("<Button-1>", on_card_click)
                for grandchild in child.winfo_children():
                    grandchild.bind("<Button-1>", on_card_click)
    
    # Right side - Results table
    table_container = tk.Frame(main_container, bg="#1e1e1e")
    table_container.pack(side="right", fill="both", expand=True)
    
    # Table
    table_frame = tk.Frame(table_container, bg="#1e1e1e")
    table_frame.pack(fill="both", expand=True)
    
    vsb = ttk.Scrollbar(table_frame, orient="vertical")
    vsb.pack(side="right", fill="y")
    
    hsb = ttk.Scrollbar(table_frame, orient="horizontal")
    hsb.pack(side="bottom", fill="x")
    
    cols = ("Category", "Name", "Team", "POS", "Age", "OVR", "POT", "Key Stats", "Why Hidden", "Upside")
    table = ttk.Treeview(
        table_frame,
        columns=cols,
        show="headings",
        yscrollcommand=vsb.set,
        xscrollcommand=hsb.set,
        height=20
    )
    table.pack(side="left", fill="both", expand=True)
    
    vsb.config(command=table.yview)
    hsb.config(command=table.xview)
    
    col_widths = {
        "Category": 120, "Name": 140, "Team": 55, "POS": 45, "Age": 40,
        "OVR": 50, "POT": 50, "Key Stats": 140, "Why Hidden": 150, "Upside": 160
    }
    
    for col in cols:
        table.heading(col, text=col, command=lambda c=col: sort_treeview(table, c, False))
        table.column(col, width=col_widths.get(col, 100), minwidth=40, anchor="center", stretch=True)
    
    # Configure tags for different categories
    for key, info in HIDDEN_GEM_CATEGORIES.items():
        table.tag_configure(key, foreground=info["color"])
    
    table.tag_configure("hover", background="#333")
    table._prev_hover = None
    table.bind("<Motion>", on_treeview_motion)
    table.bind("<Leave>", on_leave)
    
    id_map = {}
    
    def update_table():
        """Update the results table based on filters"""
        table.delete(*table.get_children())
        id_map.clear()
        
        selected_label = category_combo.get()
        selected_category = category_map.get(selected_label, "all")
        pos_filter = pos_var.get()
        
        # Gather results
        results = []
        
        if selected_category == "all":
            # Show all categories
            for cat_key, players in hidden_gems_data.items():
                for player_info in players:
                    results.append((cat_key, player_info))
        else:
            # Show specific category
            players = hidden_gems_data.get(selected_category, [])
            for player_info in players:
                results.append((selected_category, player_info))
        
        # Apply position filter
        if pos_filter != "All":
            results = [(cat, p) for cat, p in results if p.get("pos") == pos_filter]
        
        # Populate table
        for cat_key, player_info in results:
            cat_info = HIDDEN_GEM_CATEGORIES.get(cat_key, {})
            category_display = f"{cat_info.get('icon', '')} {cat_info.get('name', cat_key)}"
            
            values = (
                category_display,
                player_info.get("name", ""),
                player_info.get("team", ""),
                player_info.get("pos", ""),
                player_info.get("age", ""),
                f"{player_info.get('ovr', 0):.1f}",
                f"{player_info.get('pot', 0):.1f}",
                player_info.get("key_stat", ""),
                player_info.get("why_hidden", ""),
                player_info.get("upside", "")
            )
            
            iid = table.insert("", "end", values=values, tags=(cat_key,))
            player = player_info.get("player", {})
            player_id = player.get("ID", "")
            if player_id:
                id_map[iid] = player_id
        
        # Update summary
        summary_var.set(f"Found {len(results)} hidden gems")
        
        make_treeview_open_link_handler(table, id_map, lambda pid: player_url_template.format(pid=pid))
    
    def refresh_data():
        """Refresh hidden gems data from player lists"""
        nonlocal hidden_gems_data
        hidden_gems_data = find_all_hidden_gems(all_batters, all_pitchers)
        create_category_cards()
        update_table()
    
    # Bind filter changes
    category_combo.bind("<<ComboboxSelected>>", lambda e: update_table())
    pos_combo.bind("<<ComboboxSelected>>", lambda e: update_table())
    
    class HiddenGemsTab:
        def refresh(self, pitchers, batters):
            all_pitchers.clear()
            all_batters.clear()
            all_pitchers.extend(pitchers)
            all_batters.extend(batters)
            refresh_data()
    
    return HiddenGemsTab()
