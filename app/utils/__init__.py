"""
Utility functions for the Healthcare Deception Framework.

This package contains various utility modules used throughout the application,
including honeytoken management and security monitoring tools.
"""

# Import key utilities to make them available at the package level
from .honeytoken_manager import generate_honeytoken, check_honeytoken_access

__all__ = ['generate_honeytoken', 'check_honeytoken_access']