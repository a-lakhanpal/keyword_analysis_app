"""
Progress Tracker Component
Manages progress bars and status updates
"""

import streamlit as st
from typing import Optional

class ProgressTracker:
    """Track and display progress for long-running operations"""

    def __init__(self):
        self.progress_bar = None
        self.status_text = None

    def create(self, label: str = "Processing..."):
        """Create a new progress tracker"""
        self.status_text = st.empty()
        self.progress_bar = st.progress(0)
        self.status_text.text(label)

    def update(self, current: int, total: int, message: str):
        """Update progress"""
        if self.progress_bar is None:
            self.create()

        progress = current / total if total > 0 else 0
        self.progress_bar.progress(progress)
        self.status_text.text(f"{message} ({current}/{total}) - {progress*100:.1f}%")

    def complete(self, message: str = "✅ Complete!"):
        """Mark as complete"""
        if self.progress_bar:
            self.progress_bar.progress(1.0)
        if self.status_text:
            self.status_text.success(message)

    def error(self, message: str):
        """Show error"""
        if self.status_text:
            self.status_text.error(f"❌ {message}")
