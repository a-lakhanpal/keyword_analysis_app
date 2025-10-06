#!/usr/bin/env python3
"""
Keyword Analysis System - Streamlit App
Single-page application for comprehensive keyword analysis with AI classification
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add modules to path
sys.path.append(str(Path(__file__).parent))

from components.progress_tracker import ProgressTracker
from components.session_manager import SessionManager
from components.file_handler import FileUploadHandler
from components.data_cleaner import DataCleaner
from components.batch_processor import BatchProcessor
from components.universe_builder import UniverseBuilder

# Page config
st.set_page_config(
    page_title="Keyword Analysis System",
    layout="wide",
    initial_sidebar_state="collapsed"  # No sidebar
)

# Initialize session state
if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.uploaded_files = {}
    st.session_state.column_mappings = {}
    st.session_state.settings = {}
    st.session_state.universe_v1 = None
    st.session_state.universe_master = None
    st.session_state.batch_id = None

# Journey phase templates
def get_journey_phases(template: str, custom_phases: str = None) -> list:
    """Get journey phases based on selected template"""
    templates = {
        'Financial Services': ['UNAWARE', 'AWARE', 'RESEARCHING', 'COMPARING', 'MEMBER', 'ACTIVE_MEMBER', 'LIFE_EVENT'],
        'Insurance': ['UNAWARE', 'AWARE_NOT_INSURED', 'RESEARCHING', 'COMPARING', 'POLICY_HOLDER', 'RENEWAL', 'LIFE_EVENT'],
        'E-commerce': ['UNAWARE', 'PROBLEM_AWARE', 'SOLUTION_AWARE', 'PRODUCT_AWARE', 'CUSTOMER', 'REPEAT_CUSTOMER', 'ADVOCATE'],
        'SaaS': ['UNAWARE', 'PROBLEM_AWARE', 'SOLUTION_AWARE', 'EVALUATING', 'TRIAL', 'CUSTOMER', 'POWER_USER'],
        'B2B': ['UNAWARE', 'PROBLEM_AWARE', 'RESEARCH', 'EVALUATION', 'DECISION', 'CUSTOMER', 'EXPANSION']
    }

    if template == 'Custom' and custom_phases:
        return [phase.strip().upper() for phase in custom_phases.split(',')]

    return templates.get(template, templates['Financial Services'])

# App Header
st.title("Keyword Analysis System")
st.markdown("---")

# Progress Indicator
def show_progress_steps():
    """Display progress through workflow steps"""
    steps = [
        ("1. Upload Files", 1),
        ("2. Configure", 2),
        ("3. Clean & Preview", 3),
        ("4. AI Classification", 4),
        ("5. Results & Download", 5)
    ]

    cols = st.columns(5)
    for idx, (step_name, step_num) in enumerate(steps):
        with cols[idx]:
            if st.session_state.step > step_num:
                st.markdown(f"<div style='text-align: center; padding: 10px; background-color: #d4edda; border-radius: 5px; color: #155724;'>{step_name}</div>", unsafe_allow_html=True)
            elif st.session_state.step == step_num:
                st.markdown(f"<div style='text-align: center; padding: 10px; background-color: #d1ecf1; border-radius: 5px; color: #0c5460; font-weight: bold;'>{step_name}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align: center; padding: 10px; color: #6c757d;'>{step_name}</div>", unsafe_allow_html=True)

show_progress_steps()
st.markdown("---")

# Step 1: File Upload
if st.session_state.step == 1:
    st.header("Step 1: Upload Files")

    file_handler = FileUploadHandler()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Required Files")
        main_file = st.file_uploader(
            "Main Keywords File (SEMrush/Ahrefs CSV)",
            type=['csv'],
            key='main_keywords',
            help="Your primary keyword data with search volume, CPC, etc."
        )

        if main_file:
            st.session_state.uploaded_files['main'] = main_file
            with st.spinner("Analyzing file structure..."):
                if file_handler.load_file(main_file):
                    file_info = file_handler.get_file_info()
                    file_type = file_handler.detect_file_type()

                    st.success(f"✅ Loaded {main_file.name} ({file_type} format)")
                    st.caption(f"{file_info['rows']:,} rows × {file_info['columns']} columns ({file_info['size_kb']:.1f} KB)")

                    # Auto-detect columns
                    st.subheader("Column Mapping")
                    detected_mappings = file_handler.auto_detect_columns()

                    if detected_mappings:
                        st.info(f"Auto-detected {len(detected_mappings)} column mappings")

                    st.session_state.column_mappings['main'] = detected_mappings

                    # Show detected mappings
                    with st.expander("Review Column Mappings", expanded=True):
                        for standard_col, original_col in detected_mappings.items():
                            st.text(f"✓ {original_col} → {standard_col}")

                        # Allow manual override
                        if st.checkbox("Manual override"):
                            for standard_col in ['keyword', 'search_volume', 'cpc', 'difficulty', 'position']:
                                available_cols = ['-- None --'] + list(file_info['column_list'])
                                current = detected_mappings.get(standard_col, '-- None --')
                                idx = available_cols.index(current) if current in available_cols else 0
                                selected = st.selectbox(f"{standard_col}:", available_cols, index=idx, key=f"override_{standard_col}")
                                if selected != '-- None --':
                                    st.session_state.column_mappings['main'][standard_col] = selected

                    with st.expander("Preview Data"):
                        st.dataframe(file_handler.get_preview(10))

    with col2:
        st.subheader("Optional Files")

        resume_file = st.file_uploader(
            "Resume Previous Session",
            type=['json'],
            key='resume_session',
            help="Upload a saved session file to continue where you left off"
        )

        if resume_file:
            session_mgr = SessionManager()
            if session_mgr.load_session(resume_file):
                st.success("✅ Session loaded! Resuming...")
                st.rerun()

        rankings_file = st.file_uploader(
            "Your Website Rankings (Optional)",
            type=['csv'],
            key='rankings',
            help="Your website's current keyword rankings"
        )

        if rankings_file:
            st.session_state.uploaded_files['rankings'] = rankings_file

            # Extract brand name from filename
            brand_name = rankings_file.name.split('.')[0]
            brand_name = brand_name.replace('https_', '').replace('http_', '').replace('www_', '').replace('www', '')
            brand_name = brand_name.strip('_').strip('-')
            st.session_state.settings['brand_name'] = brand_name if brand_name else 'brand'

            with st.spinner("Analyzing rankings file structure..."):
                rankings_handler = FileUploadHandler()
                if rankings_handler.load_file(rankings_file):
                    st.success(f"✅ Loaded {rankings_file.name} (Brand: {st.session_state.settings['brand_name']})")

                    # Auto-detect columns for rankings
                    rankings_mappings = rankings_handler.auto_detect_columns()
                    st.session_state.column_mappings['rankings'] = rankings_mappings

                    with st.expander("Rankings Column Mapping"):
                        for standard_col, original_col in rankings_mappings.items():
                            st.text(f"✓ {original_col} → {standard_col}")

        competitor_files = st.file_uploader(
            "Competitor Files (Optional)",
            type=['csv'],
            accept_multiple_files=True,
            key='competitors',
            help="Competitor ranking data from Ahrefs/SEMrush"
        )

        if competitor_files:
            st.session_state.uploaded_files['competitors'] = competitor_files
            st.success(f"✅ Loaded {len(competitor_files)} competitor files")

            # Map each competitor file
            if 'competitor_mappings' not in st.session_state.column_mappings:
                st.session_state.column_mappings['competitor_mappings'] = {}

            for comp_file in competitor_files:
                # Clean competitor name: remove file extension and URL prefixes
                comp_name = comp_file.name.split('.')[0]
                # Remove common URL prefixes
                comp_name = comp_name.replace('https_', '').replace('http_', '').replace('www_', '').replace('www', '')
                # Remove leading/trailing underscores or dashes
                comp_name = comp_name.strip('_').strip('-')

                if not comp_name:
                    continue

                comp_handler = FileUploadHandler()
                if comp_handler.load_file(comp_file):
                    comp_mappings = comp_handler.auto_detect_columns()
                    st.session_state.column_mappings['competitor_mappings'][comp_name] = comp_mappings

                    with st.expander(f"{comp_name} Column Mapping"):
                        for standard_col, original_col in comp_mappings.items():
                            st.text(f"✓ {original_col} → {standard_col}")

    st.markdown("---")

    # Navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col3:
        if st.button("Next: Configure Settings →", type="primary",
                     disabled=main_file is None):
            st.session_state.step = 2
            st.rerun()

# Step 2: Configuration
elif st.session_state.step == 2:
    st.header("Step 2: Configuration")

    # OpenAI Settings at the top
    st.subheader("OpenAI API Settings")
    col1, col2 = st.columns([2, 1])

    with col1:
        api_key = st.text_input(
            "OpenAI API Key",
            value=st.session_state.settings.get('api_key', ''),
            type="password",
            help="Required for AI classification. Get one at platform.openai.com",
            placeholder="sk-..."
        )
        st.session_state.settings['api_key'] = api_key

        if api_key:
            st.success("✅ API Key saved in session")

    with col2:
        model = st.selectbox(
            "Model",
            ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
            index=0,
            help="gpt-4o-mini recommended for cost (50% off with batch)"
        )
        st.session_state.settings['model'] = model

        # Show pricing info
        pricing = {
            "gpt-4o-mini": "$0.075 / 1M tokens",
            "gpt-4o": "$2.50 / 1M tokens",
            "gpt-4-turbo": "$5.00 / 1M tokens"
        }
        st.caption(f"Batch: {pricing[model]}")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Geographic Settings")
        target_country = st.selectbox(
            "Target Country/Region",
            ["New Zealand", "Australia", "United Kingdom", "United States",
             "Canada", "Singapore", "Other"],
            index=0 if not st.session_state.settings.get('target_country') else
                  ["New Zealand", "Australia", "United Kingdom", "United States",
                   "Canada", "Singapore", "Other"].index(st.session_state.settings.get('target_country', 'New Zealand')),
            help="Keywords from other countries will be filtered out"
        )
        st.session_state.settings['target_country'] = target_country

    with col2:
        st.subheader("Industry & Journey Phases")

        industry = st.text_input(
            "Industry / Product Type",
            value=st.session_state.settings.get('industry', ''),
            placeholder="e.g., car insurance, kiwisaver, superannuation, managed funds",
            help="Enter your industry or product type - this will be used for keyword classification"
        )
        st.session_state.settings['industry'] = industry

        journey_template = st.selectbox(
            "Journey Phase Template",
            ["Financial Services", "Insurance", "E-commerce", "SaaS", "B2B", "Custom"],
            help="Pre-built journey phase frameworks for classification"
        )
        st.session_state.settings['journey_template'] = journey_template

        if journey_template == "Custom":
            custom_phases = st.text_area(
                "Define Custom Journey Phases (comma-separated)",
                value="UNAWARE, AWARE, CONSIDERATION, DECISION, CUSTOMER, LOYAL",
                help="Define the customer journey phases for your industry"
            )
            st.session_state.settings['custom_phases'] = custom_phases

    st.markdown("---")

    # Navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← Back"):
            st.session_state.step = 1
            st.rerun()
    with col3:
        if st.button("Next: Clean Data →", type="primary",
                     disabled=not api_key):
            st.session_state.step = 3
            st.rerun()

# Step 3: Data Cleaning & Universe Preview
elif st.session_state.step == 3:
    st.header("Step 3: Data Cleaning & Universe Preview")

    if st.session_state.universe_v1 is None:
        progress_tracker = ProgressTracker()
        data_cleaner = DataCleaner()
        brand_name = st.session_state.settings.get('brand_name', 'brand')
        universe_builder = UniverseBuilder(brand_name=brand_name)

        with st.status("Cleaning keywords...", expanded=True) as status:
            # Load main file
            st.write("⏳ Loading main keywords...")
            file_handler = FileUploadHandler()
            main_file = st.session_state.uploaded_files.get('main')

            # Seek to beginning of file before reading
            if main_file:
                main_file.seek(0)

            if file_handler.load_file(main_file):
                df = file_handler.apply_mappings(st.session_state.column_mappings.get('main'))
                st.write(f"  └─ Loaded {len(df):,} keywords ✓")

                # Detect brand keywords
                st.write("⏳ Detecting brand keywords...")
                competitors = st.session_state.uploaded_files.get('competitors', [])
                competitor_names = [f.name.split('.')[0] for f in competitors] if competitors else []
                brand_kws = data_cleaner.detect_brand_keywords(df, competitor_names)
                st.write(f"  └─ Identified {len(brand_kws)} brand keywords ✓")

                # Detect international keywords
                st.write("⏳ Filtering geographic keywords...")
                target_country = st.session_state.settings.get('target_country', 'New Zealand')
                country_code = 'nz' if 'Zealand' in target_country else target_country[:2].lower()
                intl_kws = data_cleaner.detect_international_keywords(df, country_code)
                st.write(f"  └─ Identified {len(intl_kws)} international keywords ✓")

                # Detect unrelated keywords
                st.write("⏳ Removing unrelated keywords...")
                industry = st.session_state.settings.get('industry', 'insurance')
                unrelated_kws = data_cleaner.detect_unrelated_keywords(df, industry)
                st.write(f"  └─ Identified {len(unrelated_kws)} unrelated keywords ✓")

                # Detect phone numbers
                st.write("⏳ Removing phone numbers...")
                phone_kws = data_cleaner.detect_phone_numbers(df)
                st.write(f"  └─ Identified {len(phone_kws)} phone number keywords ✓")

                # Detect junk/URL keywords
                st.write("⏳ Removing junk/URL keywords...")
                junk_kws = data_cleaner.detect_junk_keywords(df)
                st.write(f"  └─ Identified {len(junk_kws)} junk/URL keywords ✓")

                # Filter dataset
                st.write("⏳ Creating clean dataset...")
                clean_df = data_cleaner.filter_keywords(df, remove_brand=True, remove_international=True, remove_unrelated=True, remove_phone_numbers=True, remove_junk=True)
                st.write(f"  └─ Clean keywords: {len(clean_df):,} ready for classification ✓")

                # Create early universe
                st.write("⏳ Building Universe v1...")
                rankings_file = st.session_state.uploaded_files.get('rankings')
                rankings_df = None
                if rankings_file:
                    try:
                        rankings_file.seek(0)
                        rankings_handler = FileUploadHandler()
                        if rankings_handler.load_file(rankings_file):
                            rankings_mappings = st.session_state.column_mappings.get('rankings', {})
                            rankings_df = rankings_handler.apply_mappings(rankings_mappings)

                            # Clean rankings data (remove phone numbers and other junk)
                            if 'keyword' in rankings_df.columns:
                                initial_count = len(rankings_df)
                                # Use the same cleaner to filter rankings (apply ALL filters)
                                temp_cleaner = DataCleaner()
                                temp_cleaner.detect_phone_numbers(rankings_df)
                                temp_cleaner.detect_brand_keywords(rankings_df, competitor_names)
                                temp_cleaner.detect_junk_keywords(rankings_df)
                                temp_cleaner.detect_international_keywords(rankings_df, country_code)
                                temp_cleaner.detect_unrelated_keywords(rankings_df, industry)
                                rankings_df = temp_cleaner.filter_keywords(rankings_df, remove_brand=True, remove_international=True, remove_unrelated=True, remove_phone_numbers=True, remove_junk=True)

                                # Deduplicate: keep only one row per keyword (prefer highest ranking position)
                                if 'position' in rankings_df.columns:
                                    rankings_df = rankings_df.sort_values('position').drop_duplicates(subset=['keyword'], keep='first')

                                st.write(f"  ├─ Loaded rankings file: {initial_count} → {len(rankings_df)} keywords (removed {initial_count - len(rankings_df)} phone numbers) ✓")
                            else:
                                st.write(f"  ├─ Loaded rankings file ✓")
                    except Exception as e:
                        st.write(f"  ├─ ⚠️ Could not load rankings: {e}")

                competitor_dfs = {}
                if competitors:
                    for comp_file in competitors:
                        # Clean competitor name from filename
                        import re

                        # Remove .csv extension
                        comp_name = comp_file.name
                        if comp_name.endswith('.csv'):
                            comp_name = comp_name[:-4]

                        # Remove timestamp pattern (e.g., _2025-10-01_15-57-10)
                        comp_name = re.sub(r'_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$', '', comp_name)

                        # Remove common URL prefixes
                        comp_name = comp_name.replace('https_', '').replace('http_', '').replace('www_', '')

                        # Remove leading www. if it's a domain
                        if comp_name.startswith('www.'):
                            comp_name = comp_name[4:]

                        # For domain names, take main domain (before first dot after www removal)
                        # e.g., "australianretirementtrust.com.au-organi" -> "australianretirementtrust"
                        if '.' in comp_name:
                            # Take everything before .com or .co or first dot
                            parts = comp_name.split('.')
                            comp_name = parts[0]

                        # Remove trailing suffixes after dash
                        if '-' in comp_name:
                            comp_name = comp_name.split('-')[0]

                        # Clean up remaining underscores/dashes
                        comp_name = comp_name.strip('_').strip('-')

                        # Skip if empty after cleaning
                        if not comp_name:
                            st.write(f"  ├─ ⚠️ Skipped invalid competitor name from file: {comp_file.name}")
                            continue

                        try:
                            comp_file.seek(0)
                            comp_handler = FileUploadHandler()
                            if comp_handler.load_file(comp_file):
                                comp_mappings = st.session_state.column_mappings.get('competitor_mappings', {}).get(comp_name, {})
                                comp_df = comp_handler.apply_mappings(comp_mappings)

                                # Clean competitor data (remove phone numbers)
                                if 'keyword' in comp_df.columns:
                                    initial_count = len(comp_df)
                                    temp_cleaner = DataCleaner()
                                    temp_cleaner.detect_phone_numbers(comp_df)
                                    temp_cleaner.detect_brand_keywords(comp_df, competitor_names)
                                    temp_cleaner.detect_junk_keywords(comp_df)
                                    temp_cleaner.detect_international_keywords(comp_df, country_code)
                                    temp_cleaner.detect_unrelated_keywords(comp_df, industry)
                                    comp_df = temp_cleaner.filter_keywords(comp_df, remove_brand=True, remove_international=True, remove_unrelated=True, remove_phone_numbers=True, remove_junk=True)

                                    # Deduplicate: keep only one row per keyword (prefer highest ranking position)
                                    if 'position' in comp_df.columns:
                                        comp_df = comp_df.sort_values('position').drop_duplicates(subset=['keyword'], keep='first')

                                    competitor_dfs[comp_name] = comp_df
                                    st.write(f"  ├─ Loaded {comp_name}: {initial_count} → {len(comp_df)} keywords ✓")
                                else:
                                    competitor_dfs[comp_name] = comp_df
                                    st.write(f"  ├─ Loaded {comp_name} ✓")
                        except Exception as e:
                            st.write(f"  ├─ ⚠️ Could not load {comp_name}: {e}")

                universe_v1 = universe_builder.create_early_universe(clean_df, rankings_df, competitor_dfs)

                # Final deduplication safety check
                universe_v1 = universe_v1.drop_duplicates(subset=['keyword'], keep='first')

                st.session_state.universe_v1 = universe_v1

                summary = data_cleaner.get_cleaning_summary()
                st.write(f"✅ Total filtered: {summary['total_filtered']} keywords")
                st.write(f"✅ Universe v1 created: {len(universe_v1):,} keywords")

                status.update(label="✅ Cleaning complete!", state="complete")
            else:
                st.error("Failed to load main keywords file. Please check the file format.")
                status.update(label="❌ Failed to load file", state="error")

    # Show preview only if universe exists
    if st.session_state.universe_v1 is not None:
        st.subheader("Universe Preview (Pre-AI Classification)")
        st.dataframe(st.session_state.universe_v1.head(100), use_container_width=True)

        st.download_button(
            label="Download Universe v1 (Pre-Classification)",
            data=st.session_state.universe_v1.to_csv(index=False),
            file_name="universe_v1_pre_classification.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ No data to preview. Please check file upload and try again.")

    st.markdown("---")

    # Navigation
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if st.button("← Back"):
            st.session_state.step = 2
            st.rerun()
    with col3:
        if st.button("Skip AI Classification"):
            st.session_state.step = 5
            st.rerun()
    with col4:
        if st.button("Continue to AI →", type="primary"):
            st.session_state.step = 4
            st.rerun()

# Step 4: AI Classification
elif st.session_state.step == 4:
    st.header("Step 4: AI Classification")

    # Initialize batch processor with saved settings
    api_key = st.session_state.settings.get('api_key')
    model = st.session_state.settings.get('model', 'gpt-4o-mini')
    industry = st.session_state.settings.get('industry', 'insurance')

    if not api_key:
        st.error("❌ No API key found. Please go back to Configuration.")
        if st.button("← Back to Configuration"):
            st.session_state.step = 2
            st.rerun()
        st.stop()

    batch_processor = BatchProcessor(api_key, industry)

    # Calculate batch info
    if st.session_state.universe_v1 is not None:
        # Check if journey_phase column exists, if yes filter for unclassified keywords
        if 'journey_phase' in st.session_state.universe_v1.columns:
            keywords_to_classify = st.session_state.universe_v1[
                st.session_state.universe_v1['journey_phase'].isna()
            ]
        else:
            # No journey_phase column means all keywords need classification
            keywords_to_classify = st.session_state.universe_v1.copy()
    else:
        keywords_to_classify = pd.DataFrame()

    num_keywords = len(keywords_to_classify)
    cost_estimate = batch_processor.estimate_cost(num_keywords) if num_keywords > 0 else {}

    # Batch summary
    st.subheader("Batch Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Keywords to Classify", f"{num_keywords:,}")
    with col2:
        st.metric("Model", model)
    with col3:
        st.metric("Total Tokens", f"{cost_estimate.get('total_tokens', 0):,}")
    with col4:
        st.metric("Estimated Cost", f"${cost_estimate.get('estimated_cost_usd', 0):.4f} USD")

    # Pause point warning
    st.warning("""
    ⚠️ **IMPORTANT: Batch Processing Notice**

    OpenAI batch processing runs in the background and can take **2-24 hours** to complete.

    **Options:**
    1. Submit batch and close browser → Come back later and click "Check Status"
    2. Keep this page open (prevents Streamlit sleep) → Auto-refresh every 5 minutes

    We'll save your session either way!
    """)

    st.subheader("Option 1: Resume Existing Batch")
    with st.expander("💡 Already have a Batch ID? Enter it here"):
        st.info("Use this if you went back to fix data but already submitted a batch")

        manual_batch_id = st.text_input(
            "Batch ID",
            placeholder="batch_xxxxxxxxxxxxx",
            help="Enter your existing OpenAI batch ID"
        )

        if st.button("Load This Batch ID"):
            if manual_batch_id.startswith("batch_"):
                st.session_state.batch_id = manual_batch_id
                st.rerun()
            else:
                st.error("❌ Invalid batch ID format (should start with 'batch_')")

    st.markdown("---")
    st.subheader("Option 2: Submit New Batch")

    if st.session_state.batch_id is None:
        if num_keywords == 0:
            st.info("✅ All keywords already classified! Proceeding to final universe...")
            if st.button("Continue to Results →", type="primary"):
                st.session_state.step = 5
                st.rerun()
        else:
            # Get journey phases based on selected template
            journey_template = st.session_state.settings.get('journey_template', 'Financial Services')
            custom_phases = st.session_state.settings.get('custom_phases', '')
            journey_phases = get_journey_phases(journey_template, custom_phases)
            intent_types = ['INFORMATIONAL', 'COMPARISON', 'TRANSACTIONAL', 'NAVIGATIONAL', 'COMMERCIAL']

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("Submit Batch & Close", type="primary"):
                    with st.spinner("Preparing batch file..."):
                        jsonl_file = batch_processor.prepare_batch_file(keywords_to_classify, journey_phases, intent_types)
                        st.success(f"✓ Created batch file: {jsonl_file}")

                    with st.spinner("Submitting to OpenAI..."):
                        batch_id = batch_processor.submit_batch(jsonl_file)

                        if batch_id:
                            st.session_state.batch_id = batch_id
                            session_mgr = SessionManager()
                            session_file = session_mgr.save_session(st.session_state)
                            st.success(f"✅ Batch submitted! ID: {batch_id}")
                            st.success(f"Session saved to: {session_file}")
                            st.info("You can close this page and return later.")
                            st.rerun()

            with col2:
                if st.button("Submit & Keep Checking"):
                    with st.spinner("Preparing batch file..."):
                        jsonl_file = batch_processor.prepare_batch_file(keywords_to_classify, journey_phases, intent_types)

                    with st.spinner("Submitting to OpenAI..."):
                        batch_id = batch_processor.submit_batch(jsonl_file)

                        if batch_id:
                            st.session_state.batch_id = batch_id
                            st.session_state.auto_refresh = True
                            st.rerun()

            with col3:
                if st.button("← Cancel"):
                    st.session_state.step = 3
                    st.rerun()

    else:
        # Show batch monitoring using actual batch processor
        status_info = batch_processor.get_batch_status(st.session_state.batch_id)

        st.subheader("Batch Status")

        col1, col2 = st.columns([2, 1])
        with col1:
            status = status_info.get('status', 'unknown')
            status_colors = {
                'validating': '🔵',
                'in_progress': '🟡',
                'finalizing': '🟠',
                'completed': '🟢',
                'failed': '🔴',
                'expired': '⚫',
                'cancelling': '🟤',
                'cancelled': '⚪'
            }
            status_emoji = status_colors.get(status, '⚪')

            st.info(f"{status_emoji} **Status:** {status.upper().replace('_', ' ')}")
            st.text(f"Batch ID: {st.session_state.batch_id}")

            if 'request_counts' in status_info:
                counts = status_info['request_counts']
                total = counts.get('total', 0)
                completed = counts.get('completed', 0)
                failed = counts.get('failed', 0)

                st.text(f"Progress: {completed} / {total} completed")
                if failed > 0:
                    st.text(f"⚠️ Failed: {failed}")

                if total > 0:
                    progress = completed / total
                    st.progress(progress)

        with col2:
            if st.button("Check Status Now"):
                st.rerun()

            if status in ['validating', 'in_progress', 'finalizing']:
                auto_refresh = st.checkbox("Auto-refresh every 5 min")
                if auto_refresh:
                    import time
                    time.sleep(300)  # 5 minutes
                    st.rerun()

            if st.button("Save & Close"):
                session_mgr = SessionManager()
                session_file = session_mgr.save_session(st.session_state)
                st.success(f"Session saved: {session_file}")

        if status == 'completed':
            st.success("✅ Batch Completed! Downloading results...")

            # Download and parse results
            with st.spinner("Retrieving batch results..."):
                results_file = batch_processor.retrieve_results(st.session_state.batch_id)

                if results_file:
                    st.success(f"✓ Downloaded results: {results_file}")

                    # Parse and merge with universe
                    classified_df = batch_processor.parse_results(results_file, keywords_to_classify)
                    st.session_state.classified_keywords = classified_df
                    st.success(f"✓ Parsed {len(classified_df)} classified keywords")

            if st.button("Continue to Final Universe →", type="primary"):
                st.session_state.step = 5
                st.rerun()

        elif status == 'failed':
            st.error("❌ Batch processing failed. Please check your API key and try again.")
            if st.button("← Back to Classification"):
                st.session_state.batch_id = None
                st.rerun()

# Step 5: Results & Download
elif st.session_state.step == 5:
    st.header("Step 5: Final Universe & Analysis")

    if st.session_state.universe_master is None:
        brand_name = st.session_state.settings.get('brand_name', 'brand')
        universe_builder = UniverseBuilder(brand_name=brand_name)

        with st.status("Building final universe...", expanded=True) as status:
            st.write("⏳ Creating UNIVERSE_MASTER...")

            # Start with universe v1 (already has main + rankings + competitors merged)
            universe_master = st.session_state.universe_v1.copy()

            # Merge newly classified keywords
            if st.session_state.get('classified_keywords') is not None:
                classified = st.session_state.classified_keywords
                # Merge classifications back
                for idx, row in classified.iterrows():
                    if 'journey_phase' in row and 'search_intent' in row:
                        mask = universe_master['keyword'] == row['keyword']
                        universe_master.loc[mask, 'journey_phase'] = row['journey_phase']
                        universe_master.loc[mask, 'search_intent'] = row['search_intent']
                st.write(f"  ├─ Merged {len(classified)} AI classifications ✓")

            st.write(f"  └─ Total keywords: {len(universe_master):,} ✓")

            # Calculate business metrics
            st.write("⏳ Calculating business metrics...")
            universe_builder = UniverseBuilder(st.session_state.settings.get('brand_name', 'brand'))
            universe_master = universe_builder._calculate_business_value(universe_master)
            universe_master = universe_builder._calculate_opportunity_scores(universe_master)
            st.write(f"  └─ Business metrics calculated ✓")

            stats = universe_builder.get_universe_stats()
            for log in stats.get('logs', []):
                st.write(f"  {log}")

            # Create subsets
            st.write("⏳ Generating analysis subsets...")
            subsets = universe_builder.create_subsets(universe_master)
            st.write(f"  └─ Created {len(subsets)} analysis files ✓")

            st.session_state.universe_master = universe_master
            st.session_state.analysis_subsets = subsets

            status.update(label="✅ Universe complete!", state="complete")

    # Dashboard
    st.subheader("Dashboard")
    universe = st.session_state.universe_master
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Keywords", f"{len(universe):,}")
    with col2:
        classified_count = universe['journey_phase'].notna().sum() if 'journey_phase' in universe.columns else 0
        st.metric("Classified", f"{classified_count:,}")
    with col3:
        total_value = universe['business_value'].sum() if 'business_value' in universe.columns else 0
        st.metric("Business Value", f"${total_value:,.0f}")
    with col4:
        brand_name = st.session_state.settings.get('brand_name', 'brand')
        safe_brand = brand_name.lower().replace(' ', '_')
        brand_pos_col = f'{safe_brand}_position'
        brand_count = universe[brand_pos_col].notna().sum() if brand_pos_col in universe.columns else 0
        st.metric(f"{brand_name} Rankings", f"{brand_count}")

    # Universe preview
    st.subheader("UNIVERSE_MASTER Preview")
    st.dataframe(st.session_state.universe_master, use_container_width=True)

    # SERP Features Analysis (Optional)
    st.markdown("---")
    st.subheader("SERP Features Analysis (Optional)")

    # Extract SERP features from universe
    universe_builder_temp = UniverseBuilder()
    serp_features_dict = universe_builder_temp.extract_serp_features(universe)

    if serp_features_dict:
        st.write(f"Found **{len(serp_features_dict)}** unique SERP features in your data:")

        # Create feature options with stats
        feature_options = []
        for feature, stats in sorted(serp_features_dict.items(), key=lambda x: x[1]['count'], reverse=True):
            volume_str = f"{int(stats['total_volume']):,}" if stats['total_volume'] > 0 else "N/A"
            option_label = f"{feature} ({stats['count']} keywords, {volume_str} volume)"
            feature_options.append((feature, option_label))

        # Multiselect for SERP features
        selected_features = st.multiselect(
            "Select SERP features to analyze:",
            options=[f[0] for f in feature_options],
            format_func=lambda x: next(f[1] for f in feature_options if f[0] == x),
            help="Select which SERP features you want to create separate CSV files for"
        )

        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("Generate SERP Feature Files", disabled=len(selected_features) == 0):
                with st.spinner("Generating SERP feature files..."):
                    serp_files = universe_builder_temp.create_serp_feature_files(universe, selected_features)
                    st.session_state.serp_files = serp_files
                    st.success(f"✅ Generated {len(serp_files)} SERP feature files!")

        with col2:
            if st.button("Select All Features"):
                st.session_state.select_all_serp = True
                st.rerun()

        # Handle Select All
        if st.session_state.get('select_all_serp', False):
            selected_features = [f[0] for f in feature_options]
            st.session_state.select_all_serp = False
            with st.spinner("Generating SERP feature files..."):
                serp_files = universe_builder_temp.create_serp_feature_files(universe, selected_features)
                st.session_state.serp_files = serp_files
                st.success(f"✅ Generated {len(serp_files)} SERP feature files!")

        # Show generated files info
        if 'serp_files' in st.session_state and st.session_state.serp_files:
            st.write(f"**Generated files:** {len(st.session_state.serp_files)} ready for download")
    else:
        st.info("No SERP features column found in your data, or column is empty.")

    # Download section
    st.markdown("---")
    st.subheader("Download Results")

    subsets = st.session_state.get('analysis_subsets', {})
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    industry = st.session_state.settings.get('industry', 'analysis')

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Main Files**")
        st.download_button(
            "UNIVERSE_MASTER.csv",
            universe.to_csv(index=False),
            f"{industry.upper()}_UNIVERSE_MASTER.csv",
            "text/csv",
            use_container_width=True
        )

        if 'top_opportunities' in subsets:
            st.download_button(
                "Top_200_Opportunities.csv",
                subsets['top_opportunities'].to_csv(index=False),
                f"Top_200_Opportunities_{timestamp}.csv",
                "text/csv",
                use_container_width=True
            )

    with col2:
        st.markdown("**Analysis Files**")
        if 'journey_breakdown' in subsets:
            st.download_button(
                "Journey_Phase_Breakdown.csv",
                subsets['journey_breakdown'].to_csv(index=False),
                f"Journey_Phase_Breakdown_{timestamp}.csv",
                "text/csv",
                use_container_width=True
            )

        if 'high_value' in subsets:
            st.download_button(
                "High_Value_Keywords.csv",
                subsets['high_value'].to_csv(index=False),
                f"High_Value_Keywords_{timestamp}.csv",
                "text/csv",
                use_container_width=True
            )

        if 'low_hanging_fruit' in subsets:
            st.download_button(
                "Low_Hanging_Fruit.csv",
                subsets['low_hanging_fruit'].to_csv(index=False),
                f"Low_Hanging_Fruit_{timestamp}.csv",
                "text/csv",
                use_container_width=True
            )

        if 'high_volume_low_competition' in subsets:
            st.download_button(
                "High_Volume_Low_Competition.csv",
                subsets['high_volume_low_competition'].to_csv(index=False),
                f"High_Volume_Low_Competition_{timestamp}.csv",
                "text/csv",
                use_container_width=True
            )

        if 'newly_discovered' in subsets:
            st.download_button(
                "Newly_Discovered.csv",
                subsets['newly_discovered'].to_csv(index=False),
                f"Newly_Discovered_{timestamp}.csv",
                "text/csv",
                use_container_width=True
            )

    with col3:
        st.markdown("**Strategic Analysis**")
        if 'brand_analysis' in subsets:
            st.download_button(
                "Brand_Analysis.csv",
                subsets['brand_analysis'].to_csv(index=False),
                f"Brand_Analysis_{timestamp}.csv",
                "text/csv",
                use_container_width=True
            )

        if 'business_insights' in subsets:
            st.download_button(
                "Business_Insights.csv",
                subsets['business_insights'].to_csv(index=False),
                f"Business_Insights_{timestamp}.csv",
                "text/csv",
                use_container_width=True
            )

        # ZIP download
        import io
        import zipfile

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add universe master
            zip_file.writestr(f"{industry.upper()}_UNIVERSE_MASTER.csv", universe.to_csv(index=False))

            # Add all subsets
            for name, df in subsets.items():
                filename = f"{name.title().replace('_', '_')}_{timestamp}.csv"
                zip_file.writestr(filename, df.to_csv(index=False))

        st.download_button(
            "Download All (ZIP)",
            zip_buffer.getvalue(),
            f"{industry}_analysis_{timestamp}.zip",
            "application/zip",
            use_container_width=True
        )

    # SERP Features Downloads (if generated)
    if 'serp_files' in st.session_state and st.session_state.serp_files:
        st.markdown("---")
        st.markdown("**SERP Features Analysis**")

        serp_files = st.session_state.serp_files

        # Create columns for SERP feature downloads (max 3 per row)
        serp_features_list = [(k, v) for k, v in serp_files.items() if k != 'serp_features_summary']

        # Combine summary and features into a single list for consistent display
        all_serp_downloads = []

        if 'serp_features_summary' in serp_files:
            all_serp_downloads.append(('SERP_Features_Summary.csv', 'serp_features_summary', serp_files['serp_features_summary']))

        for feature_key, feature_df in serp_features_list:
            button_label = feature_key.replace('_', ' ').title() + '.csv'
            all_serp_downloads.append((button_label, feature_key, feature_df))

        # Display all downloads in columns (3 per row)
        if all_serp_downloads:
            cols_per_row = 3
            for i in range(0, len(all_serp_downloads), cols_per_row):
                cols = st.columns(cols_per_row)

                for j in range(cols_per_row):
                    idx = i + j
                    if idx < len(all_serp_downloads):
                        button_label, key_name, df = all_serp_downloads[idx]
                        with cols[j]:
                            filename = f"{key_name}_{timestamp}.csv" if key_name != 'serp_features_summary' else f"SERP_Features_Summary_{timestamp}.csv"
                            st.download_button(
                                button_label,
                                df.to_csv(index=False),
                                filename,
                                "text/csv",
                                use_container_width=True,
                                key=f"serp_{key_name}"
                            )

        # Update ZIP to include SERP files
        st.markdown("---")
        st.markdown("**Download Everything (Including SERP Features)**")

        zip_buffer_all = io.BytesIO()
        with zipfile.ZipFile(zip_buffer_all, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add universe master
            zip_file.writestr(f"{industry.upper()}_UNIVERSE_MASTER.csv", universe.to_csv(index=False))

            # Add all subsets
            for name, df in subsets.items():
                filename = f"{name.title().replace('_', '_')}_{timestamp}.csv"
                zip_file.writestr(filename, df.to_csv(index=False))

            # Add SERP feature files
            for feature_key, feature_df in serp_files.items():
                filename = f"SERP_{feature_key}_{timestamp}.csv"
                zip_file.writestr(filename, feature_df.to_csv(index=False))

        st.download_button(
            "Download All + SERP Features (ZIP)",
            zip_buffer_all.getvalue(),
            f"{industry}_complete_analysis_{timestamp}.zip",
            "application/zip",
            use_container_width=False
        )

    st.markdown("---")

    # Options
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Classify More Keywords"):
            st.session_state.step = 3
            st.rerun()
    with col2:
        if st.button("Export Session"):
            session_mgr = SessionManager()
            session_file = session_mgr.save_session(st.session_state)
            st.success(f"Session saved: {session_file}")
    with col3:
        if st.button("Start New Analysis"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

