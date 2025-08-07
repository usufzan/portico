#!/usr/bin/env python3
"""
Shared Workflow Utilities

Centralizes workflow logic and reduces duplication across the scraping process.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from enum import Enum

class WorkflowStage(Enum):
    INITIALIZATION = "initialization"
    FAST_PATH = "fast_path"
    ROBUST_PATH = "robust_path"
    NAVIGATION = "navigation"
    CONTENT_EXTRACTION = "content_extraction"
    METADATA_EXTRACTION = "metadata_extraction"
    VALIDATION = "validation"
    COMPLETION = "completion"

@dataclass
class WorkflowOutput:
    status: str
    stage: str
    total_stages: int
    current_stage: int
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    performance_metrics: Dict[str, float] = None

class WorkflowManager:
    """Manages workflow stages and output generation."""
    
    def __init__(self, total_stages: int = 6, logger: Optional[logging.Logger] = None):
        self.total_stages = total_stages
        self.current_stage = 0
        self.start_time = None
        self.logger = logger or logging.getLogger(__name__)
    
    def start_workflow(self):
        """Initialize workflow timing."""
        self.start_time = asyncio.get_event_loop().time()
        self.current_stage = 0
    
    def next_stage(self) -> int:
        """Advance to next stage and return stage number."""
        self.current_stage += 1
        return self.current_stage
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics."""
        if self.start_time is None:
            return {"total_elapsed_time_seconds": 0.0, "timestamp": 0.0}
        
        elapsed_time = asyncio.get_event_loop().time() - self.start_time
        return {
            "total_elapsed_time_seconds": elapsed_time,
            "timestamp": self.start_time
        }
    
    def create_output(
        self,
        status: str,
        stage: WorkflowStage,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> WorkflowOutput:
        """Create consistent workflow output."""
        return WorkflowOutput(
            status=status,
            stage=stage.value,
            total_stages=self.total_stages,
            current_stage=self.current_stage,
            message=message,
            data=data,
            error=error,
            performance_metrics=self.get_performance_metrics()
        )
    
    def yield_progress(
        self,
        stage: WorkflowStage,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> WorkflowOutput:
        """Yield a progress update."""
        return self.create_output("progress", stage, message, data)
    
    def yield_complete(
        self,
        data: Dict[str, Any],
        message: str = "Scraping completed successfully"
    ) -> WorkflowOutput:
        """Yield a completion update."""
        return self.create_output("complete", WorkflowStage.COMPLETION, message, data)
    
    def yield_error(
        self,
        stage: WorkflowStage,
        error: str,
        message: str = "An error occurred"
    ) -> WorkflowOutput:
        """Yield an error update."""
        return self.create_output("error", stage, message, error=error)

def validate_url(url: str) -> bool:
    """Validate URL format."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False

def create_error_response(error: str, stage: str = "unknown") -> Dict[str, Any]:
    """Create standardized error response."""
    return {
        "status": "error",
        "stage": stage,
        "message": f"An error occurred: {error}",
        "current_stage": 0,
        "total_stages": 6
    }
