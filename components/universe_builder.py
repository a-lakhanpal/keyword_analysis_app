"""
Universe Builder Component
Creates the master keyword universe by merging all data sources
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import streamlit as st

class UniverseBuilder:
    """Build comprehensive keyword universe"""

    def __init__(self, brand_name: str = 'brand'):
        self.universe = None
        self.build_logs = []
        self.brand_name = brand_name

    def create_early_universe(self,
                            main_keywords: pd.DataFrame,
                            brand_rankings: Optional[pd.DataFrame] = None,
                            competitors: Optional[Dict[str, pd.DataFrame]] = None) -> pd.DataFrame:
        """Create early universe (before AI classification)"""

        self.build_logs.append(f"✓ Starting with {len(main_keywords)} main keywords")

        # Start with main keywords
        universe = main_keywords.copy()

        # Merge brand rankings
        if brand_rankings is not None:
            universe = self._merge_brand_rankings(universe, brand_rankings)

        # Merge competitor data
        if competitors:
            universe = self._merge_competitors(universe, competitors)

        self.universe = universe
        self.build_logs.append(f"✓ Early universe created: {len(universe)} total keywords")

        return universe

    def create_final_universe(self,
                            classified_keywords: pd.DataFrame,
                            brand_rankings: Optional[pd.DataFrame] = None,
                            competitors: Optional[Dict[str, pd.DataFrame]] = None) -> pd.DataFrame:
        """Create final universe (after AI classification)"""

        self.build_logs.append(f"✓ Starting with {len(classified_keywords)} classified keywords")

        # Start with classified keywords
        universe = classified_keywords.copy()

        # Merge brand rankings
        if brand_rankings is not None:
            universe = self._merge_brand_rankings(universe, brand_rankings)

        # Merge competitor data
        if competitors:
            universe = self._merge_competitors(universe, competitors)

        # Calculate business metrics
        universe = self._calculate_business_value(universe)
        universe = self._calculate_opportunity_scores(universe)

        self.universe = universe
        self.build_logs.append(f"✓ Final universe created: {len(universe)} total keywords")

        return universe

    def _merge_brand_rankings(self, universe: pd.DataFrame, brand_rankings: pd.DataFrame) -> pd.DataFrame:
        """Merge brand ranking data"""

        # Ensure 'keyword' column exists
        if 'keyword' not in brand_rankings.columns:
            self.build_logs.append(f"⚠ {self.brand_name} rankings missing 'keyword' column, skipping")
            return universe

        # Prepare brand columns - include search_volume, cpc, difficulty to fill gaps
        brand_cols = ['keyword', 'position', 'url', 'traffic', 'traffic_cost', 'search_volume', 'cpc', 'difficulty']
        brand_cols = [col for col in brand_cols if col in brand_rankings.columns]

        brand_data = brand_rankings[brand_cols].copy()

        # Separate ranking columns from keyword data columns
        ranking_cols = ['position', 'url', 'traffic', 'traffic_cost']
        data_cols = ['search_volume', 'cpc', 'difficulty']

        # Rename ranking columns with brand prefix
        safe_brand = self.brand_name.lower().replace(' ', '_')
        rename_map = {col: f'{safe_brand}_{col}' for col in brand_data.columns if col in ranking_cols}
        brand_data = brand_data.rename(columns=rename_map)

        # Merge - use outer to include ALL keywords from both main and brand
        # Note: This will create _x and _y suffixes for duplicate columns
        universe = pd.merge(universe, brand_data, on='keyword', how='outer')

        # Coalesce _x and _y columns: prefer _x (main file), fallback to _y (brand file)
        for col in data_cols:
            col_x = f'{col}_x'
            col_y = f'{col}_y'

            if col_x in universe.columns and col_y in universe.columns:
                # Combine: use _x if exists, otherwise use _y
                universe[col] = universe[col_x].fillna(universe[col_y])
                # Drop the suffixed columns
                universe = universe.drop([col_x, col_y], axis=1)
            elif col_x in universe.columns:
                # Only _x exists (rename it)
                universe[col] = universe[col_x]
                universe = universe.drop([col_x], axis=1)
            elif col_y in universe.columns:
                # Only _y exists (rename it)
                universe[col] = universe[col_y]
                universe = universe.drop([col_y], axis=1)

        brand_count = universe[f'{safe_brand}_position'].notna().sum() if f'{safe_brand}_position' in universe.columns else 0
        self.build_logs.append(f"✓ Merged {self.brand_name} rankings: {brand_count} keywords with {self.brand_name} data")

        return universe

    def _merge_competitors(self, universe: pd.DataFrame, competitors: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Merge competitor ranking data"""

        for comp_name, comp_df in competitors.items():
            if 'keyword' not in comp_df.columns:
                self.build_logs.append(f"⚠ {comp_name} missing 'keyword' column, skipping")
                continue

            # Prepare competitor columns - include search_volume, cpc, difficulty to fill gaps
            comp_cols = ['keyword', 'position', 'url', 'traffic', 'traffic_cost', 'search_volume', 'cpc', 'difficulty']
            comp_cols = [col for col in comp_cols if col in comp_df.columns]

            comp_data = comp_df[comp_cols].copy()

            # Separate ranking columns from keyword data columns
            ranking_cols = ['position', 'url', 'traffic', 'traffic_cost']
            data_cols = ['search_volume', 'cpc', 'difficulty']

            # Rename ranking columns with competitor prefix
            safe_name = comp_name.lower().replace(' ', '_')
            rename_map = {col: f'{safe_name}_{col}' for col in comp_data.columns if col in ranking_cols}
            comp_data = comp_data.rename(columns=rename_map)

            # Merge - use outer to include ALL keywords from universe and competitor
            # Note: This will create _x and _y suffixes for duplicate columns
            universe = pd.merge(universe, comp_data, on='keyword', how='outer')

            # Coalesce _x and _y columns: prefer _x (existing data), fallback to _y (competitor data)
            for col in data_cols:
                col_x = f'{col}_x'
                col_y = f'{col}_y'

                if col_x in universe.columns and col_y in universe.columns:
                    # Combine: use _x if exists, otherwise use _y
                    universe[col] = universe[col_x].fillna(universe[col_y])
                    # Drop the suffixed columns
                    universe = universe.drop([col_x, col_y], axis=1)
                elif col_x in universe.columns:
                    # Only _x exists (rename it)
                    universe[col] = universe[col_x]
                    universe = universe.drop([col_x], axis=1)
                elif col_y in universe.columns:
                    # Only _y exists (rename it)
                    universe[col] = universe[col_y]
                    universe = universe.drop([col_y], axis=1)

            comp_count = universe[f'{safe_name}_position'].notna().sum() if f'{safe_name}_position' in universe.columns else 0
            self.build_logs.append(f"✓ Merged {comp_name}: {comp_count} keywords with {comp_name} data")

        return universe

    def _get_journey_weight(self, phase: str) -> float:
        """Get journey weight with intelligent fallback for any industry"""
        if pd.isna(phase):
            return 0.5

        phase_str = str(phase).upper()

        # Exact matches first (for known phases)
        exact_weights = {
            'UNAWARE': 0.3,
            'AWARE': 0.5,
            'AWARE_NOT_INSURED': 0.8,
            'AWARE_NOT_JOINED': 0.8,
            'RESEARCH': 0.6,
            'RESEARCHING': 0.6,
            'COMPARISON': 0.9,
            'COMPARING': 0.9,
            'DECISION': 1.0,
            'NEW_MEMBER': 0.7,
            'MEMBER': 0.7,
            'NEW_CUSTOMER': 0.5,
            'ESTABLISHED_MEMBER': 0.6,
            'ACTIVE_MEMBER': 0.8,
            'POLICY_HOLDER': 0.4,
            'RENEWAL': 0.7,
            'LIFE_EVENT': 0.6
        }

        if phase_str in exact_weights:
            return exact_weights[phase_str]

        # Pattern matching for unknown phases (works for any industry)
        phase_lower = phase_str.lower()

        if 'unaware' in phase_lower:
            return 0.3
        elif any(word in phase_lower for word in ['aware', 'learning', 'discover']):
            return 0.5
        elif any(word in phase_lower for word in ['research', 'browse', 'consider', 'evaluat']):
            return 0.6
        elif any(word in phase_lower for word in ['compar', 'shortlist', 'assess']):
            return 0.9
        elif any(word in phase_lower for word in ['decision', 'checkout', 'purchase', 'buy', 'trial']):
            return 1.0
        elif any(word in phase_lower for word in ['customer', 'member', 'holder', 'user', 'subscriber']):
            return 0.6
        elif any(word in phase_lower for word in ['renewal', 'retain', 'expansion']):
            return 0.7
        elif any(word in phase_lower for word in ['advocate', 'power', 'experienced']):
            return 0.8
        else:
            return 0.5

    def _get_intent_weight(self, intent: str) -> float:
        """Get intent weight with intelligent fallback"""
        if pd.isna(intent):
            return 0.5

        intent_str = str(intent).upper()

        # Exact matches
        exact_weights = {
            'TRANSACTIONAL': 1.0,
            'COMMERCIAL': 0.9,
            'COMPARISON': 0.8,
            'NAVIGATIONAL': 0.7,
            'INFORMATIONAL': 0.5
        }

        if intent_str in exact_weights:
            return exact_weights[intent_str]

        # Pattern matching
        intent_lower = intent_str.lower()

        if any(word in intent_lower for word in ['transact', 'buy', 'purchase', 'checkout']):
            return 1.0
        elif any(word in intent_lower for word in ['commercial', 'comparison', 'compare']):
            return 0.9
        elif any(word in intent_lower for word in ['navigat', 'brand']):
            return 0.7
        else:
            return 0.5

    def _calculate_business_value(self, universe: pd.DataFrame) -> pd.DataFrame:
        """Calculate business value scores"""

        if 'search_volume' not in universe.columns or 'cpc' not in universe.columns:
            self.build_logs.append("⚠ Missing search_volume or cpc, skipping business value calculation")
            return universe

        # Apply weights using intelligent functions
        if 'journey_phase' in universe.columns:
            universe['journey_weight'] = universe['journey_phase'].apply(self._get_journey_weight)
        else:
            universe['journey_weight'] = 0.5

        if 'search_intent' in universe.columns:
            universe['intent_weight'] = universe['search_intent'].apply(self._get_intent_weight)
        else:
            universe['intent_weight'] = 0.5

        # Calculate business value
        universe['business_value'] = (
            universe['search_volume'].fillna(0) *
            universe['cpc'].fillna(0) *
            universe['journey_weight'] *
            universe['intent_weight']
        )

        self.build_logs.append("✓ Calculated business values")

        return universe

    def _calculate_opportunity_scores(self, universe: pd.DataFrame) -> pd.DataFrame:
        """Calculate opportunity scores based on gaps"""

        # Find brand position column
        safe_brand = self.brand_name.lower().replace(' ', '_')
        brand_pos_col = f'{safe_brand}_position'

        # Calculate opportunity gap (not ranking but competitors are)
        competitor_cols = [col for col in universe.columns if col.endswith('_position') and col != brand_pos_col]

        if brand_pos_col in universe.columns and competitor_cols:
            # Not ranking (brand_position is NaN) but competitors are
            universe['competitors_ranking'] = universe[competitor_cols].notna().sum(axis=1)
            universe['opportunity_gap'] = (
                (universe[brand_pos_col].isna()) &
                (universe['competitors_ranking'] > 0)
            ).astype(int)

            gap_count = universe['opportunity_gap'].sum()
            self.build_logs.append(f"✓ Identified {gap_count} opportunity gaps")
        else:
            universe['opportunity_gap'] = 0
            universe['competitors_ranking'] = 0

        # Calculate opportunity score
        if 'business_value' in universe.columns and 'difficulty' in universe.columns:
            # Higher value, lower difficulty, higher gap = better opportunity
            universe['opportunity_score'] = (
                (universe['business_value'].fillna(0) / universe['business_value'].max()) * 0.5 +
                ((100 - universe['difficulty'].fillna(50)) / 100) * 0.3 +
                (universe['opportunity_gap'] * 0.2)
            ) * 100

            self.build_logs.append("✓ Calculated opportunity scores")

        return universe

    def create_subsets(self, universe: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Create analysis subsets from universe"""

        subsets = {}

        # Top opportunities
        if 'opportunity_score' in universe.columns:
            subsets['top_opportunities'] = universe.nlargest(200, 'opportunity_score')
            self.build_logs.append(f"✓ Created top 200 opportunities subset")

        # High value keywords
        if 'business_value' in universe.columns:
            high_value = universe[universe['business_value'] > universe['business_value'].quantile(0.75)]
            subsets['high_value'] = high_value
            self.build_logs.append(f"✓ Created high value subset: {len(high_value)} keywords")

        # Journey phase breakdown
        if 'journey_phase' in universe.columns:
            journey_summary = universe.groupby('journey_phase').agg({
                'keyword': 'count',
                'search_volume': 'sum',
                'business_value': 'sum'
            }).reset_index()
            journey_summary.columns = ['journey_phase', 'keyword_count', 'total_volume', 'total_value']
            subsets['journey_breakdown'] = journey_summary
            self.build_logs.append(f"✓ Created journey phase breakdown")

        # Brand analysis
        brand_analysis = self._create_brand_analysis(universe)
        if brand_analysis is not None:
            subsets['brand_analysis'] = brand_analysis
            self.build_logs.append(f"✓ Created brand analysis")

        # Business insights
        business_insights = self._create_business_insights(universe)
        if business_insights is not None:
            subsets['business_insights'] = business_insights
            self.build_logs.append(f"✓ Created business insights")

        # Low hanging fruit (position 4-15)
        safe_brand = self.brand_name.lower().replace(' ', '_')
        brand_pos_col = f'{safe_brand}_position'
        if brand_pos_col in universe.columns:
            low_hanging = universe[
                (universe[brand_pos_col] >= 4) &
                (universe[brand_pos_col] <= 15)
            ].copy()
            if len(low_hanging) > 0:
                # Sort by position (best first) then by search volume if available
                if 'search_volume' in low_hanging.columns:
                    low_hanging = low_hanging.sort_values([brand_pos_col, 'search_volume'], ascending=[True, False])
                else:
                    low_hanging = low_hanging.sort_values([brand_pos_col], ascending=[True])
                subsets['low_hanging_fruit'] = low_hanging
                self.build_logs.append(f"✓ Created low hanging fruit subset: {len(low_hanging)} keywords")

        # High volume, low competition (difficulty ≤ 10, volume ≥ 500)
        if 'difficulty' in universe.columns and 'search_volume' in universe.columns:
            high_vol_low_comp = universe[
                (universe['difficulty'] <= 10) &
                (universe['search_volume'] >= 500)
            ].copy()
            if len(high_vol_low_comp) > 0:
                # Sort by volume descending
                high_vol_low_comp = high_vol_low_comp.sort_values('search_volume', ascending=False)
                subsets['high_volume_low_competition'] = high_vol_low_comp
                self.build_logs.append(f"✓ Created high volume low competition subset: {len(high_vol_low_comp)} keywords")

        # Newly discovered (first seen within last 3 months)
        if 'first_seen' in universe.columns:
            import pandas as pd
            from datetime import datetime, timedelta

            # Convert first_seen to datetime if it's not already
            universe['first_seen_dt'] = pd.to_datetime(universe['first_seen'], errors='coerce')

            # Calculate 3 months ago
            three_months_ago = datetime.now() - timedelta(days=90)

            newly_discovered = universe[
                universe['first_seen_dt'] >= three_months_ago
            ].copy()

            if len(newly_discovered) > 0:
                # Sort by first seen (newest first) then by volume
                if 'search_volume' in newly_discovered.columns:
                    newly_discovered = newly_discovered.sort_values(['first_seen_dt', 'search_volume'], ascending=[False, False])

                # Drop the temporary datetime column
                newly_discovered = newly_discovered.drop('first_seen_dt', axis=1)

                subsets['newly_discovered'] = newly_discovered
                self.build_logs.append(f"✓ Created newly discovered subset: {len(newly_discovered)} keywords")

        return subsets

    def _create_brand_analysis(self, universe: pd.DataFrame) -> pd.DataFrame:
        """Create brand analysis showing each brand's performance across journey phases"""

        # Find all brand position columns
        position_cols = [col for col in universe.columns if col.endswith('_position')]

        if not position_cols:
            return None

        brand_data = []

        for pos_col in position_cols:
            brand_name = pos_col.replace('_position', '')

            # Get keywords where this brand ranks
            brand_keywords = universe[universe[pos_col].notna()]

            if len(brand_keywords) == 0:
                continue

            # Calculate metrics
            row = {
                'Brand_Name': brand_name,
                'Total_Keywords_Ranking': len(brand_keywords),
                'Avg_Position': brand_keywords[pos_col].mean(),
            }

            # Add traffic and cost if available
            traffic_col = f'{brand_name}_traffic'
            cost_col = f'{brand_name}_traffic_cost'

            if traffic_col in universe.columns:
                row['Total_Traffic'] = brand_keywords[traffic_col].sum()

            if cost_col in universe.columns:
                row['Total_Traffic_Cost'] = brand_keywords[cost_col].sum()

            # Add CPC if available
            if 'cpc' in brand_keywords.columns:
                row['Avg_CPC'] = brand_keywords['cpc'].mean()

            # Journey phase breakdown
            if 'journey_phase' in brand_keywords.columns:
                phase_counts = brand_keywords['journey_phase'].value_counts()
                for phase, count in phase_counts.items():
                    row[f'{phase}_count'] = count

            brand_data.append(row)

        if not brand_data:
            return None

        return pd.DataFrame(brand_data)

    def _create_business_insights(self, universe: pd.DataFrame) -> pd.DataFrame:
        """Create business insights summary"""

        insights = []

        # Summary statistics
        insights.append({
            'Category': 'Summary',
            'Metric': 'Total_Keywords',
            'Value': f"{len(universe):,}",
            'Business_Impact': 'Complete market coverage'
        })

        if 'journey_phase' in universe.columns:
            classified = universe['journey_phase'].notna().sum()
            insights.append({
                'Category': 'Summary',
                'Metric': 'Classified_Keywords',
                'Value': f"{classified:,}",
                'Business_Impact': f'{classified/len(universe)*100:.1f}% of keywords classified'
            })

        if 'business_value' in universe.columns:
            total_value = universe['business_value'].sum()
            insights.append({
                'Category': 'Summary',
                'Metric': 'Total_Business_Value',
                'Value': f"${total_value:,.0f}",
                'Business_Impact': 'Estimated monthly revenue opportunity'
            })

        # Top opportunities
        if 'opportunity_score' in universe.columns:
            top_opps = universe.nlargest(5, 'opportunity_score')
            for idx, (_, row) in enumerate(top_opps.iterrows(), 1):
                value = row.get('business_value', 0)
                volume = row.get('search_volume', 0)
                insights.append({
                    'Category': 'Top_Opportunities',
                    'Metric': f'Opportunity_{idx:02d}',
                    'Value': row['keyword'],
                    'Business_Impact': f"${value:.0f} value, {volume:,.0f} searches"
                })

        # Journey phase insights
        if 'journey_phase' in universe.columns and 'business_value' in universe.columns:
            phase_values = universe.groupby('journey_phase')['business_value'].sum().nlargest(3)
            for phase, value in phase_values.items():
                insights.append({
                    'Category': 'Journey_Insights',
                    'Metric': f'{phase}_Phase',
                    'Value': f"${value:,.0f}",
                    'Business_Impact': f'Highest value journey phase'
                })

        return pd.DataFrame(insights)

    def extract_serp_features(self, universe: pd.DataFrame) -> Dict[str, Dict]:
        """Extract all unique SERP features with their keyword counts and metrics"""

        if 'serp_features' not in universe.columns:
            return {}

        # Parse all SERP features
        all_features = {}

        for idx, row in universe.iterrows():
            serp_value = row.get('serp_features')

            if pd.isna(serp_value) or serp_value == '':
                continue

            # Split by comma and clean each feature
            features = [f.strip() for f in str(serp_value).split(',')]

            for feature in features:
                if not feature:
                    continue

                if feature not in all_features:
                    all_features[feature] = {
                        'count': 0,
                        'total_volume': 0,
                        'total_value': 0
                    }

                all_features[feature]['count'] += 1

                # Add volume if available
                if 'search_volume' in universe.columns:
                    volume = row.get('search_volume', 0)
                    if not pd.isna(volume):
                        all_features[feature]['total_volume'] += volume

                # Add business value if available
                if 'business_value' in universe.columns:
                    value = row.get('business_value', 0)
                    if not pd.isna(value):
                        all_features[feature]['total_value'] += value

        return all_features

    def create_serp_feature_files(self, universe: pd.DataFrame, selected_features: list) -> Dict[str, pd.DataFrame]:
        """Create separate DataFrames for each selected SERP feature"""

        if 'serp_features' not in universe.columns:
            return {}

        serp_files = {}

        for feature in selected_features:
            # Find all keywords that have this SERP feature
            mask = universe['serp_features'].apply(
                lambda x: feature in str(x) if not pd.isna(x) else False
            )

            feature_df = universe[mask].copy()

            if len(feature_df) > 0:
                # Clean feature name for filename
                safe_feature_name = feature.lower().replace(' ', '_').replace('/', '_')
                serp_files[safe_feature_name] = feature_df
                self.build_logs.append(f"✓ Created {feature} file: {len(feature_df)} keywords")

        # Create summary of all SERP features
        feature_stats = self.extract_serp_features(universe)

        if feature_stats:
            summary_data = []
            for feature, stats in feature_stats.items():
                summary_data.append({
                    'SERP_Feature': feature,
                    'Keyword_Count': stats['count'],
                    'Total_Search_Volume': stats['total_volume'],
                    'Total_Business_Value': stats['total_value']
                })

            summary_df = pd.DataFrame(summary_data)
            summary_df = summary_df.sort_values('Keyword_Count', ascending=False)
            serp_files['serp_features_summary'] = summary_df
            self.build_logs.append(f"✓ Created SERP features summary")

        return serp_files

    def get_universe_stats(self) -> Dict:
        """Get statistics about the universe"""

        if self.universe is None:
            return {}

        stats = {
            'total_keywords': len(self.universe),
            'columns': len(self.universe.columns),
            'size_kb': self.universe.memory_usage(deep=True).sum() / 1024
        }

        if 'journey_phase' in self.universe.columns:
            stats['classified_keywords'] = self.universe['journey_phase'].notna().sum()

        # Find brand position column
        safe_brand = self.brand_name.lower().replace(' ', '_')
        brand_pos_col = f'{safe_brand}_position'

        if brand_pos_col in self.universe.columns:
            stats['brand_ranking_keywords'] = self.universe[brand_pos_col].notna().sum()

        if 'business_value' in self.universe.columns:
            stats['total_business_value'] = self.universe['business_value'].sum()

        competitor_cols = [col for col in self.universe.columns if col.endswith('_position') and col != brand_pos_col]
        if competitor_cols:
            stats['competitor_data_keywords'] = self.universe[competitor_cols].notna().any(axis=1).sum()

        stats['logs'] = self.build_logs

        return stats
