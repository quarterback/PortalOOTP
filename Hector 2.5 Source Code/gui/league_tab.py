# League Analytics Tab
# UI for displaying league-wide analysis and insights

import tkinter as tk
from tkinter import ttk
from .style import on_treeview_motion, on_leave, sort_treeview


def add_league_tab(notebook, font):
    """
    Add League Analysis tab to the notebook.
    
    Args:
        notebook: ttk.Notebook to add tab to
        font: Font tuple for styling
    
    Returns:
        LeagueTab object with refresh() method
    """
    league_frame = ttk.Frame(notebook)
    notebook.add(league_frame, text="League Analysis")
    
    # Data storage
    league_report = {"value": {}}
    
    # Create scrollable canvas
    canvas = tk.Canvas(league_frame, bg="#2d2d2d", highlightthickness=0)
    scrollbar = ttk.Scrollbar(league_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg="#2d2d2d")
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Bind mousewheel
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    # Header
    header_frame = tk.Frame(scrollable_frame, bg="#2d2d2d")
    header_frame.pack(fill="x", padx=20, pady=(15, 10))
    
    tk.Label(
        header_frame,
        text="🏆 League Analytics",
        font=(font[0], font[1] + 6, "bold"),
        bg="#2d2d2d",
        fg="#00bfff"
    ).pack(side="left")
    
    tk.Label(
        header_frame,
        text="Comprehensive league-wide insights and competitive balance analysis",
        font=(font[0], font[1]),
        bg="#2d2d2d",
        fg="#888888"
    ).pack(side="left", padx=(20, 0))
    
    # Summary Insights Section
    insights_frame = tk.LabelFrame(
        scrollable_frame,
        text="📊 Key Insights",
        font=(font[0], font[1] + 1, "bold"),
        bg="#2d2d2d",
        fg="#00ff7f",
        relief="raised",
        bd=2
    )
    insights_frame.pack(fill="x", padx=20, pady=10)
    
    insights_text = tk.Text(
        insights_frame,
        height=6,
        font=font,
        bg="#1e1e1e",
        fg="#d4d4d4",
        relief="flat",
        wrap="word",
        state="disabled"
    )
    insights_text.pack(fill="x", padx=10, pady=10)
    
    # Season Summary Card
    summary_frame = tk.LabelFrame(
        scrollable_frame,
        text="📈 Season Summary",
        font=(font[0], font[1] + 1, "bold"),
        bg="#2d2d2d",
        fg="#00bfff",
        relief="raised",
        bd=2
    )
    summary_frame.pack(fill="x", padx=20, pady=10)
    
    summary_labels = {}
    summary_grid = tk.Frame(summary_frame, bg="#2d2d2d")
    summary_grid.pack(fill="x", padx=10, pady=10)
    
    # Parity Index Section
    parity_frame = tk.LabelFrame(
        scrollable_frame,
        text="⚖️ Competitive Balance",
        font=(font[0], font[1] + 1, "bold"),
        bg="#2d2d2d",
        fg="#ffd700",
        relief="raised",
        bd=2
    )
    parity_frame.pack(fill="x", padx=20, pady=10)
    
    parity_text = tk.Text(
        parity_frame,
        height=8,
        font=font,
        bg="#1e1e1e",
        fg="#d4d4d4",
        relief="flat",
        wrap="word",
        state="disabled"
    )
    parity_text.pack(fill="both", padx=10, pady=10)
    
    # Park Factors Section
    parks_frame = tk.LabelFrame(
        scrollable_frame,
        text="🏟️ Park Factors",
        font=(font[0], font[1] + 1, "bold"),
        bg="#2d2d2d",
        fg="#ff8c00",
        relief="raised",
        bd=2
    )
    parks_frame.pack(fill="x", padx=20, pady=10)
    
    # Parks table
    parks_table_frame = tk.Frame(parks_frame, bg="#2d2d2d")
    parks_table_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    parks_vsb = ttk.Scrollbar(parks_table_frame, orient="vertical")
    parks_vsb.pack(side="right", fill="y")
    
    parks_cols = ("Team", "Park", "PF", "PF HR", "PF AVG", "Type")
    parks_table = ttk.Treeview(
        parks_table_frame,
        columns=parks_cols,
        show="headings",
        height=8,
        yscrollcommand=parks_vsb.set
    )
    parks_vsb.config(command=parks_table.yview)
    
    for col in parks_cols:
        parks_table.heading(col, text=col, command=lambda c=col: sort_treeview(parks_table, c, False))
        if col == "Park":
            parks_table.column(col, width=180, anchor="w")
        elif col == "Team":
            parks_table.column(col, width=60, anchor="center")
        elif col == "Type":
            parks_table.column(col, width=120, anchor="w")
        else:
            parks_table.column(col, width=80, anchor="center")
    
    parks_table.pack(side="left", fill="both", expand=True)
    parks_table.tag_configure("extreme", background="#4a1515")
    parks_table.tag_configure("hover", background="#333")
    
    parks_table._prev_hover = None
    parks_table.bind("<Motion>", on_treeview_motion)
    parks_table.bind("<Leave>", on_leave)
    
    # Talent Distribution Section
    talent_frame = tk.LabelFrame(
        scrollable_frame,
        text="🌟 Talent Distribution",
        font=(font[0], font[1] + 1, "bold"),
        bg="#2d2d2d",
        fg="#9370db",
        relief="raised",
        bd=2
    )
    talent_frame.pack(fill="x", padx=20, pady=10)
    
    # Talent table
    talent_table_frame = tk.Frame(talent_frame, bg="#2d2d2d")
    talent_table_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    talent_vsb = ttk.Scrollbar(talent_table_frame, orient="vertical")
    talent_vsb.pack(side="right", fill="y")
    
    talent_cols = ("Rank", "Team", "Batting WAR", "Pitching WAR", "Total WAR")
    talent_table = ttk.Treeview(
        talent_table_frame,
        columns=talent_cols,
        show="headings",
        height=10,
        yscrollcommand=talent_vsb.set
    )
    talent_vsb.config(command=talent_table.yview)
    
    for col in talent_cols:
        talent_table.heading(col, text=col, command=lambda c=col: sort_treeview(talent_table, c, False))
        if col == "Rank":
            talent_table.column(col, width=50, anchor="center")
        elif col == "Team":
            talent_table.column(col, width=200, anchor="w")
        else:
            talent_table.column(col, width=120, anchor="center")
    
    talent_table.pack(side="left", fill="both", expand=True)
    talent_table.tag_configure("super_team", background="#1a3a1a")
    talent_table.tag_configure("hover", background="#333")
    
    talent_table._prev_hover = None
    talent_table.bind("<Motion>", on_treeview_motion)
    talent_table.bind("<Leave>", on_leave)
    
    # Division Breakdown Section
    division_frame = tk.LabelFrame(
        scrollable_frame,
        text="🏆 Division Breakdown",
        font=(font[0], font[1] + 1, "bold"),
        bg="#2d2d2d",
        fg="#00ced1",
        relief="raised",
        bd=2
    )
    division_frame.pack(fill="x", padx=20, pady=10)
    
    division_text = tk.Text(
        division_frame,
        height=10,
        font=font,
        bg="#1e1e1e",
        fg="#d4d4d4",
        relief="flat",
        wrap="word",
        state="disabled"
    )
    division_text.pack(fill="both", padx=10, pady=10)
    
    # Year-over-Year Section
    yoy_frame = tk.LabelFrame(
        scrollable_frame,
        text="📅 Year-over-Year Trends",
        font=(font[0], font[1] + 1, "bold"),
        bg="#2d2d2d",
        fg="#ff6b6b",
        relief="raised",
        bd=2
    )
    yoy_frame.pack(fill="x", padx=20, pady=(10, 20))
    
    # YoY table
    yoy_table_frame = tk.Frame(yoy_frame, bg="#2d2d2d")
    yoy_table_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    yoy_vsb = ttk.Scrollbar(yoy_table_frame, orient="vertical")
    yoy_vsb.pack(side="right", fill="y")
    
    yoy_cols = ("Team", "Current W%", "Last Year W%", "Change", "Wins +/-")
    yoy_table = ttk.Treeview(
        yoy_table_frame,
        columns=yoy_cols,
        show="headings",
        height=10,
        yscrollcommand=yoy_vsb.set
    )
    yoy_vsb.config(command=yoy_table.yview)
    
    for col in yoy_cols:
        yoy_table.heading(col, text=col, command=lambda c=col: sort_treeview(yoy_table, c, False))
        if col == "Team":
            yoy_table.column(col, width=200, anchor="w")
        else:
            yoy_table.column(col, width=100, anchor="center")
    
    yoy_table.pack(side="left", fill="both", expand=True)
    yoy_table.tag_configure("improver", foreground="#00ff7f")
    yoy_table.tag_configure("decliner", foreground="#ff6b6b")
    yoy_table.tag_configure("hover", background="#333")
    
    yoy_table._prev_hover = None
    yoy_table.bind("<Motion>", on_treeview_motion)
    yoy_table.bind("<Leave>", on_leave)
    
    def update_display():
        """Update all display sections with current report data"""
        report = league_report["value"]
        
        if not report or report.get("error"):
            # Show error or empty state
            insights_text.config(state="normal")
            insights_text.delete("1.0", "end")
            insights_text.insert("1.0", "No team data available. Please ensure Team List.html is loaded.")
            insights_text.config(state="disabled")
            return
        
        # Update insights
        insights_text.config(state="normal")
        insights_text.delete("1.0", "end")
        for insight in report.get("summary_insights", []):
            insights_text.insert("end", f"  • {insight}\n")
        insights_text.config(state="disabled")
        
        # Update season summary
        for widget in summary_grid.winfo_children():
            widget.destroy()
        
        env = report.get("environment", {})
        parity = report.get("parity", {})
        
        row = 0
        col = 0
        summary_items = [
            ("Environment Type", env.get("environment_type", "N/A").replace("_", " ").title()),
            ("Total Teams", env.get("total_teams", 0)),
            ("Overall Parity", parity.get("overall_parity", "N/A").title()),
            ("Win % Std Dev", f"{parity.get('win_pct_std', 0):.3f}"),
            ("Avg Park Factor", f"{env.get('park_factors', {}).get('PF_mean', 1.0):.3f}"),
            ("Avg Batting WAR", f"{env.get('batting_war', {}).get('mean', 0):.1f}"),
            ("Avg Pitching WAR", f"{env.get('pitching_war', {}).get('mean', 0):.1f}"),
        ]
        
        for label_text, value_text in summary_items:
            label = tk.Label(
                summary_grid,
                text=f"{label_text}:",
                font=(font[0], font[1], "bold"),
                bg="#2d2d2d",
                fg="#888888",
                anchor="e"
            )
            label.grid(row=row, column=col*2, sticky="e", padx=(10, 5), pady=3)
            
            value = tk.Label(
                summary_grid,
                text=str(value_text),
                font=font,
                bg="#2d2d2d",
                fg="#00bfff",
                anchor="w"
            )
            value.grid(row=row, column=col*2+1, sticky="w", padx=(0, 20), pady=3)
            
            row += 1
            if row >= 4:
                row = 0
                col += 1
        
        # Update parity details
        parity_text.config(state="normal")
        parity_text.delete("1.0", "end")
        
        near_500 = parity.get("teams_near_500", {})
        parity_text.insert("end", f"Teams near .500:\n")
        parity_text.insert("end", f"  Within 5 games: {near_500.get('within_5_games', 0)} teams\n")
        parity_text.insert("end", f"  Within 10 games: {near_500.get('within_10_games', 0)} teams\n\n")
        
        parity_text.insert("end", "Division Competitive Balance:\n")
        for div_name, div_data in parity.get("division_balance", {}).items():
            status = div_data.get("status", "").replace("_", " ").title()
            parity_text.insert("end", f"  {div_name}: {status}\n")
            parity_text.insert("end", f"    W% Range: {div_data.get('min_pct', 0):.3f} - {div_data.get('max_pct', 0):.3f}\n")
            parity_text.insert("end", f"    Spread: {div_data.get('spread', 0):.3f}\n")
        
        parity_text.config(state="disabled")
        
        # Update parks table
        parks_table.delete(*parks_table.get_children())
        
        park_data = report.get("park_factors", {})
        extreme_parks = park_data.get("extreme_parks", [])
        
        for park in extreme_parks:
            park_type = park.get("type", "").replace("_", " ").title()
            tag = "extreme" if park.get("severity") == "extreme" else ""
            
            parks_table.insert("", "end", values=(
                park.get("team", ""),
                park.get("park", ""),
                f"{park.get('PF', 1.0):.3f}",
                f"{park.get('PF HR', 1.0):.3f}",
                f"{park.get('PF AVG', 1.0):.3f}",
                park_type
            ), tags=(tag,))
        
        # Update talent table
        talent_table.delete(*talent_table.get_children())
        
        talent_data = report.get("talent_distribution", {})
        super_teams = {t["team"] for t in talent_data.get("super_teams", [])}
        
        for rank, team in enumerate(talent_data.get("top_teams", []), 1):
            tag = "super_team" if team["team"] in super_teams else ""
            
            talent_table.insert("", "end", values=(
                rank,
                team.get("team_name", ""),
                f"{team.get('batting_war', 0):.1f}",
                f"{team.get('pitching_war', 0):.1f}",
                f"{team.get('total_war', 0):.1f}"
            ), tags=(tag,))
        
        # Update division breakdown
        division_text.config(state="normal")
        division_text.delete("1.0", "end")
        
        for div_name, div_data in talent_data.get("division_talent", {}).items():
            division_text.insert("end", f"{div_name}:\n")
            division_text.insert("end", f"  Teams: {div_data.get('teams', 0)}\n")
            division_text.insert("end", f"  Average WAR: {div_data.get('avg_war', 0):.1f}\n")
            division_text.insert("end", f"  Total WAR: {div_data.get('total_war', 0):.1f}\n")
            division_text.insert("end", f"  Leader: {div_data.get('top_team', '')} ({div_data.get('top_team_war', 0):.1f} WAR)\n\n")
        
        division_text.config(state="disabled")
        
        # Update year-over-year table
        yoy_table.delete(*yoy_table.get_children())
        
        yoy_data = report.get("year_over_year", {})
        improvers = yoy_data.get("biggest_improvers", [])
        decliners = yoy_data.get("biggest_decliners", [])
        
        # Combine and sort by absolute change
        all_changes = improvers + decliners
        all_changes.sort(key=lambda x: abs(x.get("pct_change", 0)), reverse=True)
        
        for team in all_changes[:20]:  # Show top 20
            tag = "improver" if team.get("pct_change", 0) > 0 else "decliner"
            
            yoy_table.insert("", "end", values=(
                team.get("team_name", ""),
                f"{team.get('current_pct', 0):.3f}",
                f"{team.get('ly_pct', 0):.3f}",
                f"{team.get('pct_change', 0):+.3f}",
                f"{team.get('wins_change', 0):+.0f}"
            ), tags=(tag,))
    
    class LeagueTab:
        def refresh(self, teams_list, league_analytics_report):
            """
            Refresh the league tab with new data.
            
            Args:
                teams_list: List of team dicts (not used directly, kept for consistency)
                league_analytics_report: Dict with league analysis data
            """
            league_report["value"] = league_analytics_report or {}
            update_display()
    
    return LeagueTab()
