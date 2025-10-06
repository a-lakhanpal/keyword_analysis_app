"""
Data Cleaning Component
Handles filtering of brand, international, and unrelated keywords
"""

import pandas as pd
import streamlit as st
from typing import List, Dict, Set
import re

class DataCleaner:
    """Clean and filter keyword data"""

    def __init__(self):
        self.cleaning_logs = []
        self.brand_keywords = set()
        self.international_keywords = set()
        self.unrelated_keywords = set()
        self.phone_number_keywords = set()
        self.junk_keywords = set()

    def detect_brand_keywords(self, df: pd.DataFrame, competitor_names: List[str] = None) -> Set[str]:
        """Detect brand keywords based on competitor names"""
        brand_keywords = set()

        if competitor_names is None:
            competitor_names = []

        # Comprehensive insurance/financial brands (NZ + International)
        default_brands = [
            # NZ insurers
            'amp', 'tower', 'aa insurance', 'aa', 'state', 'ami', 'anz',
            '1cover', 'southern cross', 'youi', 'vero', 'cove', 'nib',
            'asteron', 'fidelity', 'partners life', 'aia', 'cigna',
            # International insurers
            'aig', 'aaa', 'aami', 'admiral', 'aviva', 'aon', 'allianz', 'allstate',
            'american', 'ama', 'amica', 'argonaut', 'assurant',
            'bupa', 'chubb', 'churchill', 'direct line', 'esurance', 'farmers',
            'geico', 'general', 'gocompare', 'hastings', 'hiscox',
            'liberty', 'lv', 'medibank', 'metlife', 'nationwide', 'progressive',
            'prudential', 'qbe', 'raa', 'racv', 'racq', 'rac', 'nrma',
            'saga', 'suncorp', 'swann', 'the general', 'travelers', 'usaa',
            'woolworths insurance', 'zurich', 'budget direct', 'comparethemarket', 'moneysupermarket',
            # Rental companies (rental car insurance is brand-related)
            'hertz', 'avis', 'budget', 'thrifty', 'enterprise', 'europcar',
            'sixt', 'dollar', 'alamo', 'national', 'payless', 'ace',
            'apex', 'alaska rental', 'advantage',
            # Banks & financial services
            'bnz', 'westpac', 'asb', 'kiwibank', 'tsb', 'sbs',
            'american express', 'amex', 'visa', 'mastercard',
            # KiwiSaver providers (NZ)
            'simplicity', 'generate', 'fisher funds', 'fisherfunds', 'milford',
            'smartshares', 'sharesies', 'kernel', 'booster', 'kiwi wealth', 'koura',
            'mercer', 'generate wealth', 'juno', 'amanah', 'aon russell',
            # Australian superannuation funds
            'australiansuper', 'australian super', 'aust super',
            'australian retirement trust', 'aware super', 'aware',
            'hostplus', 'host plus', 'rest super', 'rest',
            'cbus', 'hesta', 'unisuper', 'qsuper', 'sunsuper',
            'care super', 'caresuper', 'catholic super', 'bussq',
            'child care super', 'energy super', 'equip super', 'first super',
            'future super', 'guild super', 'guildsuper', 'grow super',
            'spirit super', 'maritime super', 'media super', 'telstra super',
            'essuper', 'gesb', 'qantas super', 'virgin super',
            'crescent wealth', 'cruelty free super', 'ioof', 'ing super',
            'asgard', 'bt super', 'colonial first state', 'macquarie super',
            'mlc super', 'onepath', 'vision super', 'bendigo super',
            # Other financial
            'latitude', 'genoapay', 'afterpay', 'humm', 'klarna', 'zip'
        ]
        all_brands = list(set(competitor_names + default_brands))

        # Special patterns for short brand names that need word boundaries
        short_brands = ['aa', 'ami', 'anz', 'aia', 'bnz', 'asb', 'tsb', 'sbs', 'nib',
                       'aig', 'aaa', 'ama', 'aon', 'lv', 'qbe', 'raa', 'rac', 'ace', 'zip',
                       'rest', 'cbus', 'hesta', 'gesb', 'ioof', 'ing', 'mlc']

        for keyword in df['keyword']:
            keyword_lower = str(keyword).lower()

            # Check short brands with word boundary (must be standalone or followed by space)
            for short_brand in short_brands:
                if re.search(rf'\b{short_brand}\b', keyword_lower):
                    brand_keywords.add(keyword)
                    break

            # Check all other brands (substring match)
            if keyword not in brand_keywords:
                for brand in all_brands:
                    if brand.lower() not in short_brands and brand.lower() in keyword_lower:
                        brand_keywords.add(keyword)
                        break

        self.brand_keywords = brand_keywords
        self.cleaning_logs.append(f"✓ Detected {len(brand_keywords)} brand keywords")
        return brand_keywords

    def detect_international_keywords(self, df: pd.DataFrame, target_country: str = "nz") -> Set[str]:
        """Detect keywords with country references (excluding target country)"""
        international_keywords = set()

        # Country patterns (excluding target)
        country_patterns = [
            r'\busa?\b', r'\buk\b', r'\baustralia\b', r'\baus\b', r'\bau\b',
            r'\bcanada\b', r'\beurope\b', r'\bafrica\b', r'\basia\b',
            r'\bindia\b', r'\bchina\b', r'\bjapan\b', r'\bsouth africa\b'
        ]

        # Currency conversion patterns
        currency_patterns = [
            # ANY keyword containing "X to nz/nzd" or "X to Y" where X or Y is currency
            r'\bto\s+(nz|nzd)\b',  # Anything "to nz" or "to nzd"
            r'\b(us|au|uk|usd|aud|gbp|eur)\s+to\b',  # Currency "to" anything
            # Specific conversions
            r'(usd|aud|gbp|eur)\s+(to|into|in)\s+(nzd|nz)',
            r'(us|au)\s+(to|into|in)\s+(nz|nzd)',
            # With numbers
            r'\d+\s+(usd|aud|gbp|eur|us|au)\s+(to|into|in)',
            # General currency mentions with nzd
            r'\b(usd|aud|gbp)\b.*\bnzd\b'
        ]

        # Exclude target country
        if target_country.lower() == "nz":
            target_patterns = [r'\bnz\b', r'\bnew zealand\b']
        else:
            target_patterns = [target_country.lower()]

        for keyword in df['keyword']:
            keyword_lower = str(keyword).lower()

            # Check if contains currency conversion
            is_currency_conversion = any(re.search(pattern, keyword_lower) for pattern in currency_patterns)

            # Check if contains international reference
            is_international = any(re.search(pattern, keyword_lower) for pattern in country_patterns)

            # But not if it's about target country
            is_target = any(re.search(pattern, keyword_lower) for pattern in target_patterns)

            if is_currency_conversion or (is_international and not is_target):
                international_keywords.add(keyword)

        self.international_keywords = international_keywords
        self.cleaning_logs.append(f"✓ Detected {len(international_keywords)} international keywords")
        return international_keywords

    def detect_unrelated_keywords(self, df: pd.DataFrame, industry: str = "insurance") -> Set[str]:
        """Detect keywords unrelated to the industry"""
        unrelated_keywords = set()

        # Unrelated patterns by industry
        unrelated_patterns = {
            'insurance': [
                # Financial services (not insurance)
                r'\bretirement\b', r'\bpension\b', r'\bkiwisaver\b',
                r'\bmortgage\b', r'\bloan\b', r'\bcredit card\b',
                # Deposits - match any keyword containing these terms
                r'term deposit', r'fixed deposit', r'time deposit', r'\bdeposit rate',
                r'\bsavings account\b', r'\btransaction account\b',
                # Investments
                r'\binvestment\b', r'\bmanaged fund\b', r'\bmutual fund\b',
                r'\bportfolio\b', r'\bstocks\b', r'\bshares\b', r'\bbonds\b',
                r'\binterest rate\b', r'\bapy\b', r'\byield\b', r'\bdividend'
            ],
            'kiwisaver': [
                r'\binsurance\b', r'\bcar insurance\b', r'\btravel insurance\b',
                r'\bmortgage\b', r'\bloan\b'
            ],
            'managed_funds': [
                r'\binsurance\b', r'\bkiwisaver\b', r'\bmortgage\b'
            ]
        }

        patterns = unrelated_patterns.get(industry.lower(), [])

        for keyword in df['keyword']:
            keyword_lower = str(keyword).lower()
            if any(re.search(pattern, keyword_lower) for pattern in patterns):
                unrelated_keywords.add(keyword)

        self.unrelated_keywords = unrelated_keywords
        self.cleaning_logs.append(f"✓ Detected {len(unrelated_keywords)} unrelated keywords")
        return unrelated_keywords

    def detect_phone_numbers(self, df: pd.DataFrame) -> Set[str]:
        """Detect phone numbers and purely numeric keywords"""
        phone_keywords = set()

        for keyword in df['keyword']:
            keyword_str = str(keyword).strip()
            keyword_lower = keyword_str.lower()

            # Pattern 1: Pure numbers only (no text at all)
            if re.match(r'^\d+$', keyword_str):
                phone_keywords.add(keyword)
                continue

            # Pattern 2: Keywords starting with phone patterns (e.g., "0800 contact", "0800 damage", "1300 anything")
            if re.match(r'^(1300|0800|0508|0064)\s+\w+', keyword_str):
                phone_keywords.add(keyword)
                continue

            # Pattern 2b: Phone-specific patterns with phone/number/code/call keywords
            # e.g., "1300 phone number", "0064 country code", "1300 phone numbers"
            if re.search(r'\b(phone|number|code|call|contact)\b', keyword_lower):
                # Check if it starts with typical phone patterns
                if re.match(r'^(1300|0800|0508|0\d{3}|\+?\d{2,4})', keyword_str):
                    phone_keywords.add(keyword)
                    continue
                # Or contains long number sequences with phone keywords
                if re.search(r'\d{7,}', keyword_str):
                    phone_keywords.add(keyword)
                    continue

            # Pattern 3: Standard phone formats without spaces
            # e.g., "1300300273" (10 digits no spaces)
            if re.match(r'^(1300|0800|0\d)\d{6,}$', keyword_str):
                phone_keywords.add(keyword)
                continue

            # Pattern 4: Phone formats WITH spaces
            # e.g., "1300 300 273", "1300 650 286", "0800 123 456"
            # Remove spaces and check if it's purely numeric phone format
            no_spaces = keyword_str.replace(' ', '')
            if re.match(r'^(1300|0800|0\d)\d{6,}$', no_spaces):
                phone_keywords.add(keyword)
                continue

            # Pattern 5: International formats
            # e.g., "+64 9 123 4567", "0064 9 123"
            if re.match(r'^(\+|00)\d{2,4}\s*\d', keyword_str):
                phone_keywords.add(keyword)
                continue

        self.phone_number_keywords = phone_keywords
        self.cleaning_logs.append(f"✓ Detected {len(phone_keywords)} phone number keywords")
        return phone_keywords

    def detect_junk_keywords(self, df: pd.DataFrame) -> Set[str]:
        """Detect junk keywords (URLs, domains, fragments)"""
        junk_keywords = set()

        for keyword in df['keyword']:
            keyword_str = str(keyword).strip()
            keyword_lower = keyword_str.lower()

            # Pattern 1: Starts with www or http/https
            if re.match(r'^(www\.|https?://)', keyword_lower):
                junk_keywords.add(keyword)
                continue

            # Pattern 2: Just "www" or domain extensions
            if re.match(r'^(www|co\.nz|com\.au|\.nz|\.com|\.au)$', keyword_lower):
                junk_keywords.add(keyword)
                continue

            # Pattern 3: Contains multiple dots (likely domain)
            if keyword_str.count('.') >= 2:
                junk_keywords.add(keyword)
                continue

            # Pattern 4: Ends with domain extensions
            if re.search(r'\.(co\.nz|com\.au|com|net|org|nz|au)$', keyword_lower):
                junk_keywords.add(keyword)
                continue

            # Pattern 5: Rental/Backpacker/Travel-specific insurance patterns (niche products, not main insurance)
            if re.search(r'\b(rental|hire)\s+(car|vehicle)\s+insurance\b', keyword_lower):
                junk_keywords.add(keyword)
                continue
            if re.search(r'\bcar\s+(rental|hire)\s+insurance\b', keyword_lower):
                junk_keywords.add(keyword)
                continue
            if re.search(r'\bbackpacker\s+(car\s+)?insurance\b', keyword_lower):
                junk_keywords.add(keyword)
                continue

            # Pattern 6: Pure price/currency patterns ($500, 100 nzd, etc.)
            if re.match(r'^\$?\d+(\.\d{2})?\s*(nzd|usd|aud|dollars?)?$', keyword_lower):
                junk_keywords.add(keyword)
                continue
            # Also catch dollar sign + space + number
            if re.match(r'^\$\s*\d+', keyword_str):
                junk_keywords.add(keyword)
                continue

        if not hasattr(self, 'junk_keywords'):
            self.junk_keywords = junk_keywords
        else:
            self.junk_keywords.update(junk_keywords)

        self.cleaning_logs.append(f"✓ Detected {len(junk_keywords)} junk/URL keywords")
        return junk_keywords

    def filter_keywords(self,
                       df: pd.DataFrame,
                       remove_brand: bool = True,
                       remove_international: bool = True,
                       remove_unrelated: bool = True,
                       remove_phone_numbers: bool = True,
                       remove_junk: bool = True) -> pd.DataFrame:
        """Filter keywords based on detection results"""

        initial_count = len(df)
        filtered_df = df.copy()

        keywords_to_remove = set()

        if remove_brand:
            keywords_to_remove.update(self.brand_keywords)

        if remove_international:
            keywords_to_remove.update(self.international_keywords)

        if remove_unrelated:
            keywords_to_remove.update(self.unrelated_keywords)

        if remove_phone_numbers:
            keywords_to_remove.update(self.phone_number_keywords)

        if remove_junk:
            keywords_to_remove.update(self.junk_keywords)

        # Filter out unwanted keywords
        filtered_df = filtered_df[~filtered_df['keyword'].isin(keywords_to_remove)]

        final_count = len(filtered_df)
        removed_count = initial_count - final_count

        self.cleaning_logs.append(f"✓ Filtered dataset: {initial_count} → {final_count} keywords ({removed_count} removed)")

        return filtered_df

    def create_filtered_subsets(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Create separate dataframes for each filtered category"""
        subsets = {}

        if self.brand_keywords:
            subsets['brand'] = df[df['keyword'].isin(self.brand_keywords)]

        if self.international_keywords:
            subsets['international'] = df[df['keyword'].isin(self.international_keywords)]

        if self.unrelated_keywords:
            subsets['unrelated'] = df[df['keyword'].isin(self.unrelated_keywords)]

        if self.phone_number_keywords:
            subsets['phone_numbers'] = df[df['keyword'].isin(self.phone_number_keywords)]

        return subsets

    def get_cleaning_summary(self) -> Dict:
        """Get summary statistics of cleaning operation"""
        return {
            'brand_count': len(self.brand_keywords),
            'international_count': len(self.international_keywords),
            'unrelated_count': len(self.unrelated_keywords),
            'phone_number_count': len(self.phone_number_keywords),
            'total_filtered': len(self.brand_keywords) + len(self.international_keywords) + len(self.unrelated_keywords) + len(self.phone_number_keywords),
            'logs': self.cleaning_logs
        }

    def reset(self):
        """Reset cleaning state"""
        self.cleaning_logs = []
        self.brand_keywords = set()
        self.international_keywords = set()
        self.unrelated_keywords = set()
        self.phone_number_keywords = set()
