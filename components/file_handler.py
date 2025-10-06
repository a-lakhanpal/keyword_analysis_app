"""
File Upload Handler Component
Handles CSV uploads with intelligent column mapping
"""

import pandas as pd
import streamlit as st
from typing import Dict, List, Optional
from rapidfuzz import fuzz, process

class FileUploadHandler:
    """Handle file uploads and auto-detect column mappings"""

    # Standard column names we expect
    STANDARD_COLUMNS = {
        'keyword': ['keyword', 'query', 'search term', 'term', 'keywords'],
        'search_volume': ['search volume', 'volume', 'searches', 'monthly searches', 'avg monthly searches'],
        'cpc': ['cpc', 'cost per click', 'avg cpc', 'cost'],
        'difficulty': ['keyword difficulty', 'difficulty', 'kd', 'competition', 'keyword competition'],
        'intent': ['intent', 'search intent', 'user intent'],
        'position': ['position', 'rank', 'ranking', 'current position'],
        'traffic': ['traffic', 'estimated traffic', 'visits', 'organic traffic'],
        'traffic_cost': ['traffic cost', 'traffic value', 'cost', 'value'],
        'trend': ['trend', 'trends', 'trend data'],
        'url': ['url', 'page', 'landing page', 'target url'],
        'serp_features': ['serp features', 'serp', 'features']
    }

    def __init__(self):
        self.df = None
        self.column_mappings = {}

    def load_file(self, uploaded_file) -> bool:
        """Load CSV file into dataframe"""
        try:
            self.df = pd.read_csv(uploaded_file)
            return True
        except Exception as e:
            st.error(f"Failed to load file: {e}")
            return False

    def auto_detect_columns(self) -> Dict[str, str]:
        """Auto-detect column mappings using fuzzy matching"""
        if self.df is None:
            return {}

        detected_mappings = {}
        available_columns = list(self.df.columns)

        for standard_col, variations in self.STANDARD_COLUMNS.items():
            # Try exact match first (case insensitive)
            for col in available_columns:
                if col.lower() in [v.lower() for v in variations]:
                    detected_mappings[standard_col] = col
                    break

            # If no exact match, use fuzzy matching
            if standard_col not in detected_mappings and available_columns:
                best_match = process.extractOne(
                    standard_col,
                    available_columns,
                    scorer=fuzz.ratio,
                    score_cutoff=60
                )
                if best_match:
                    detected_mappings[standard_col] = best_match[0]

        self.column_mappings = detected_mappings
        return detected_mappings

    def apply_mappings(self, custom_mappings: Optional[Dict[str, str]] = None) -> pd.DataFrame:
        """Apply column mappings and return standardized dataframe"""
        if self.df is None:
            return None

        # Use custom mappings if provided, otherwise use auto-detected
        mappings = custom_mappings or self.column_mappings

        # Create new dataframe with standardized columns
        standardized_df = pd.DataFrame()

        for standard_col, original_col in mappings.items():
            if original_col and original_col in self.df.columns:
                standardized_df[standard_col] = self.df[original_col]

        # Add any unmapped columns with original names
        mapped_original_cols = set(mappings.values())
        for col in self.df.columns:
            if col not in mapped_original_cols:
                standardized_df[col] = self.df[col]

        return standardized_df

    def get_preview(self, rows: int = 5) -> pd.DataFrame:
        """Get preview of dataframe"""
        if self.df is None:
            return None
        return self.df.head(rows)

    def get_file_info(self) -> Dict:
        """Get file statistics"""
        if self.df is None:
            return {}

        return {
            'rows': len(self.df),
            'columns': len(self.df.columns),
            'size_kb': self.df.memory_usage(deep=True).sum() / 1024,
            'column_list': list(self.df.columns)
        }

    def detect_file_type(self) -> str:
        """Detect if this is SEMrush, Ahrefs, or other format"""
        if self.df is None:
            return "Unknown"

        columns_lower = [col.lower() for col in self.df.columns]

        # SEMrush indicators
        semrush_indicators = ['keyword difficulty', 'cpc', 'search volume', 'serp features']
        if sum(ind in ' '.join(columns_lower) for ind in semrush_indicators) >= 3:
            return "SEMrush"

        # Ahrefs indicators
        ahrefs_indicators = ['keyword', 'position', 'url', 'traffic', 'volume']
        if sum(ind in ' '.join(columns_lower) for ind in ahrefs_indicators) >= 3:
            return "Ahrefs"

        return "Custom"

    def validate_required_fields(self) -> tuple[bool, List[str]]:
        """Check if required fields are present"""
        required = ['keyword']
        missing = []

        for field in required:
            if field not in self.column_mappings or not self.column_mappings[field]:
                missing.append(field)

        return len(missing) == 0, missing
