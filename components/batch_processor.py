"""
OpenAI Batch Processor Component
Handles batch submission and monitoring
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import streamlit as st
from openai import OpenAI
import os

class BatchProcessor:
    """Handle OpenAI Batch API operations"""

    def __init__(self, api_key: str, industry: str = "insurance"):
        self.client = OpenAI(api_key=api_key)
        self.industry = industry
        self.batch_id = None

    def prepare_batch_file(self, df: pd.DataFrame, journey_phases: list, intent_types: list, output_dir: str = "batches") -> str:
        """Create JSONL file for batch processing"""

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        jsonl_file = output_path / f"batch_{timestamp}.jsonl"

        # Prepare batch requests
        batch_requests = []

        for idx, row in df.iterrows():
            keyword = row['keyword']

            # Build classification prompt
            prompt = self._build_classification_prompt(keyword, journey_phases, intent_types)

            request = {
                "custom_id": f"request-{idx}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are an expert at classifying search keywords for customer journey analysis."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 150,
                    "temperature": 0.3
                }
            }
            batch_requests.append(request)

        # Write JSONL file
        with open(jsonl_file, 'w') as f:
            for request in batch_requests:
                f.write(json.dumps(request) + '\n')

        return str(jsonl_file)

    def _build_classification_prompt(self, keyword: str, journey_phases: list, intent_types: list) -> str:
        """Build classification prompt for a keyword"""

        prompt = f"""Classify this search keyword: "{keyword}"

Industry: {self.industry.upper()}

Classify into:

1. JOURNEY PHASE (choose one):
{chr(10).join(f'   - {phase}' for phase in journey_phases)}

2. SEARCH INTENT (choose one):
{chr(10).join(f'   - {intent}' for intent in intent_types)}

Respond ONLY with valid JSON format:
{{"journey_phase": "PHASE_NAME", "search_intent": "INTENT_NAME"}}

No explanation, just JSON."""

        return prompt

    def submit_batch(self, jsonl_file: str) -> str:
        """Submit batch to OpenAI"""

        try:
            # Upload file
            with open(jsonl_file, 'rb') as f:
                batch_input_file = self.client.files.create(
                    file=f,
                    purpose="batch"
                )

            # Create batch
            batch = self.client.batches.create(
                input_file_id=batch_input_file.id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
                metadata={
                    "description": f"{self.industry} keyword classification"
                }
            )

            self.batch_id = batch.id
            return batch.id

        except Exception as e:
            st.error(f"Failed to submit batch: {e}")
            return None

    def get_batch_status(self, batch_id: Optional[str] = None) -> Dict:
        """Get status of batch processing"""

        if batch_id is None:
            batch_id = self.batch_id

        if not batch_id:
            return {'status': 'no_batch'}

        try:
            batch = self.client.batches.retrieve(batch_id)

            return {
                'status': batch.status,
                'id': batch.id,
                'request_counts': {
                    'total': batch.request_counts.total,
                    'completed': batch.request_counts.completed,
                    'failed': batch.request_counts.failed
                },
                'created_at': batch.created_at,
                'completed_at': batch.completed_at if hasattr(batch, 'completed_at') else None,
                'output_file_id': batch.output_file_id if hasattr(batch, 'output_file_id') else None,
                'error_file_id': batch.error_file_id if hasattr(batch, 'error_file_id') else None
            }

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def retrieve_results(self, batch_id: Optional[str] = None, output_dir: str = "batches/results") -> Optional[str]:
        """Download and save batch results"""

        if batch_id is None:
            batch_id = self.batch_id

        if not batch_id:
            return None

        try:
            status = self.get_batch_status(batch_id)

            if status['status'] != 'completed':
                st.warning(f"Batch not completed yet. Current status: {status['status']}")
                return None

            # Download results
            output_file_id = status.get('output_file_id')
            if not output_file_id:
                st.error("No output file available")
                return None

            file_response = self.client.files.content(output_file_id)

            # Save to file
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True, parents=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_file = output_path / f"batch_results_{timestamp}.jsonl"

            with open(result_file, 'wb') as f:
                f.write(file_response.content)

            return str(result_file)

        except Exception as e:
            st.error(f"Failed to retrieve results: {e}")
            return None

    def parse_results(self, results_file: str, original_df: pd.DataFrame) -> pd.DataFrame:
        """Parse batch results and merge with original dataframe"""

        # Read results
        results = []
        with open(results_file, 'r') as f:
            for line in f:
                results.append(json.loads(line))

        # Extract classifications
        classifications = {}

        for result in results:
            try:
                custom_id = result['custom_id']
                idx = int(custom_id.replace('request-', ''))

                response = result['response']['body']['choices'][0]['message']['content']

                # Parse JSON response
                classification = json.loads(response)

                classifications[idx] = {
                    'journey_phase': classification.get('journey_phase'),
                    'search_intent': classification.get('search_intent')
                }

            except Exception as e:
                st.warning(f"Failed to parse result {custom_id}: {e}")
                continue

        # Merge with original dataframe
        classified_df = original_df.copy()
        classified_df['journey_phase'] = None
        classified_df['search_intent'] = None

        for idx, classification in classifications.items():
            if idx < len(classified_df):
                classified_df.at[idx, 'journey_phase'] = classification['journey_phase']
                classified_df.at[idx, 'search_intent'] = classification['search_intent']

        return classified_df

    def estimate_cost(self, num_keywords: int) -> Dict:
        """Estimate batch processing cost"""

        # GPT-4o-mini pricing (batch: 50% discount)
        input_tokens_per_request = 200  # Estimated
        output_tokens_per_request = 30  # Estimated

        total_input_tokens = num_keywords * input_tokens_per_request
        total_output_tokens = num_keywords * output_tokens_per_request

        # Batch pricing (50% off)
        input_cost_per_1m = 0.075  # USD per 1M tokens
        output_cost_per_1m = 0.30  # USD per 1M tokens

        input_cost = (total_input_tokens / 1_000_000) * input_cost_per_1m
        output_cost = (total_output_tokens / 1_000_000) * output_cost_per_1m

        total_cost = input_cost + output_cost

        return {
            'keywords': num_keywords,
            'total_tokens': total_input_tokens + total_output_tokens,
            'estimated_cost_usd': round(total_cost, 4),
            'model': 'gpt-4o-mini (batch)'
        }
