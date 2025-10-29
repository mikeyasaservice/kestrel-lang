# Phase 2 Architecture: Pure Polars (No Pandas)

**Decision:** Remove pandas entirely, make Polars the sole DataFrame library.

**Rationale:**
1. Phase 3 will replace SQLite+SQLAlchemy with DuckDB+Ibis anyway
2. Keeping pandas is technical debt we'll remove later
3. Polars has native SQLite support (`read_database`, `write_database`)
4. Clean architecture: One DataFrame library, not two

## Current State (v2.1.0.dev0)

```
Data Flow:
┌─────────────┐
│   Session   │ ← User API
└──────┬──────┘
       │ pandas.DataFrame
       ↓
┌─────────────┐
│    Cache    │ ← SQLite + pandas
│  (sql.py)   │   read_sql(), to_sql()
└──────┬──────┘
       │ pandas.DataFrame
       ↓
┌─────────────┐
│  Interface  │ ← Data sources
│  (codegen)  │
└─────────────┘

Dependencies:
- pandas ✅ (required)
- polars ✅ (installed but unused)
- SQLAlchemy ✅ (required for pandas.to_sql)
```

## Target State (v2.1.0-aether.1)

```
Data Flow:
┌─────────────┐
│   Session   │ ← User API
└──────┬──────┘
       │ polars.DataFrame
       ↓
┌─────────────┐
│    Cache    │ ← SQLite + polars
│  (sql.py)   │   read_database(), write_database()
└──────┬──────┘
       │ polars.DataFrame
       ↓
┌─────────────┐
│  Interface  │ ← Data sources
│  (codegen)  │
└─────────────┘

Dependencies:
- polars ✅ (required, sole DataFrame lib)
- pandas ❌ (removed)
- SQLAlchemy ✅ (still needed for cache, removed in Phase 3)
```

## Future State (Phase 3: v2.2.0-aether.1)

```
Data Flow:
┌─────────────┐
│   Session   │ ← User API
└──────┬──────┘
       │ polars.DataFrame
       ↓
┌─────────────┐
│    Cache    │ ← DuckDB + Polars
│  (duckdb.py)│   via Ibis
└──────┬──────┘
       │ polars.DataFrame
       ↓
┌─────────────┐
│  Interface  │ ← Data sources
│  (codegen)  │
└─────────────┘

Dependencies:
- polars ✅ (required)
- ibis-framework[duckdb] ✅ (required)
- duckdb ✅ (required)
- pandas ❌ (removed in Phase 2)
- SQLAlchemy ❌ (removed in Phase 3)
```

## Migration Strategy

### Phase 2 (Now): pandas → Polars

**Goal:** Remove pandas dependency entirely.

**Files to Modify (17 total):**

#### Core Cache Layer (Priority 1)

1. **`cache/sql.py`** (Most critical)
   ```python
   # BEFORE
   from pandas import DataFrame, read_sql
   df = read_sql(query, conn)
   df.to_sql(table, conn)

   # AFTER
   import polars as pl
   df = pl.read_database(query, connection_uri)
   df.write_database(table, connection_uri)
   ```

2. **`cache/inmemory.py`**
   ```python
   # BEFORE
   from pandas import DataFrame

   # AFTER
   import polars as pl
   DataFrame = pl.DataFrame  # Type alias for compatibility
   ```

3. **`cache/base.py`**
   ```python
   # BEFORE
   from pandas import DataFrame

   # AFTER
   import polars as pl
   DataFrame = pl.DataFrame
   ```

#### IR Layer (Priority 2)

4. **`ir/instructions.py`**
   ```python
   # BEFORE
   from pandas import DataFrame, read_json

   # AFTER
   import polars as pl
   DataFrame = pl.DataFrame
   # read_json replacement: pl.read_json()
   ```

5. **`ir/graph.py`** (no pandas imports currently - verify)

#### Interface/Codegen Layer (Priority 3)

6. **`interface/base.py`**
7. **`interface/codegen/dataframe.py`**
8. **`interface/codegen/sql.py`** ⚠️ **COMPLEX**
   - Uses `pandas.io.sql.SQLTable` and `pandasSQL_builder`
   - Need Polars equivalent or refactor
9. **`interface/codegen/utils.py`**

#### Frontend Layer (Priority 4)

10. **`frontend/parser.py`**
11. **`frontend/compile.py`**
12. **`cli.py`**
13. **`display.py`**

#### Mapping Layer (Priority 5)

14. **`mapping/data_model.py`**
    - Uses `Int64Dtype` - Polars equivalent: `pl.Int64`
15. **`mapping/transformers.py`**
    - Uses pandas `Series` - Polars equivalent: `pl.Series`

#### Analytics Layer (Priority 6)

16. **`analytics/interface.py`**

#### Config Layer (Priority 7)

17. **`config/utils.py`**
18. **`config/internal.py`**

### Key Challenges

#### Challenge 1: SQLAlchemy Integration

**Current:**
```python
# pandas integrates tightly with SQLAlchemy
df.to_sql(name, con=sqlalchemy_engine)
```

**Solution:**
```python
# Polars uses connection URI
connection_uri = f"sqlite:///{db_path}"
df.write_database(table_name, connection_uri)

# OR use SQLAlchemy to get URI
uri = str(engine.url)
```

#### Challenge 2: `pandas.io.sql` internals

**File:** `interface/codegen/sql.py`

**Current:**
```python
from pandas.io.sql import SQLTable, pandasSQL_builder
```

**This is DEEP pandas internals.** Options:

1. **Refactor away** (best) - Don't use pandas SQL internals
2. **Keep SQLAlchemy** - Use SQLAlchemy directly, not via pandas
3. **Wait for Phase 3** - Will be replaced by Ibis anyway

**Decision:** Option 2 - Refactor to use SQLAlchemy directly.

#### Challenge 3: DataFrame API Differences

| Operation | Pandas | Polars |
|-----------|--------|--------|
| Create | `pd.DataFrame(data)` | `pl.DataFrame(data)` |
| Read SQL | `pd.read_sql(query, conn)` | `pl.read_database(query, uri)` |
| Write SQL | `df.to_sql(name, conn)` | `df.write_database(name, uri)` |
| Read JSON | `pd.read_json(json_str)` | `pl.read_json(json_str)` |
| Column access | `df['col']` or `df.col` | `df['col']` or `df.get_column('col')` |
| Select | `df[['a', 'b']]` | `df.select(['a', 'b'])` |
| Filter | `df[df['a'] > 5]` | `df.filter(pl.col('a') > 5)` |
| dtypes | `df.dtypes` | `df.dtypes` (similar) |

**Most operations are similar.** Main differences:
- Polars is more explicit (`.select()` vs `[]`)
- Polars uses expressions (`pl.col()`) for complex operations
- Polars is lazy by default (use `.collect()` for eager)

#### Challenge 4: Tests

**Current:** 194 tests use pandas DataFrames

**Strategy:**
1. Update test fixtures to create Polars DataFrames
2. Update assertions (`pd.testing.assert_frame_equal` → `pl.testing.assert_frame_equal`)
3. Update test data loading

**Expected test failures:** 50-100 initially

**Expected time to fix:** 1-2 days

### Implementation Plan

#### Step 1: Update Dependencies (10 min)

```toml
# pyproject.toml
dependencies = [
    "polars>=0.19.0",       # REQUIRED
    # pandas REMOVED
    "SQLAlchemy>=2.0.31",   # Still needed (Phase 3 removes)
    # ... rest unchanged
]

[project.optional-dependencies]
pandas = [
    "pandas>=2.0.3",        # Optional for backwards compat
]
```

#### Step 2: Create Compatibility Layer (30 min)

**New file:** `src/kestrel/compat.py`

```python
"""Compatibility layer for DataFrame operations."""

import polars as pl
from typing import Union, Any

# Type aliases
DataFrame = pl.DataFrame
Series = pl.Series

def read_database(query: str, connection) -> pl.DataFrame:
    """Read from database (SQLite, etc)."""
    # Handle both URI and SQLAlchemy engine
    if hasattr(connection, 'url'):
        uri = str(connection.url)
    else:
        uri = connection
    return pl.read_database(query, uri)

def write_database(df: pl.DataFrame, table: str, connection,
                   if_exists: str = 'replace') -> None:
    """Write to database."""
    if hasattr(connection, 'url'):
        uri = str(connection.url)
    else:
        uri = connection

    # Map pandas if_exists to Polars engine
    engine = 'replace' if if_exists == 'replace' else 'append'
    df.write_database(table, uri, engine=engine)

def from_dict(data: dict) -> pl.DataFrame:
    """Create DataFrame from dict."""
    return pl.DataFrame(data)

def concat(dfs: list) -> pl.DataFrame:
    """Concatenate DataFrames."""
    return pl.concat(dfs)

# Optional pandas compatibility
try:
    import pandas as pd

    def to_pandas(df: pl.DataFrame) -> pd.DataFrame:
        """Convert Polars to pandas (optional)."""
        return df.to_pandas()

    def from_pandas(df: pd.DataFrame) -> pl.DataFrame:
        """Convert pandas to Polars (optional)."""
        return pl.from_pandas(df)

except ImportError:
    def to_pandas(df):
        raise ImportError("pandas not installed. Install with: pip install pandas")

    def from_pandas(df):
        raise ImportError("pandas not installed. Install with: pip install pandas")
```

#### Step 3: Update Cache Layer (2-3 hours)

**`cache/sql.py`** - Main refactor:

```python
# BEFORE
from pandas import DataFrame, read_sql

def get_dataframe(self, instruction_id):
    return read_sql(self.cache_catalog[instruction_id], self.connection)

def set_dataframe(self, data, instruction_id):
    data.to_sql(
        f"d{instruction_id}",
        self.connection,
        if_exists="replace",
        index=False,
    )

# AFTER
import polars as pl
from kestrel.compat import DataFrame, read_database, write_database

def get_dataframe(self, instruction_id):
    query = self.cache_catalog[instruction_id]
    return read_database(query, self.connection)

def set_dataframe(self, data: pl.DataFrame, instruction_id):
    table_name = f"d{instruction_id}"
    write_database(data, table_name, self.connection, if_exists='replace')
```

**`cache/inmemory.py`** - Simple:

```python
# BEFORE
from pandas import DataFrame

# AFTER
from kestrel.compat import DataFrame
# Everything else stays the same!
```

**`cache/base.py`** - Simple:

```python
# BEFORE
from pandas import DataFrame

# AFTER
from kestrel.compat import DataFrame
```

#### Step 4: Update IR Layer (1 hour)

**`ir/instructions.py`**:

```python
# BEFORE
from pandas import DataFrame, read_json

# AFTER
from kestrel.compat import DataFrame
import polars as pl

# Replace read_json() calls:
# data = read_json(json_string)
data = pl.read_json(json_string)
```

#### Step 5: Update Interface Layer (2-3 hours)

**`interface/codegen/sql.py`** - COMPLEX FILE:

```python
# BEFORE
from pandas.io.sql import SQLTable, pandasSQL_builder

# AFTER - Refactor to use SQLAlchemy directly
from sqlalchemy import Table, MetaData, insert, select
# Remove pandas SQL internals completely
```

This file needs careful refactoring. It's using pandas internals for SQL generation.

**Alternative:** Since Phase 3 replaces this with Ibis anyway, we could:
1. Keep minimal pandas dependency just for this file
2. Add TODO comments
3. Remove in Phase 3

**Decision needed:** Full refactor now vs minimal change?

#### Step 6: Update All Other Files (2 hours)

Simple find-replace in:
- `frontend/parser.py`
- `frontend/compile.py`
- `cli.py`
- `display.py`
- `mapping/data_model.py`
- `mapping/transformers.py`
- `analytics/interface.py`
- `config/utils.py`
- `config/internal.py`

```python
# BEFORE
from pandas import DataFrame

# AFTER
from kestrel.compat import DataFrame
```

Most code will work unchanged since we're using type aliases.

#### Step 7: Update Tests (4-6 hours)

**Test file changes:**

```python
# BEFORE
import pandas as pd
from pandas import DataFrame

df = pd.DataFrame({'a': [1, 2, 3]})
pd.testing.assert_frame_equal(df1, df2)

# AFTER
import polars as pl
from kestrel.compat import DataFrame

df = pl.DataFrame({'a': [1, 2, 3]})
assert df1.equals(df2)  # or pl.testing.assert_frame_equal
```

**Expected failures:**
- DataFrame creation syntax
- DataFrame comparison methods
- Column access patterns
- Type assertions

#### Step 8: Test Without Pandas (1 hour)

```bash
# Uninstall pandas
pip uninstall pandas -y

# Run full test suite
pytest -v

# Should pass with 0 pandas imports
```

### Timeline

| Task | Time | Priority |
|------|------|----------|
| 1. Update dependencies | 10 min | P0 |
| 2. Create compat layer | 30 min | P0 |
| 3. Cache layer | 2-3 hrs | P0 |
| 4. IR layer | 1 hr | P0 |
| 5. Interface layer | 2-3 hrs | P1 |
| 6. Other files | 2 hrs | P1 |
| 7. Update tests | 4-6 hrs | P0 |
| 8. Test without pandas | 1 hr | P0 |

**Total: 13-18 hours (2-3 days)**

### Risks

#### Risk 1: SQLAlchemy+Polars compatibility

**Likelihood:** Medium
**Impact:** High

**Mitigation:**
- Polars `write_database()` and `read_database()` support SQLite URIs
- Can convert SQLAlchemy engine to URI: `str(engine.url)`
- Test early with actual SQLite database

#### Risk 2: `interface/codegen/sql.py` complexity

**Likelihood:** High
**Impact:** Medium

**Mitigation:**
- Option A: Deep refactor (3-4 hours)
- Option B: Keep pandas just for this file temporarily (add to optional deps)
- Option C: Skip for now, fix in Phase 3 when we replace with Ibis

**Recommendation:** Option B - Keep pandas as optional dep for now, document removal in Phase 3.

#### Risk 3: Test failures

**Likelihood:** High
**Impact:** Medium

**Mitigation:**
- Fix incrementally
- Focus on critical tests first (cache, session)
- Some tests may need rewrite

#### Risk 4: Performance differences

**Likelihood:** Low
**Impact:** Low

**Mitigation:**
- Polars is usually faster than pandas
- Benchmark critical paths
- Document any regressions

### Success Criteria

✅ All 194 tests pass without pandas installed
✅ `pip show pandas` returns "not found"
✅ SQLite cache works with Polars DataFrames
✅ Session API returns Polars DataFrames
✅ Zero pandas imports in codebase (except optional)
✅ Performance equal or better than pandas

### Backward Compatibility

**Breaking changes:**
- Return type: `pandas.DataFrame` → `polars.DataFrame`
- DataFrame API differences (`.select()` vs `[]`)

**Mitigation:**
```toml
[project.optional-dependencies]
pandas = ["pandas>=2.0.3"]
```

```python
# For users who need pandas
pip install kestrel_core[pandas]

# Then in code:
from kestrel.compat import to_pandas
df_polars = session.get_variable('procs')
df_pandas = to_pandas(df_polars)  # Optional conversion
```

## Next Steps

1. **Get approval** - Confirm Strategy B (Pure Polars)
2. **Start with compat layer** - Foundation for all changes
3. **Cache layer first** - Core functionality
4. **Iterative testing** - Fix as we go
5. **Document breaking changes** - Update DIFFERENCES.md

**Ready to start?**

---

**Estimated completion:** 2-3 days
**Target version:** v2.1.0-aether.1
**Breaking change:** YES (major API change)
**Worth it:** ABSOLUTELY 🚀
