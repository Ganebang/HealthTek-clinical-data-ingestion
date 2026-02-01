"""
HTTP Utilities Module

Provides utility functions for downloading files from URLs with progress logging
and error handling. Used by data source modules for Bronze layer extraction.
"""

from typing import Dict, Any
import requests


def get_json(url: str) -> Dict[str, Any]:
    """
    Fetch JSON data from a URL.
    
    Args:
        url: URL to fetch JSON from
        
    Returns:
        Parsed JSON response as dictionary
        
    Raises:
        requests.HTTPError: If the request fails
    """
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()
