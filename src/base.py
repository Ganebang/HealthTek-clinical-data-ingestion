"""
Abstract base class for data sources with retry logic and error handling.
"""
import abc
import logging
import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import config

logger = logging.getLogger("healthtek.datasource")


class DataSourceError(Exception):
    """Base exception for data source errors."""
    pass


class DownloadError(DataSourceError):
    """Exception raised when download fails."""
    pass


class RefreshCheckError(DataSourceError):
    """Exception raised when checking refresh status fails."""
    pass


def create_session_with_retries(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    timeout: int = 30
) -> requests.Session:
    """
    Create a requests session with retry configuration and timeout.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Backoff factor for exponential backoff
        timeout: Request timeout in seconds
        
    Returns:
        Configured requests.Session object
    """
    session = requests.Session()
    
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set default timeout for all requests
    session.request = lambda *args, **kwargs: requests.Session.request(
        session, *args, timeout=kwargs.get('timeout', timeout), **kwargs
    )
    
    return session


class DataSource(abc.ABC):
    """
    Abstract base class representing a data source.
    
    Each data source must implement:
      - should_refresh(): Check if data needs to be refreshed
      - download(): Download the data
      
    Attributes:
        name: Name of the data source
        session: HTTP session with retry configuration
    """

    def __init__(self, name: str):
        """
        Initialize the data source.
        
        Args:
            name: Name of the data source
        """
        self.name = name
        self.session = create_session_with_retries(
            max_retries=config.MAX_RETRIES,
            backoff_factor=config.RETRY_BACKOFF_FACTOR,
            timeout=config.REQUEST_TIMEOUT
        )

    @abc.abstractmethod
    def should_refresh(self) -> bool:
        """
        Check if the data source needs to be refreshed.
        
        Returns:
            True if refresh is needed, False otherwise
            
        Raises:
            RefreshCheckError: If checking refresh status fails
        """
        pass

    @abc.abstractmethod
    def download(self) -> None:
        """
        Download data from the source.
        
        Raises:
            DownloadError: If download fails
        """
        pass

    def run(self) -> None:
        """
        Execute the data source extraction process.
        
        Checks if refresh is needed and downloads if necessary.
        Handles errors gracefully with logging.
        """
        logger.info(f"=== Source: {self.name} ===")

        try:
            if self.should_refresh():
                logger.info("Refresh needed - starting download")
                start_time = time.time()
                
                self.download()
                
                elapsed = time.time() - start_time
                logger.info(f"Download completed successfully in {elapsed:.2f}s")
            else:
                logger.info("No refresh needed - data is up to date")
                
        except RefreshCheckError as e:
            logger.error(f"Failed to check refresh status for {self.name}: {e}")
            raise
            
        except DownloadError as e:
            logger.error(f"Failed to download data for {self.name}: {e}")
            raise
            
        except Exception as e:
            logger.exception(f"Unexpected error in data source {self.name}: {e}")
            raise DataSourceError(f"Unexpected error in {self.name}") from e
