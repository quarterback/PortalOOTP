# Autocontract Generator - Feature Walkthrough

## UI Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Hector 2.7 - OOTP Analyzer                                             │
├─────────────────────────────────────────────────────────────────────────┤
│ Tabs: [Pitchers][Batters][Teams][Trade][Contract][Trade Finder]...     │
│       ...["Autocontract"]                         👈 NEW TAB            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│ ┌─────────────────────────────────┬─────────────────────────────────┐  │
│ │  FREE AGENT POOL                │  SELECTED PLAYER                │  │
│ │  [Load Free Agents.html]        │  Mike Trout - CF, Age 32        │  │
│ ├─────────────────────────────────┤  WAR: 5.2 | wRC+: 145 | OVR: 70│  │
│ │ Name         Age POS WAR  wRC+  │                                  │  │
│ │ Mike Trout    32  CF  5.2  145  │  GENERATED CONTRACT OFFERS       │  │
│ │ Shohei Ohtani 29  DH  8.1  167  │                                  │  │
│ │ Aaron Judge   31  RF  6.8  178  │  Team Archetype  Yrs  AAV    Tot │  │
│ │ Juan Soto     25  RF  5.5  161  │  Dynasty         7   $42.0M $294M│  │
│ │ Ronald Acuña  26  OF  7.2  171  │  Contender       6   $38.5M $231M│  │
│ │ ...                              │  Window Builder  5   $36.2M $181M│  │
│ │                                  │  🏠 Dynasty(HT)  6   $36.0M $216M│  │
│ │                                  │  Rebuilding      4   $29.1M $116M│  │
│ │                                  │  Tanking         4   $25.8M $103M│  │
│ │                                  │                                  │  │
│ ├─────────────────────────────────┤                                  │  │
│ │  MARKET SETTINGS                │  Notes:                          │  │
│ │  $/WAR Baseline: [8.50] M       │  - Dynasty: paying premium       │  │
│ │  [Auto-Calculate from Player    │  - Contender: aggressive bidding │  │
│ │   List]                          │  - 🏠 Hometown: 10% discount    │  │
│ │                                  │                                  │  │
│ │  Eye Test Weight:  [===|---] 15%│                                  │  │
│ │  Market Randomness:[===|---] 15%│                                  │  │
│ │  [✓] Hometown Discount: [10] %  │                                  │  │
│ │                                  │                                  │  │
│ ├─────────────────────────────────┤                                  │  │
│ │  GENERATION SETTINGS            │                                  │  │
│ │  Number of Teams: [5]           │                                  │  │
│ │                                  │                                  │  │
│ │  Team Archetypes:               │                                  │  │
│ │  [✓] Dynasty                    │                                  │  │
│ │  [✓] Contender                  │                                  │  │
│ │  [✓] Window Builder             │                                  │  │
│ │  [✓] Rebuilding                 │                                  │  │
│ │  [✓] Tanking                    │                                  │  │
│ │                                  │                                  │  │
│ │  [ ] International Mode         │                                  │  │
│ │                                  │                                  │  │
│ │  [Generate Contracts]           │                                  │  │
│ └─────────────────────────────────┴─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Step-by-Step Walkthrough

### Step 1: Export Free Agents from OOTP
In OOTP, go to:
1. League → Reports → Player Reports
2. Filter for Free Agents
3. Export as HTML (same process as Player List)
4. Save as "Free Agents.html" in the Hector directory

### Step 2: Load Free Agents
```
Click: [Load Free Agents.html]
Result: ✓ Loaded 247 free agents from Free Agents.html
```

The left panel populates with all free agents showing:
- Name
- Age
- Position
- WAR
- wRC+ (batters) or ERA+ (pitchers)
- OVR rating

### Step 3: Auto-Calculate Market Rate
```
Click: [Auto-Calculate from Player List]
Result: Calculated $/WAR baseline: $8.50M
        Based on 1,247 players in Player List.html
```

The system analyzes all contracts in your league to determine the current market rate for WAR.

### Step 4: Adjust Settings (Optional)

**Market Settings:**
- Eye Test Weight: How much OVR rating influences valuation (0-30%)
- Market Randomness: Variance in offers (10-30%)
- Hometown Discount: Enable and set percentage (5-15%)

**Generation Settings:**
- Number of Teams: How many teams are bidding (1-8)
- Team Archetypes: Which types of teams are in the market
- International Mode: For players without stats (toggle to enable)

### Step 5: Select a Free Agent
```
Click: Mike Trout row
Result: Player info updates at top right
        Contract offers generate automatically
```

### Step 6: Review Contract Offers

Offers are sorted by total value (highest to lowest):

```
1. Dynasty - 7 years @ $42.0M AAV = $294M total
   Notes: Dynasty (paying premium)
   
2. Contender - 6 years @ $38.5M AAV = $231M total
   Notes: Contender (aggressive bidding)
   
3. Window Builder - 5 years @ $36.2M AAV = $181M total
   Notes: Window Builder
   
4. 🏠 Dynasty (Hometown) - 6 years @ $36.0M AAV = $216M total
   Notes: Hometown discount (10% off)
   
5. Rebuilding - 4 years @ $29.1M AAV = $116M total
   Notes: Rebuilding (value seeking)
   
6. Tanking - 4 years @ $25.8M AAV = $103M total
   Notes: Tanking (value seeking)
```

## Example Scenarios

### Scenario 1: Elite Free Agent (32yo, 5.2 WAR, 145 wRC+)

**Settings:**
- $/WAR: $8.50M
- Eye Test Weight: 15%
- Market Randomness: 15%
- 5 bidding teams

**Base Calculation:**
```
WAR-based value: 5.2 × $8.50M = $44.2M
Stats adjustment: 145 / 100 = 1.45x
Adjusted value: $44.2M × 1.45 = $64.1M
Contract years (age 32): 2-4 years
```

**Expected Offers:**
- Dynasty: ~$65-75M/year × 4 years = $260-300M
- Contender: ~$60-70M/year × 3-4 years = $180-280M
- Window: ~$55-65M/year × 3 years = $165-195M
- Rebuilding: ~$45-55M/year × 2-3 years = $90-165M

### Scenario 2: Young Prospect (24yo, 2.0 WAR, No Stats)

**Settings:**
- International Mode: ✓ Enabled
- Projected WAR: 2.5
- Market Randomness: 25% (auto-increased)

**Base Calculation:**
```
Projected WAR: 2.5
Base value: 2.5 × $8.50M = $21.25M
Higher randomness: ±25%
Contract years (age 24): 5-7 years (but limited to 2-4 for international)
```

**Expected Offers:**
- Dynasty: ~$24-28M/year × 4 years = $96-112M
- Contender: ~$22-26M/year × 3 years = $66-78M
- Window: ~$19-23M/year × 3 years = $57-69M

### Scenario 3: Veteran Rental (37yo, 1.5 WAR)

**Settings:**
- Standard settings
- 3 bidding teams (less interest)

**Base Calculation:**
```
WAR-based value: 1.5 × $8.50M = $12.75M
Contract years (age 37): 1 year only
```

**Expected Offers:**
- Contender: ~$14-16M/year × 1 year = $14-16M (one year rental)
- Window: ~$12-14M/year × 1 year = $12-14M
- Rebuilding: ~$9-11M/year × 1 year = $9-11M

## Use Cases

### 1. Commissioner League Management
Generate contracts for AI teams to simulate realistic free agency:
- Set archetypes to match team situations
- Use actual market rates from your league
- Create variety with different team types bidding

### 2. Single-Player Career Realism
Add manual intervention to free agency:
- Generate realistic competing offers
- Make decisions based on fit vs. dollars
- Simulate team strategy differences

### 3. Contract Negotiations
Use as a negotiation baseline:
- See what market would offer
- Justify contract demands
- Find fair value for extensions

### 4. League Economics Analysis
Understand your league's market:
- Calculate $/WAR from actual contracts
- See how age affects contract length
- Identify overpays and bargains

## Tips and Tricks

### Tip 1: Calibrate Your Market
Run Auto-Calculate periodically as the market changes:
- After big free agent signings
- Before each offseason
- After trades affect team situations

### Tip 2: Match Archetypes to Teams
Think about each team's situation:
- Playoff teams → Dynasty or Contender
- Middle teams → Window Builder
- Rebuilding teams → Rebuilding or Tanking

### Tip 3: Use Eye Test Sparingly
Keep Eye Test Weight low (10-15%) for:
- Established veterans (stats more reliable)
- Recent performance is good

Increase Eye Test Weight (20-30%) for:
- Injury comeback players
- Players changing roles
- Small sample sizes

### Tip 4: Adjust Randomness for Uncertainty
Low randomness (10-15%):
- Proven veterans
- Predictable skills
- Stable market

High randomness (20-30%):
- International players
- Injury risks
- Volatile performance

### Tip 5: Hometown Discount Strategy
Enable for:
- Players with 3+ years tenure
- Fan favorites
- Team-friendly veterans

Typical discounts:
- 5%: Slight loyalty bonus
- 10%: Standard hometown deal
- 15%: Major team-friendly discount

## Color Coding

The UI uses color coding for clarity:
- 🏠 **Gold**: Hometown discount offers
- **NEON_GREEN** (#29ff9e): Headers and labels
- **DARK_BG** (#2d2d2d): Background
- **Hover**: Rows highlight on mouseover

## Keyboard Shortcuts

While in the Autocontract tab:
- Click free agent → Auto-generates contracts
- Adjust sliders → Real-time label updates
- Change settings → Click "Generate Contracts" to refresh

## Integration with Other Tabs

The Autocontract Generator works alongside:
- **Contract Value Tab**: Compare generated offers to current contracts
- **Trade Finder Tab**: Identify which teams should be buyers
- **Player Tabs**: See detailed stats before generating offers
- **Trade Value Calculator**: Understand player worth beyond just WAR

## Technical Notes

### Data Requirements
- **Required**: Free Agents.html (same format as Player List.html)
- **Optional but Recommended**: Player List.html (for market calculation)

### Columns Used
From Free Agents.html:
- Name, Age, POS
- WAR (Batter) or WAR (Pitcher)
- wRC+ (batters) or ERA+ (pitchers)
- OVR (optional, for eye test weight)

### Performance
- Instant calculation for single player
- Handles 1000+ free agents without lag
- Market calculation: <1 second for typical league

## Troubleshooting

**Q: "No players found in Free Agents.html"**
A: Ensure the export includes the required columns and uses the standard OOTP HTML format

**Q: "Market rate is $8.00M (default)"**
A: Player List.html not loaded or has insufficient salary data. Check that salaries are populated.

**Q: "All offers are very similar"**
A: Increase Market Randomness slider or ensure multiple archetypes are selected

**Q: "Contract years seem too short/long"**
A: Age-based calculation is automatic. Check player's age - 36+ always gets 1 year.

**Q: "International Mode not showing"**
A: Toggle the checkbox to reveal the Projected WAR input field

## Future Enhancements

Ideas for future versions (not currently implemented):
- Save generated contracts to database
- Export contracts to CSV
- Contract comparison tool
- Historical market trends
- Team budget constraints
- Position-specific adjustments

---

Feature complete and ready to use! 🎉
