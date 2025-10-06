"""
Session Manager Component
Handles saving and resuming sessions
"""

import streamlit as st
import json
from datetime import datetime
from pathlib import Path
import pandas as pd

class SessionManager:
    """Manage session state persistence"""

    def __init__(self, save_dir: str = "sessions"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True)

    def save_session(self, session_state: dict) -> str:
        """Save current session to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"session_{timestamp}.json"
        filepath = self.save_dir / filename

        # Prepare session data (exclude non-serializable objects)
        session_data = {
            'step': session_state.get('step'),
            'settings': session_state.get('settings', {}),
            'column_mappings': session_state.get('column_mappings', {}),
            'batch_id': session_state.get('batch_id'),
            'timestamp': timestamp
        }

        # Save dataframes separately
        if session_state.get('universe_v1') is not None:
            df_path = self.save_dir / f"universe_v1_{timestamp}.csv"
            session_state['universe_v1'].to_csv(df_path, index=False)
            session_data['universe_v1_file'] = str(df_path)

        if session_state.get('universe_master') is not None:
            df_path = self.save_dir / f"universe_master_{timestamp}.csv"
            session_state['universe_master'].to_csv(df_path, index=False)
            session_data['universe_master_file'] = str(df_path)

        # Save JSON
        with open(filepath, 'w') as f:
            json.dump(session_data, f, indent=2)

        return str(filepath)

    def load_session(self, uploaded_file) -> bool:
        """Load session from uploaded JSON file"""
        try:
            session_data = json.load(uploaded_file)

            # Restore session state
            st.session_state.step = session_data.get('step', 1)
            st.session_state.settings = session_data.get('settings', {})
            st.session_state.column_mappings = session_data.get('column_mappings', {})
            st.session_state.batch_id = session_data.get('batch_id')

            # Load dataframes if they exist
            if 'universe_v1_file' in session_data:
                df_path = Path(session_data['universe_v1_file'])
                if df_path.exists():
                    st.session_state.universe_v1 = pd.read_csv(df_path)

            if 'universe_master_file' in session_data:
                df_path = Path(session_data['universe_master_file'])
                if df_path.exists():
                    st.session_state.universe_master = pd.read_csv(df_path)

            return True

        except Exception as e:
            st.error(f"Failed to load session: {e}")
            return False

    def get_session_info(self, session_file: Path) -> dict:
        """Get session metadata"""
        with open(session_file) as f:
            data = json.load(f)

        return {
            'timestamp': data.get('timestamp'),
            'step': data.get('step'),
            'batch_id': data.get('batch_id')
        }
