"""Compatibility layer for DataFrame operations using Polars.

This module provides a unified interface for DataFrame operations,
with Polars as the primary DataFrame library and optional pandas support.
"""

import polars as pl
from typing import Any, Union, Optional
import logging

_logger = logging.getLogger(__name__)

# Type aliases
DataFrame = pl.DataFrame
Series = pl.Series


def read_database(
    query: str,
    connection: Union[str, Any],
    **kwargs
) -> pl.DataFrame:
    """Read from database using Polars.

    Args:
        query: SQL query string or table name
        connection: Connection URI string or SQLAlchemy engine/connection
        **kwargs: Additional arguments passed to read_database

    Returns:
        Polars DataFrame with query results

    Examples:
        >>> df = read_database("SELECT * FROM users", "sqlite:///db.sqlite")
        >>> df = read_database("users", sqlalchemy_engine)
    """
    # Convert SQLAlchemy Compiler object to string with literal binds
    if not isinstance(query, str):
        # Check if it's already a Compiled object (has compile() been called)
        if hasattr(query, 'statement'):
            # This is a Compiled object, get the statement and recompile with literal_binds
            from sqlalchemy import __version__ as sa_version
            try:
                # For SQLAlchemy 2.x
                query = str(query.statement.compile(
                    compile_kwargs={"literal_binds": True}
                ))
            except Exception:
                # Fallback: just stringify
                query = str(query)
        elif hasattr(query, 'compile'):
            # This is a Selectable, compile it with literal_binds
            query = str(query.compile(compile_kwargs={"literal_binds": True}))
        else:
            query = str(query)

    # Convert table name to query if needed (no spaces and no SQL keywords)
    query_lower = query.lower().strip()
    if ' ' not in query and not any(kw in query_lower for kw in ['select', 'with', 'insert', 'update', 'delete']):
        # This looks like a table name, convert to SELECT query
        query = f'SELECT * FROM "{query}"'

    # Convert SQLAlchemy engine/connection to URI if needed
    if hasattr(connection, 'engine'):
        # This is a SQLAlchemy Connection object
        connection_uri = str(connection.engine.url)
    elif hasattr(connection, 'url'):
        # This is a SQLAlchemy Engine object
        connection_uri = str(connection.url)
    else:
        connection_uri = connection

    try:
        # Use read_database_uri for consistent behavior
        return pl.read_database_uri(query, connection_uri, **kwargs)
    except Exception as e:
        _logger.error(f"Failed to read from database: {e}")
        raise


def write_database(
    df: pl.DataFrame,
    table_name: str,
    connection: Union[str, Any],
    if_exists: str = 'replace',
    **kwargs
) -> None:
    """Write DataFrame to database using Polars.

    Args:
        df: Polars DataFrame to write
        table_name: Name of the table to write to
        connection: Connection URI string or SQLAlchemy engine
        if_exists: How to behave if table exists ('replace', 'append', 'fail')
        **kwargs: Additional arguments

    Examples:
        >>> write_database(df, "users", "sqlite:///db.sqlite")
        >>> write_database(df, "users", engine, if_exists='append')
    """
    # Convert SQLAlchemy engine/connection to URI if needed
    if hasattr(connection, 'engine'):
        # This is a SQLAlchemy Connection object
        connection_uri = str(connection.engine.url)
    elif hasattr(connection, 'url'):
        # This is a SQLAlchemy Engine object
        connection_uri = str(connection.url)
    else:
        connection_uri = connection

    try:
        df.write_database(
            table_name=table_name,
            connection=connection_uri,
            if_table_exists=if_exists,
            **kwargs
        )
    except Exception as e:
        _logger.error(f"Failed to write to database: {e}")
        raise


def from_dict(data: dict, **kwargs) -> pl.DataFrame:
    """Create DataFrame from dictionary.

    Args:
        data: Dictionary with column names as keys
        **kwargs: Additional arguments

    Returns:
        Polars DataFrame
    """
    return pl.DataFrame(data, **kwargs)


def concat(dfs: list, **kwargs) -> pl.DataFrame:
    """Concatenate DataFrames vertically.

    Args:
        dfs: List of Polars DataFrames
        **kwargs: Additional arguments

    Returns:
        Concatenated Polars DataFrame
    """
    return pl.concat(dfs, **kwargs)


def read_json(source: Union[str, bytes], **kwargs) -> pl.DataFrame:
    """Read JSON into DataFrame.

    Args:
        source: JSON string, bytes, or file path
        **kwargs: Additional arguments

    Returns:
        Polars DataFrame
    """
    return pl.read_json(source, **kwargs)


# Optional pandas compatibility
try:
    import pandas as pd

    _HAS_PANDAS = True

    def to_pandas(df: pl.DataFrame) -> pd.DataFrame:
        """Convert Polars DataFrame to pandas (requires pandas install).

        Args:
            df: Polars DataFrame

        Returns:
            pandas DataFrame

        Raises:
            ImportError: If pandas is not installed
        """
        return df.to_pandas()

    def from_pandas(df: pd.DataFrame) -> pl.DataFrame:
        """Convert pandas DataFrame to Polars (requires pandas install).

        Args:
            df: pandas DataFrame

        Returns:
            Polars DataFrame

        Raises:
            ImportError: If pandas is not installed
        """
        return pl.from_pandas(df)

    _logger.debug("pandas compatibility layer enabled")

except ImportError:
    _HAS_PANDAS = False

    def to_pandas(df: pl.DataFrame):
        """Convert to pandas (not available)."""
        raise ImportError(
            "pandas not installed. Install with: pip install kestrel_core[pandas]"
        )

    def from_pandas(df):
        """Convert from pandas (not available)."""
        raise ImportError(
            "pandas not installed. Install with: pip install kestrel_core[pandas]"
        )

    _logger.debug("pandas compatibility layer disabled (pandas not installed)")


def has_pandas() -> bool:
    """Check if pandas is available.

    Returns:
        True if pandas is installed, False otherwise
    """
    return _HAS_PANDAS
