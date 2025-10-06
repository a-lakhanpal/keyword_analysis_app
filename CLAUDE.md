# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Streamlit application for keyword analysis and AI-powered customer journey classification. Processes SEMrush/Ahrefs keyword data, uses OpenAI Batch API to classify keywords by customer journey phase and search intent, and generates comprehensive business insights.

**Primary Users:** Financial services companies (KiwiSaver, car insurance, managed funds)
**Key Technology:** Python/Streamlit + OpenAI Batch API + Pandas

## Commands

### Development
```bash
# Run the application
streamlit run app.py

# Install dependencies
pip install -r requirements.txt
```

### Testing
The app uses real data validation rather than unit tests. When making changes to data merge logic in `universe_builder.py`, validate with actual CSV files across the full workflow.

## Architecture

### 5-Step Workflow (app.py)
1. **Upload Files** - Main keywords (SEMrush), brand rankings (Ahrefs), competitor files
2. **Configure** - OpenAI API key, model selection, industry/journey phases
3. **Clean & Preview** - Filter brand/international/unrelated keywords, create Universe v1
4. **AI Classification** - Submit batch to OpenAI, monitor status (2-24 hours)
5. **Results** - Generate Universe Master + analysis subsets

### Critical Data Flow

**Universe v1 (Pre-AI):**
```
main_keywords (SEMrush)
  → merge brand_rankings (outer join)
  → merge competitors (outer join for each)
  → universe_v1 (all keywords from all sources)
```

**Universe Master (Post-AI):**
```
universe_v1
  + AI classifications (journey_phase + search_intent)
  → calculate business_value (volume × cpc × journey_weight × intent_weight)
  → calculate opportunity_scores
  → universe_master
```

### Component Architecture

**components/file_handler.py**
- Auto-detects CSV format (SEMrush vs Ahrefs)
- Fuzzy column mapping (e.g., "Volume" → "search_volume", "KD" → "difficulty")
- Handles manual column overrides

**components/data_cleaner.py**
- Detects and filters: brand keywords, international keywords, phone numbers, unrelated keywords
- Pattern-based detection using competitor names and industry context
- Maintains filtering statistics for user display

**components/universe_builder.py** ⚠️ CRITICAL
- **Most important file** - handles all data merging
- Two major bugs fixed Oct 2, 2025 (see BUG_FIX_SUMMARY.md and CONTEXT.md)
- **Key merge logic:** When merging DataFrames with duplicate columns (search_volume, cpc, difficulty), pandas creates `_x` and `_y` suffixes. Must coalesce these correctly to preserve data from rankings files.
- **Pattern-matching weights:** Uses intelligent fallback for journey phases and intents that AI might return differently than templates (e.g., "RESEARCHING" vs "RESEARCH"). Never hardcode exact phase names.
- Creates analysis subsets: low hanging fruit, high value, top opportunities, journey breakdown

**components/batch_processor.py**
- Creates JSONL batch files for OpenAI Batch API
- Submits batches and monitors status
- Parses batch results and extracts journey_phase + search_intent
- Handles batch resume by batch_id (allows user to fix data without resubmitting)

**components/session_manager.py**
- Saves/loads Streamlit session state as JSON
- Enables long-running workflows (batch processing takes hours)

### Critical Code Sections

**universe_builder.py Lines 94-115:** Brand rankings merge with column coalescing
```python
# After merge creates _x and _y suffixes for duplicate columns
universe = pd.merge(universe, brand_data, on='keyword', how='outer')

# MUST coalesce to preserve data from rankings files
for col in ['search_volume', 'cpc', 'difficulty']:
    col_x = f'{col}_x'
    col_y = f'{col}_y'
    if col_x in universe.columns and col_y in universe.columns:
        universe[col] = universe[col_x].fillna(universe[col_y])
        universe = universe.drop([col_x, col_y], axis=1)
```

**universe_builder.py Lines 173-255:** Journey/intent weight calculation
- Uses pattern matching to handle ANY industry's journey phases
- Never hardcode exact phase names (breaks for different industries)
- Fallback logic: "research/browse" → 0.6, "compar" → 0.9, "checkout/purchase" → 1.0, etc.

**app.py Lines 567-583:** Manual batch ID resume
- Allows user to enter existing batch_id if they went back to fix data
- Prevents expensive resubmission to OpenAI

## Data Merge Strategy

**Join Type:** Always use `outer` join to include keywords from all sources
**Priority:** Main file data preferred over rankings data (use `fillna()` to backfill)
**Deduplication:** Automatic via merge on 'keyword' column

Common data sources:
- **Main keywords:** 2,000+ keywords from SEMrush (has search_volume, cpc, difficulty)
- **Brand rankings:** 1,000+ keywords from Ahrefs (has position, plus may have volume/cpc/difficulty for keywords not in main)
- **Competitors:** 4-5 competitor files with 500-1,500 keywords each

Total universe typically 4,000-5,000 unique keywords after merge.

## Business Value Calculation

```
business_value = search_volume × cpc × journey_weight × intent_weight
```

**Journey weights** (pattern-matched, not hardcoded):
- Unaware/Discovery: 0.3
- Learning/Aware: 0.5
- Research/Browse/Evaluate: 0.6
- Compare/Consideration: 0.9
- Decision/Purchase/Checkout: 1.0
- Customer/Member: 0.6
- Renewal: 0.7
- Power/Advocate: 0.8

**Intent weights:**
- Transactional: 1.0
- Commercial/Comparison: 0.9
- Navigational: 0.7
- Informational: 0.5

## Known Issues & Important Context

1. **Missing CPC data:** Some keywords legitimately have no CPC → business_value = 0 (correct behavior)

2. **Batch processing time:** OpenAI batches take 2-24 hours. App supports two modes: close browser and resume later, or keep page open with auto-refresh.

3. **Column mapping edge cases:** Auto-detection works for SEMrush and Ahrefs. For other formats, provide manual override in Step 1.

4. **AI classification variations:** AI might return "RESEARCHING" instead of template's "RESEARCH". Pattern matching handles this. Never use `.map()` with hardcoded dictionaries for journey phases.

5. **Session state persistence:** Streamlit resets on browser refresh. Session save/resume via JSON files is critical for long workflows.

## Historical Context

**Major bugs fixed Oct 2, 2025:**

1. **Empty search_volume/cpc/difficulty** (CRITICAL): Keywords from rankings files lost data because merge created `_x/__y` suffixes but code tried to access unsuffixed columns. Fix: Coalesce logic in Lines 94-115, 145-166 of universe_builder.py

2. **Hardcoded journey phase weights** (CRITICAL): Used dictionary with exact Insurance phase names. AI returned different phase names → 95% of keywords defaulted to 0.5 weight → wrong business value. Fix: Pattern-matching functions `_get_journey_weight()` and `_get_intent_weight()` that work for ANY industry.

See CONTEXT.md for detailed bug history and BUG_FIX_SUMMARY.md for technical validation.

## File Naming Patterns

**Competitor files:** Remove URL prefixes (`https_`, `www_`), domain extensions (`.com.au`), timestamps, and extract base name. Example: `https_australianretirementtrust.com.au-organic_2025-10-01.csv` → `australianretirementtrust`

**Brand name extraction:** Similar cleaning from filename, stored in session state as `brand_name`

**Position columns:** Created as `{brand_name}_position` (e.g., `aware_position`, `australiansuper_position`)

## When Making Changes

**To data merge logic (universe_builder.py):**
- Validate with actual CSV files (not just dummy data)
- Check that keywords appearing only in rankings files retain their data
- Verify no duplicate keywords in final universe
- Test with 6+ files (1 main + 1 brand + 4 competitors)

**To journey/intent weights (universe_builder.py):**
- Use pattern matching, never hardcoded exact phase names
- Test with multiple industries (Financial Services, Insurance, E-commerce, SaaS)
- Verify business_value calculations are not defaulting to 0.5 weights

**To batch processing (batch_processor.py):**
- Remember batch submission costs money
- Provide ways to resume/retry without resubmission
- Handle all OpenAI batch statuses: validating, in_progress, finalizing, completed, failed

**To UI (app.py):**
- Keep minimal comments (no "NEW:" or obvious annotations)
- Maintain 5-step workflow structure
- Preserve session state management for long-running operations
