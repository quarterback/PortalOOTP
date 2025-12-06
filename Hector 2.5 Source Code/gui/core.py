import tkinter as tk
import sys
import os
from tkinter import ttk, messagebox, filedialog
import importlib
import importlib.util
import threading
from pathlib import Path
from pitchers import calculate_score
from batters import calculate_batter_score
from team_parser import parse_team_html, build_teams_by_abbr
from .style import setup_theme
from .pitcher_tab import add_pitcher_tab
from .batter_tab import add_batter_tab
from .teams_tab import add_teams_tab
from .trade_tab import add_trade_tab
from .contract_tab import add_contract_tab
from .trade_finder_tab import add_trade_finder_tab
from .trade_builder_tab import add_trade_builder_tab
from .contract_value_tab import add_contract_value_tab
from .platoon_finder_tab import add_platoon_finder_tab
from .hidden_gems_tab import add_hidden_gems_tab
from .roster_builder_tab import add_roster_builder_tab
from .advanced_stats_tab import add_advanced_stats_tab
from .auto_contract_tab import add_auto_contract_tab
from percentiles import initialize_percentiles
from advanced_stats import add_advanced_stats_to_players
from .widgets import (
    create_title_label, create_summary_widgets, create_control_frame, update_summary_widgets,
    validate_fields, detect_wrong_import, show_loading_bar, set_app_icon
)
from bs4 import BeautifulSoup

REQUIRED_PITCHER_FIELDS = [
    "Name", "ORG", "POS", "Age", "T", "Prone", "SctAcc",
    "STU", "MOV", "CON", "STU P", "MOV P", "CON P",
    "PIT", "VELO", "STM", "G/F", "OVR", "POT",
    "FB", "CH", "CB", "SL", "SI", "SP", "CT", "FO", "CC", "SC", "KC", "KN",
    "FBP", "CHP", "CBP", "SLP", "SIP", "SPP", "CTP", "FOP", "CCP", "SCP", "KCP", "KNP"
]

REQUIRED_BATTER_FIELDS = [
    "Name", "ORG", "POS", "Age", "B", "Prone", "SctAcc", "OVR", "POT",
    "CON", "GAP", "POW", "EYE", "K's", "CON P", "GAP P", "POW P", "EYE P", "K P",
    "C ABI", "C ARM", "C FRM", "IF RNG", "IF ERR", "IF ARM", "TDP",
    "OF RNG", "OF ERR", "OF ARM", "SPE", "STE", "RUN",
    "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"
]



PITCHER_POSITIONS = {"P", "SP", "RP", "CL"}
BATTER_POSITIONS = {"C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"}

NEON_GREEN = "#29ff9e"
DARK_BG = "#2d2d2d"

def get_weights_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent

def import_weights_module(module_name):
    module_path = get_weights_dir() / f"{module_name}.py"
    if module_name in sys.modules:
        del sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    if spec is None or not module_path.exists():
        raise ImportError(f"Could not find spec for {module_name} at {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[module_name] = module
    return module

def reload_weights():
    global section_weights, batter_section_weights
    pitcher_weights_module = import_weights_module("pitcher_weights")
    batter_weights_module  = import_weights_module("batter_weights")
    global section_weights, batter_section_weights
    section_weights = pitcher_weights_module.section_weights
    batter_section_weights = batter_weights_module.section_weights

def parse_players_from_html(html_path):
    # Accept either a Path or string
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, "html.parser")
    table = soup.find("table", class_="data")
    if not table:
        raise ValueError(f"No table with class 'data' found in {html_path}")
    # Header row:
    thead = table.find("thead")
    if thead:
        header_row = thead.find("tr")
    else:
        header_row = table.find("tr")
    if not header_row:
        raise ValueError(f"No header row found in the table in {html_path}.")
    headers = [th.get_text(strip=True) for th in header_row.find_all("th")]
    # Handle duplicate header names by checking context
    # WAR appears twice: once for batters (after wRC+) and once for pitchers (after ERA+)
    processed_headers = []
    for i, header in enumerate(headers):
        if header == "WAR":
            # Check previous headers to determine which WAR this is
            if i > 0 and headers[i-1] == "wRC+":
                processed_headers.append("WAR (Batter)")
            elif i > 0 and headers[i-1] == "ERA+":
                processed_headers.append("WAR (Pitcher)")
            else:
                processed_headers.append(header)
        else:
            processed_headers.append(header)
    
    # Data rows:
    tbody = table.find("tbody")
    if tbody:
        rows = tbody.find_all("tr")
    else:
        rows = table.find_all("tr")[1:] # skip header row
    players = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) != len(processed_headers):
            continue  # skip junk
        player_data = {processed_headers[i]: cells[i].get_text(strip=True) for i in range(len(processed_headers))}
        players.append(player_data)
    return players

def split_players_by_type(players):
    pitchers = []
    batters = []
    for player in players:
        pos = player.get("POS", "").strip().upper()
        # Split by most comprehensive logic:
        if pos in PITCHER_POSITIONS:
            pitchers.append(player)
        elif pos in BATTER_POSITIONS:
            batters.append(player)
        # optionally, add fallback here for secondary detection by columns if needed.
    return pitchers, batters

def build_gui():
    root = tk.Tk()
    set_app_icon(root)
    root.title("Hector 2.7")
    root.geometry("1800x950")
    root.configure(bg=DARK_BG)

    font = ("Consolas", 11)
    large_font = (font[0], font[1] + 11, "bold")
    setup_theme(font, root)
    loading_frame, loading_bar = show_loading_bar(
        root, label_text="Loading data, please wait...",
        font=large_font, bar_color=NEON_GREEN, bg=DARK_BG)
    class DATA:
        pitchers = []
        batters = []
        teams_by_abbr = {}  # Team data keyed by abbreviation
        team_data_loaded = False  # Track if team data was successfully loaded

    def load_team_data():
        """
        Load team data from Team List.html.
        Returns dict mapping team abbreviation to team data, or empty dict if file not found.
        """
        team_file_path = "Team List.html"
        
        if not os.path.exists(team_file_path):
            return {}, False
        
        try:
            teams_list = parse_team_html(team_file_path)
            if teams_list:
                teams_by_abbr = build_teams_by_abbr(teams_list)
                return teams_by_abbr, True
            return {}, False
        except (ValueError, IOError, UnicodeDecodeError) as e:
            # Log specific parsing errors but continue gracefully
            print(f"Warning: Could not parse Team List.html: {e}")
            return {}, False
        except Exception as e:
            # Catch unexpected errors but don't crash the app
            print(f"Warning: Unexpected error loading team data: {e}")
            return {}, False

    def choose_and_load_file(result):
        reload_weights()
        # Use simple relative path like old working version
        # PyInstaller sets working directory to exe location, so this works
        file_path = "Player List.html"
        
        # Debug: Show file path info when compiled (temporary for diagnosis)
        if getattr(sys, 'frozen', False):
            debug_info = f"Debug Info:\n"
            debug_info += f"Working directory: {os.getcwd()}\n"
            debug_info += f"Executable: {sys.executable}\n"
            debug_info += f"File path: {file_path}\n"
            debug_info += f"File exists: {os.path.exists(file_path)}\n"
            if os.path.exists(file_path):
                debug_info += f"File size: {os.path.getsize(file_path)} bytes\n"
            # Show debug info in messagebox (comment out after testing)
            # messagebox.showinfo("Debug Info", debug_info)
        
        try:
            all_players = parse_players_from_html(file_path)
            
            # Debug: Show parsing results
            if getattr(sys, 'frozen', False):
                debug_parse = f"Parsed {len(all_players)} total players\n"
                # messagebox.showinfo("Parse Debug", debug_parse)
            
            if not all_players:
                result["exception"] = ValueError(
                    f"No player data found in 'Player List.html'.\n"
                    f"File location: {os.path.abspath(file_path) if getattr(sys, 'frozen', False) else file_path}\n"
                    f"Please check that the file contains valid player data."
                )
                return
                
            pitchers, batters = split_players_by_type(all_players)
            DATA.pitchers = pitchers
            DATA.batters = batters
            
            # Debug: Show split results
            if getattr(sys, 'frozen', False):
                debug_split = f"Split results:\nPitchers: {len(DATA.pitchers)}\nBatters: {len(DATA.batters)}\n"
                # messagebox.showinfo("Split Debug", debug_split)
            
            for pitcher in DATA.pitchers:
                pitcher['Scores'] = calculate_score(pitcher, section_weights)
            for batter in DATA.batters:
                batter['Scores'] = calculate_batter_score(batter, batter_section_weights)
            
            # Restore validation - check for missing fields but warn instead of error
            missing_pitcher_fields = validate_fields(DATA.pitchers, REQUIRED_PITCHER_FIELDS)
            missing_batter_fields = validate_fields(DATA.batters, REQUIRED_BATTER_FIELDS)
            
            # Check if we actually have any players first
            if not DATA.pitchers and not DATA.batters:
                result["exception"] = RuntimeError(
                    f"No players found in file.\n\n"
                    f"Parsed {len(all_players)} total players.\n"
                    f"Pitchers: {len(DATA.pitchers)}, Batters: {len(DATA.batters)}\n"
                    f"File: {os.path.abspath(file_path) if getattr(sys, 'frozen', False) else file_path}"
                )
                return
            
            # Warn about missing fields but don't stop execution
            if (missing_pitcher_fields or missing_batter_fields):
                warning_msg = "Warning: Some fields are missing from your export:\n\n"
                if missing_pitcher_fields:
                    warning_msg += "Pitchers missing: " + ", ".join(sorted(missing_pitcher_fields)) + "\n"
                if missing_batter_fields:
                    warning_msg += "Batters missing: " + ", ".join(sorted(missing_batter_fields)) + "\n"
                warning_msg += "\nThe app will continue, but some features may not work correctly."
                messagebox.showwarning("Field Warning", warning_msg)
            
            if detect_wrong_import(DATA.pitchers, PITCHER_POSITIONS, BATTER_POSITIONS):
                result["exception"] = RuntimeError("Could not find any pitchers in file. Is this the batter export?")
            elif detect_wrong_import(DATA.batters, BATTER_POSITIONS, PITCHER_POSITIONS):
                result["exception"] = RuntimeError("Could not find any batters in file. Is this the pitcher export?")
            else:
                result["pitchers"] = sorted(DATA.pitchers, key=lambda p: p["Scores"].get("total", 0), reverse=True)
                result["batters"] = sorted(DATA.batters, key=lambda b: b["Scores"].get("total", 0), reverse=True)
                
                # Load team data (optional - app continues if not found)
                DATA.teams_by_abbr, DATA.team_data_loaded = load_team_data()
                result["teams_by_abbr"] = DATA.teams_by_abbr
                result["team_data_loaded"] = DATA.team_data_loaded
                
                # Show warning if team data not loaded (don't crash, just reduced functionality)
                if not DATA.team_data_loaded:
                    # Queue warning to show after main thread is available
                    result["team_warning"] = (
                        "Team List.html not found or could not be loaded.\n\n"
                        "Some features will have reduced functionality:\n"
                        "- Team buyer/seller status unavailable\n"
                        "- Park factors not available for player evaluation\n\n"
                        "To enable these features, export 'Team List.html' from OOTP\n"
                        "and place it in the same folder as Player List.html."
                    )
        except Exception as e:
            # Provide more detailed error information
            error_msg = f"Error loading 'Player List.html':\n\n{str(e)}\n\n"
            error_msg += f"File path attempted: {file_path}\n"
            error_msg += f"Absolute path: {os.path.abspath(file_path)}\n"
            error_msg += f"Working directory: {os.getcwd()}\n"
            error_msg += f"File exists: {os.path.exists(file_path)}\n"
            if os.path.exists(file_path):
                error_msg += f"File size: {os.path.getsize(file_path)} bytes"
            result["exception"] = RuntimeError(error_msg)


    def finish_load_and_init(result, after_reload=False):
        loading_bar.stop()
        loading_frame.place_forget()
        loading_frame.pack_forget()
        if result.get("exception"):
            messagebox.showerror("Load Error", str(result["exception"]))
            root.destroy()
            sys.exit(1)
        
        # Show team data warning if needed (only on initial load, not reload)
        if not after_reload and result.get("team_warning"):
            messagebox.showwarning("Team Data", result["team_warning"])
        
        if not after_reload:
            # Main UI
            title = create_title_label(root, font, "Hector 2.7 - OOTP Analyzer")
            title.pack(fill="x", padx=10, pady=5)
            summary_frame, summary_left_var, summary_right_var = create_summary_widgets(root, font)
            summary_frame.pack(fill="x", padx=10)
            control_frame, reload_btn = create_control_frame(root, reload_callback=None, font=font)
            control_frame.pack(fill="x", padx=10, pady=5)
            notebook = ttk.Notebook(root)
            notebook.pack(fill="both", expand=True, padx=10, pady=10)
            pitcher_tab = add_pitcher_tab(notebook, font)
            batter_tab = add_batter_tab(notebook, font)
            teams_tab = add_teams_tab(notebook, font)
            trade_tab = add_trade_tab(notebook, font)
            contract_tab = add_contract_tab(notebook, font)
            trade_finder_tab = add_trade_finder_tab(notebook, font)
            trade_builder_tab = add_trade_builder_tab(notebook, font)
            contract_value_tab = add_contract_value_tab(notebook, font)
            platoon_finder_tab = add_platoon_finder_tab(notebook, font)
            hidden_gems_tab = add_hidden_gems_tab(notebook, font)
            roster_builder_tab = add_roster_builder_tab(notebook, font)
            advanced_stats_tab = add_advanced_stats_tab(notebook, font)
            auto_contract_tab = add_auto_contract_tab(notebook, font)
            root._gui_vars = {
                "summary_left_var": summary_left_var,
                "summary_right_var": summary_right_var,
                "pitcher_tab": pitcher_tab,
                "batter_tab": batter_tab,
                "teams_tab": teams_tab,
                "trade_tab": trade_tab,
                "contract_tab": contract_tab,
                "trade_finder_tab": trade_finder_tab,
                "trade_builder_tab": trade_builder_tab,
                "contract_value_tab": contract_value_tab,
                "platoon_finder_tab": platoon_finder_tab,
                "hidden_gems_tab": hidden_gems_tab,
                "roster_builder_tab": roster_builder_tab,
                "advanced_stats_tab": advanced_stats_tab,
                "auto_contract_tab": auto_contract_tab,
                "font": font,
                "notebook": notebook
            }
            def refresh_all_tabs():
                reload_frame, reload_bar = show_loading_bar(
                    root, label_text="Loading data, please wait...", font=large_font, bg=DARK_BG)
                result_reload = {}
                thread = threading.Thread(target=choose_and_load_file, args=(result_reload,))
                thread.start()
                def check_reload():
                    if thread.is_alive():
                        root.after(65, check_reload)
                    else:
                        reload_bar.stop()
                        reload_frame.place_forget()
                        reload_frame.destroy()
                        if result_reload.get("exception"):
                            messagebox.showerror("Data Load Error", str(result_reload["exception"]))
                        else:
                            # Initialize percentiles for the new data
                            initialize_percentiles(result_reload["batters"], result_reload["pitchers"])
                            pitcher_tab.refresh(result_reload["pitchers"])
                            batter_tab.refresh(result_reload["batters"])
                            teams_tab.refresh(result_reload["pitchers"], result_reload["batters"])
                            trade_tab.refresh(result_reload["pitchers"], result_reload["batters"])
                            contract_tab.refresh(result_reload["pitchers"], result_reload["batters"])
                            # Pass team data to trade_finder_tab
                            trade_finder_tab.refresh(
                                result_reload["pitchers"], 
                                result_reload["batters"],
                                result_reload.get("teams_by_abbr", {})
                            )
                            # Pass team data to trade_builder_tab
                            trade_builder_tab.refresh(
                                result_reload["pitchers"], 
                                result_reload["batters"],
                                result_reload.get("teams_by_abbr", {})
                            )
                            contract_value_tab.refresh(result_reload["pitchers"], result_reload["batters"])
                            platoon_finder_tab.refresh(result_reload["pitchers"], result_reload["batters"])
                            hidden_gems_tab.refresh(result_reload["pitchers"], result_reload["batters"])
                            roster_builder_tab.refresh(result_reload["pitchers"], result_reload["batters"])
                            advanced_stats_tab.refresh(result_reload["pitchers"], result_reload["batters"])
                            auto_contract_tab.refresh(result_reload["pitchers"], result_reload["batters"])
                            update_summary_widgets(DATA, summary_left_var, summary_right_var)
                check_reload()
            reload_btn.config(command=refresh_all_tabs)
            # Initialize percentiles for the initial data
            initialize_percentiles(result["batters"], result["pitchers"])
            # Show initial data
            pitcher_tab.refresh(result["pitchers"])
            batter_tab.refresh(result["batters"])
            teams_tab.refresh(result["pitchers"], result["batters"])
            trade_tab.refresh(result["pitchers"], result["batters"])
            contract_tab.refresh(result["pitchers"], result["batters"])
            # Pass team data to trade_finder_tab
            trade_finder_tab.refresh(
                result["pitchers"], 
                result["batters"],
                result.get("teams_by_abbr", {})
            )
            # Pass team data to trade_builder_tab
            trade_builder_tab.refresh(
                result["pitchers"], 
                result["batters"],
                result.get("teams_by_abbr", {})
            )
            contract_value_tab.refresh(result["pitchers"], result["batters"])
            platoon_finder_tab.refresh(result["pitchers"], result["batters"])
            hidden_gems_tab.refresh(result["pitchers"], result["batters"])
            roster_builder_tab.refresh(result["pitchers"], result["batters"])
            advanced_stats_tab.refresh(result["pitchers"], result["batters"])
            auto_contract_tab.refresh(result["pitchers"], result["batters"])
            update_summary_widgets(DATA, summary_left_var, summary_right_var)

    # Initial threaded load (while showing the loader)
    result = {}
    thread = threading.Thread(target=choose_and_load_file, args=(result,))
    thread.start()
    def check_main_load():
        if thread.is_alive():
            root.after(60, check_main_load)
        else:
            finish_load_and_init(result, after_reload=False)
    check_main_load()
    root.mainloop()
