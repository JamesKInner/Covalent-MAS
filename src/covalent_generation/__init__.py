"""Minimal interfaces for a covalent molecule generation workflow."""

from .interfaces import Candidate, CandidateGenerator, DockingRequest, DockingResult, DockingTool

__all__ = ["Candidate", "CandidateGenerator", "DockingRequest", "DockingResult", "DockingTool"]
__version__ = "0.1.0"
