<a name="top"></a>

# Hector OOTP Analyzer

Hector is a powerful and fully customizable desktop analytics tool for Out of the Park Baseball (OOTP) leagues. Built for both casual GMs and competitive online leagues, Hector imports your exported HTML data and delivers clear, actionable insights with a dark-mode UI. Get in-depth, sortable breakdowns for every player and team, intelligent highlights, advanced filters, and direct Stats+ integration—helping you evaluate talent, find hidden gems, and make smart roster moves.

---

## Fork Overview

This is a fork of [zab1996/HectorOOTP](https://github.com/zab1996/HectorOOTP) that adds several new features:

- **Stats-Based Evaluation**: Evaluate players based on actual performance stats (wRC+, WAR, ERA+, FIP, etc.) instead of just ratings
- **Trade Analysis Tools**: Find trade targets with the Trade Finder tab - identify expiring veterans to sell and high-upside prospects to buy
- **Mac Compatible**: Can run from source with Python on macOS (see [Running on Mac](#running-on-mac))

---

## Table of Contents

- [Fork Overview](#fork-overview)
- [Downloading the Latest Version](#downloading-the-latest-version)
- [Running on Mac](#running-on-mac)
- [Flexible Weighting System](#flexible-weighting-system)
- [Stats-Based Scoring](#stats-based-scoring)
- [Trade Finder Tab](#trade-finder-tab)
- [Age Definitions](#age-definitions)
- [Stat Columns Used](#stat-columns-used)
- [Hector Data Export Instructions](#hector-data-export-instructions)
- [Features Overview](#features-overview)
  - [Core Functionality](#core-functionality)
  - [User Interface Features](#user-interface-features)
  - [Reporting and Analysis Tools](#reporting-and-analysis-tools)
  - [Dataset Overview](#dataset-overview)
  - [User Assistance](#user-assistance)
- [Calculation Flowcharts](#calculation-flowcharts)

---

## Downloading the Latest Version

Download the newest build of Hector from the **Releases** page:

➡️ [**Download the latest version here**](../../releases)

1. Download the ZIP for the latest release.
2. Extract it to a folder of your choice.
3. Run the executable (or use Python if running from source).

<details>
<summary><strong>Showcase: Click to view screenshots of Hector in action</strong></summary>

![Showcase1](screenshots/showcase1.png)
![Showcase2](screenshots/showcase2.png)
![Showcase3](screenshots/showcase3.png)
![Showcase4](screenshots/showcase4.png)
![Showcase5](screenshots/showcase5.png)
![Showcase6](screenshots/contracttool.png)
![Showcase7](screenshots/drafttool.png)
![Showcase8](screenshots/tradetool.png)

</details>

---

## Running on Mac
[⬆️ Back to Top](#top)

Hector can run from source on macOS:

1. Clone the repository:
   ```bash
   git clone https://github.com/quarterback/HectorOOTP.git
   ```

2. Navigate to the source code directory:
   ```bash
   cd "HectorOOTP/Hector 2.4.5 Beta Source code"
   ```

3. Install dependencies:
   ```bash
   pip3 install pandas beautifulsoup4
   ```

4. Run Hector:
   ```bash
   python3 main.py
   ```

> **Note:** `tkinter` comes built-in with Python on macOS.

---

## Flexible Weighting System
[⬆️ Back to Top](#top)

**Editing Player Weights**

- `pitcher_weights.py`: Set importance of pitching attributes
- `batter_weights.py`: Set importance of hitting/defense/baserunning

How to adjust the weights:

1. Open `pitcher_weights.py` or `batter_weights.py` in a text editor (e.g., Notepad++, VS Code, or TextEdit on Mac).
2. Modify values in the `section_weights` dictionary — higher = more influence on the score.
3. Save your changes in the program folder alongside the `.exe` (or in the source directory on Mac).
4. In Hector, click the **Reload Data** button to apply changes immediately.

---

## Stats-Based Scoring
[⬆️ Back to Top](#top)

Hector includes a stats-based scoring system that evaluates players on actual performance rather than ratings.

**How to Enable:**
- Check the "Use Stats-Based Scoring" toggle in the Pitchers or Batters tab

**How It Works:**
- Calculates player value using real performance stats instead of scout ratings
- Provides a more accurate picture of current production
- Especially useful for evaluating MLB-level players with established track records

**Batter Stats Used:**
- **wRC+** (Weighted Runs Created Plus) - Primary offensive value metric (30% weight)
- **WAR** (Wins Above Replacement) - Overall value (30% weight)
- **OPS+** (OPS Plus) - Park-adjusted OPS (15% weight)
- **G** (Games) - Sample size indicator (5% weight)

**Pitcher Stats Used:**
- **WAR** (Wins Above Replacement) - Overall value (30% weight)
- **ERA+** (ERA Plus) - Park-adjusted ERA, higher is better (30% weight)
- **rWAR** (Replacement-level WAR) - (15% weight)
- **HLD** (Holds) - Reliever value indicator (5% weight, RP/CL only)
- **IP** (Innings Pitched) - Workload indicator (5% weight)

**Automatic Fallback to Ratings:**
Players with limited sample sizes automatically use ratings-only scoring:
- **Batters**: Less than 50 games → uses ratings only
- **Pitchers**: Less than 20 IP → uses ratings only

**Configuring Weights:**
- Edit `batter_stat_weights.py` for batter stat weights and thresholds
- Edit `pitcher_stat_weights.py` for pitcher stat weights and thresholds

---

## Trade Finder Tab
[⬆️ Back to Top](#top)

The Trade Finder tab helps identify trade targets and assets. It displays two panels:

### 📤 Expiring Veterans (Sell High)
Find productive veterans on expiring contracts to trade for prospects:
- **Age**: 27 or older
- **Years Left (YL)**: 1 year or less remaining
- **Production**: Currently producing (configurable minimum WAR)
- Displays wRC+ for batters, ERA+ for pitchers

### 📥 High-Upside Prospects (Buy Low)
Find young players with significant development upside:
- **Age**: 25 or under
- **Potential Gap**: POT - OVR ≥ 15 (configurable)
- Shows OVR, POT, and the gap between them

**Features:**
- Sortable tables by clicking column headers
- Position filters for both panels
- Adjustable thresholds for WAR and potential gap
- Double-click to open player's Stats+ page

---

## Age Definitions
[⬆️ Back to Top](#top)

Hector uses the following age categories for trade analysis:

| Category | Age Range | Description |
|----------|-----------|-------------|
| **Prospect** | 25 or under | Young players still developing, valued for future potential |
| **Tweener** | 26 | Players in transition, evaluate case-by-case |
| **Veteran** | 27 or older | Established players, valued primarily for current production |

---

## Stat Columns Used
[⬆️ Back to Top](#top)

Hector can ingest the following statistics from your OOTP HTML export:

### Batting Stats
| Stat | Description |
|------|-------------|
| G | Games played |
| HR | Home runs |
| RBI | Runs batted in |
| BB% | Walk percentage |
| SO% | Strikeout percentage |
| AVG | Batting average |
| OBP | On-base percentage |
| SLG | Slugging percentage |
| ISO | Isolated power |
| wOBA | Weighted on-base average |
| OPS | On-base plus slugging |
| OPS+ | Park-adjusted OPS (100 = league average) |
| BABIP | Batting average on balls in play |
| wRC+ | Weighted runs created plus (100 = league average) |
| WAR | Wins above replacement (batter) |
| SB | Stolen bases |
| UBR | Ultimate base running |

### Pitching Stats
| Stat | Description |
|------|-------------|
| W | Wins |
| SV | Saves |
| HLD | Holds |
| SD | Shutdowns |
| IP | Innings pitched |
| HR/9 | Home runs per 9 innings |
| BB/9 | Walks per 9 innings |
| K/9 | Strikeouts per 9 innings |
| pLi | Average leverage index |
| ERA+ | Park-adjusted ERA (100 = league average, higher is better) |
| FIP | Fielding independent pitching |
| FIP- | FIP minus (100 = league average, lower is better) |
| WAR | Wins above replacement (pitcher) |
| rWAR | Reference WAR |
| SIERA | Skill-interactive ERA |

### Contract/Other
| Stat | Description |
|------|-------------|
| YL | Years left on contract |
| SLR | Salary |
| SctAcc | Scout accuracy |

---

## Hector Data Export Instructions
[⬆️ Back to Top](#top)

Export player data from OOTP with custom views:

- Data Import Process
    - Create a combined view for All Players (see screenshots below)
    - Export the view as HTML
    - Replace the provided `Player List.html`.
    - Click **Reload Data** in Hector for instant refresh

### 1. Create the View in OOTP

Customize your view:

![Customizeview](screenshots/customize.png)

Include all these Data points/Attributes:

![views](screenshots/General.png)
![views](screenshots/battingratings.png)
![views](screenshots/battingstats.png)
![views](screenshots/pitcherratings.png)
![views](screenshots/pitcherstats.png)
![views](screenshots/fieldingratings.png)
![views](screenshots/scoutaccnew.png)

### 3. Save View as Global

- Save the view as **Global**
  
![views](screenshots/global.png)
- Name it as **"Hector All"** (or anything you'd like)

### 4. Export HTML File

- Export the report to disk. This will open a browser window, hit save as on the browser page and save as`Player List.html` this is the default for OOTP.

![Export HTML DATA](screenshots/export.png)
![Export HTML DATA](screenshots/save.png)

### 5. Replace The Existing File

- Overwrite the `Player List.html` file in your Hector program folder. Restart the program or hit the Reload Button to refresh the data.

![Export HTML DATA](screenshots/overwrite.png)

> Tip:
> If you see errors or warnings, check your export views and make sure all fields were included.

---

## Features Overview

### Core Functionality
[⬆️ Back to Top](#top)

- Advanced Calculations
    - Weighted scoring for both pitchers and batters, fully customizable
    - Current vs. potential talent projections
    - Comprehensive total value scores for comparison
    - **Draft Comparison Mode**: Toggle to emphasize potential (1.5x) over current performance (0.9x) for prospect evaluation

- Scouting Details
    - Injury proneness (Durability/Prone)
    - Scout accuracy confidence
    - Player handedness (throw/bat)
    - Pitcher velocity, repertoire count, ground/fly ball ratio
    - Enhanced statistical support: OPS+, wRC+, ERA+, WAR (Batter), WAR (Pitcher), rWAR, SLR, YL, CV

### User Interface Features
[⬆️ Back to Top](#top)

- Filtering & Navigation
    - Easy position-based filters (SP, RP, all batting roles)
    - Infield/Outfield group toggles for mass selection
    - Double-click player names to open their Stats+ league page (configurable via config file)
    - **Smart stat-based filtering**: OPS+, wRC+, WAR for batters; ERA+, WAR, rWAR for pitchers with age ranges

- Smart Search
    - Filter by team (`ATL` etc.), position, and age (e.g., `<30`, `>25`)
    - Chain filters (e.g., `ATL 2B <30`)

- Intelligent Highlighting
    - Flags RPs with 3+ pitches and stamina ≥50 as SP candidates
    - 1B who qualify at 3B: Range ≥50, Arm ≥55, Error ≥45
    - 2B meeting criteria for SS training: Range ≥60, Arm ≥50, Error ≥50, DP ≥50
    - Tooltips explain all highlight rules
    - Dynamic column display showing only relevant stats based on player position

### Reporting and Analysis Tools
[⬆️ Back to Top](#top)

- Quick Reports
    - Top 10 batters at each position
    - Top 20 pitchers (per SP/RP)
    - Batters with ≥50 at secondary positions can be included with one click
    - All data columns sortable ascending/descending

- Team Evaluations
    - See each team's SP/RP current & potential scores, combined pitching, offense, defense, and total rating

- **Trade Tool** (v2.3.5+)
    - Player search with autocomplete for pitchers and batters
    - Team A vs Team B comparison with value totals
    - Score normalization between pitchers and batters for fair comparison
    - Draft pick support with configurable league settings (28 teams, 20 rounds default)
    - Dynamic draft pick value calculation with exponential decay
    - Trade summary comparing total values
    - Player removal functionality

- **Contract Tool** (v2.3.5+)
    - Player selection and comparison to similar players at their position
    - Contract suggestions based on comparable salaries and values
    - Stat-based filtering with age ranges
    - Position filters with "Compare to all batters" option
    - Excludes players with 0 games (batters) or 0 innings pitched (pitchers)
    - Displays Games (G) for batters and Innings Pitched (IP) for pitchers

### Dataset Overview
[⬆️ Back to Top](#top)

- At-a-Glance Stats
    - Total and breakdown counts by role and position
    - Average scores for SP, RP, and batters
    - Visual display of positional talent spread

### User Assistance
[⬆️ Back to Top](#top)

- Hover tooltips for every calculated metric
- Click **Reload Data** to refresh at any time
- Inline help and error warnings if data is missing
- **Draft Comparison Mode tooltip** explaining prospect evaluation functionality

---

## Calculation Flowcharts
[⬆️ Back to Top](#top)

<details>
<summary><strong>Pitcher Score Calculation Flowchart</strong></summary>

![Pitcher Score Calculation Flowchart](screenshots/pitcherchart.png)

</details>

<details>
<summary><strong>Batter Score Calculation Flowchart</strong></summary>

![Batter Score Calculation Flowchart](screenshots/batterflowchart.png)

</details>

<details>
<summary><strong>Team Score Calculation Flowchart</strong></summary>

![Team Score Calculation Flowchart](screenshots/teamsflowchart.png)

</details>

---

> For issues, guidance, or detailed explanations, explore the program's tooltips or consult the full documentation.

Thank you for using Hector!
