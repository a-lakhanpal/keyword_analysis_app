# Keyword Analysis System - Streamlit App

Generic keyword analysis workflow application with AI classification using OpenAI Batch API.

## Features

- **Auto Column Mapping**: Intelligent detection of CSV columns from SEMrush, Ahrefs, or custom formats
- **Data Cleaning**: Automatic detection and filtering of brand, international, and unrelated keywords
- **Early Universe Creation**: Preview combined dataset before AI classification
- **OpenAI Batch Processing**: Cost-effective AI classification with 50% discount
- **Batch Monitoring**: Real-time status checking with auto-refresh options
- **Session Management**: Save and resume long-running workflows
- **Comprehensive Analysis**: Business value calculation, opportunity scoring, journey phase breakdown
- **Multiple Export Formats**: Download master universe and analysis subsets

## Installation

```bash
cd keyword_analysis_app
pip install -r requirements.txt
```

## Usage

```bash
streamlit run app.py
```

## Workflow Steps

### 1. Upload Files
- **Main Keywords File** (required): SEMrush or Ahrefs CSV with keyword data
- **Your Website Rankings** (optional): Current ranking positions
- **Competitor Files** (optional): Competitor ranking data
- **Resume Session** (optional): Continue from saved session

### 2. Configuration
- **OpenAI API Key**: Required for AI classification
- **Model Selection**: Choose between gpt-4o-mini (recommended), gpt-4o, or gpt-4-turbo
- **Target Country**: Filter international keywords
- **Industry**: Auto-detected or manual selection

### 3. Data Cleaning & Universe Preview
- Automatic detection of brand keywords
- Geographic filtering (exclude international keywords)
- Remove unrelated keywords
- Create Universe v1 (pre-classification)

### 4. AI Classification
- Submit batch to OpenAI Batch API
- Real-time status monitoring
- Auto-refresh option (5-minute intervals)
- Session save/resume capability

### 5. Results & Download
- View UNIVERSE_MASTER with all data merged
- Download analysis files:
  - UNIVERSE_MASTER.csv (main file with everything)
  - Top_200_Opportunities.csv
  - Journey_Phase_Breakdown.csv
  - High_Value_Keywords.csv
  - SEMrush vs AI-Only Keywords

## File Structure

```
keyword_analysis_app/
├── app.py                          # Main Streamlit application
├── components/
│   ├── file_handler.py             # File upload and column mapping
│   ├── data_cleaner.py             # Keyword filtering and cleaning
│   ├── batch_processor.py          # OpenAI Batch API integration
│   ├── universe_builder.py         # Master universe creation
│   ├── progress_tracker.py         # Progress visualization
│   └── session_manager.py          # Session persistence
├── sessions/                       # Saved sessions (auto-created)
├── batches/                        # Batch files and results (auto-created)
├── requirements.txt
└── README.md
```

## OpenAI Batch API

This app uses OpenAI's Batch API for cost-effective classification:
- 50% discount on token costs
- Processes complete within 24 hours
- Full status monitoring and error handling

### Cost Estimates
- **gpt-4o-mini**: ~$0.01-0.02 per 1,000 keywords
- **gpt-4o**: ~$0.30-0.50 per 1,000 keywords

## Session Management

Sessions are automatically saved when:
- Submitting a batch to OpenAI
- Manually clicking "Save & Close"

To resume a session:
1. Go to Step 1: Upload Files
2. Upload your saved session JSON file
3. App will restore your progress

## Column Auto-Detection

The app automatically detects and maps these columns:
- keyword
- search_volume
- cpc
- difficulty
- position
- traffic
- traffic_cost
- trend
- intent
- url
- serp_features

Manual override available if detection is incorrect.

## Data Cleaning

Automatic detection and filtering:
- **Brand Keywords**: Based on competitor names and patterns
- **International Keywords**: Country references (excluding target)
- **Unrelated Keywords**: Industry-specific patterns

## Universe Builder

Creates comprehensive master file by merging:
- Main keywords (cleaned)
- AI classifications (journey phase + search intent)
- Your website rankings
- Competitor rankings (multiple competitors)
- Business metrics (value, opportunity scores)

## Journey Phase Classification

Default phases (customizable):
- UNAWARE
- AWARE_NOT_INSURED
- NEW_CUSTOMER
- POLICY_HOLDER
- RENEWAL
- LIFE_EVENT
- EXPERIENCED_CUSTOMER

## Search Intent Types

- INFORMATIONAL
- COMPARISON
- TRANSACTIONAL
- NAVIGATIONAL
- COMMERCIAL

## Business Value Calculation

```
Business Value = Search Volume × CPC × Journey Weight × Intent Weight
```

## Opportunity Scoring

```
Opportunity Score = (Value Score × 0.5) + (Low Difficulty × 0.3) + (Gap × 0.2)
```

Where:
- **Value Score**: Normalized business value (0-1)
- **Low Difficulty**: (100 - Keyword Difficulty) / 100
- **Gap**: 1 if competitors rank but you don't, 0 otherwise

## Tips

1. **Start with clean data**: Remove test keywords before uploading
2. **Use gpt-4o-mini**: Best cost/accuracy balance for most use cases
3. **Save sessions frequently**: Especially before batch submission
4. **Check batch status**: Usually completes in 2-6 hours
5. **Download all files**: Create backups of analysis results

## Troubleshooting

### Column mapping issues
- Use manual override in Step 1
- Ensure CSV has a 'keyword' column (required)

### Batch submission fails
- Check API key is valid
- Verify sufficient OpenAI credits
- Try again (network issues are temporary)

### Session won't load
- Ensure session JSON is from same app version
- Check that referenced CSV files still exist

### Out of memory
- Process smaller batches (<10,000 keywords)
- Reduce competitor file sizes

## Support

For issues or questions, refer to the main project documentation at:
`/Users/ankur/AI Brief/Customer_Journey_Mapping_System/CLAUDE.md`
