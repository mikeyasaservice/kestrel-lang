# Kestrel Modernization Assessment for Aether
**Date:** 2025-10-29
**Branch:** claude/kestrel-lang-modernization-011CUafHWiNmnxME2SyFtVuR

## Executive Summary

Kestrel is in **better shape than expected** for modernization. Already on v2.0.0b with modern dependencies and good architecture. Recommended approach: **contribute upstream first, fork only if rejected**.

## Current State Analysis

### Project Structure
```
Monorepo with 5 packages:
- kestrel_core (main runtime)
- kestrel_jupyter (Jupyter integration)
- kestrel_interface_opensearch
- kestrel_interface_sqlalchemy
- kestrel_tool

Total Python files in core: 40
Test files: 15
```

### Dependencies (packages/kestrel_core/pyproject.toml)
```toml
requires-python = ">=3.8"  # ← UPGRADE TARGET
dependencies = [
    "typeguard>=4.3.0",      # ✅ Modern
    "pyyaml>=6.0.1",         # ✅ Modern
    "lark>=1.1.9",           # Parser
    "pandas>=2.0.3",         # ✅ Already modern!
    "pyarrow>=17.0.0",       # ✅ Modern
    "mashumaro>=3.13.1",     # Serialization
    "networkx>=3.1",         # Graph operations
    "SQLAlchemy>=2.0.31",    # ✅ Modern
]
```

**Finding:** Dependencies are already modern! Just need Python version bump.

### Architecture Strengths

1. **IR Graph Design** (session.py:29)
   - Uses Intermediate Representation graph for execution
   - Allows optimization and compilation
   - Good foundation for analytics

2. **Type Safety** (session.py:23)
   - Already using @typechecked decorator
   - Type hints present
   - Easy to extend with strict mypy

3. **Interface System** (session.py:41)
   - Pluggable interface manager
   - PythonAnalyticsInterface already exists
   - Perfect for Ibis/DuckDB integration

4. **Cache System** (session.py:36)
   - SqlCache for intermediate results
   - **Critical integration point for Polars**

### What's Missing (Our Opportunity)

- ❌ No Polars support
- ❌ No DuckDB integration
- ❌ No Ibis analytics interface
- ❌ No YAML playbook support
- ❌ Python 3.8 still supported (EOL)

## Recommended Phased Approach

### Phase 0: Research & Upstream Engagement (Week 1)

**Before writing code:**

```bash
# Check community receptiveness
gh issue create --repo opencybersecurityalliance/kestrel-lang \
  --title "RFC: Polars DataFrame support and analytics modernization" \
  --body "We'd like to contribute Polars support, Ibis analytics, and YAML playbooks. Interested?"

# Meanwhile, deep dive:
# 1. Read all of ir/graph.py
# 2. Understand instruction execution
# 3. Trace a simple hunt end-to-end
# 4. Run all tests locally
```

**Decision point:** If positive response → contribute upstream. If no response in 1 week or rejection → proceed with fork.

### Phase 1: Foundation (Weeks 2-3)

**Goal:** Modernize base without breaking anything

```toml
# pyproject.toml changes
requires-python = ">=3.10"  # Drop 3.8, 3.9
classifiers = [
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    # ... existing ...
    "polars>=0.19.0",  # ADD
]
```

**Tasks:**
- [x] Update Python version requirement
- [ ] Test on 3.10, 3.11, 3.12
- [ ] Update CI/CD for multi-version testing
- [ ] Add polars dependency
- [ ] Run full test suite - ensure 100% pass

**Deliverable:** v2.0.0 or v2.1.0 (depending on versioning strategy)

### Phase 2: Polars Integration (Weeks 3-4)

**Key files to modify:**

```python
# 1. kestrel/cache/sql.py - Add Polars support
class SqlCache:
    def get_dataframe(self, var_name: str, format: str = 'pandas'):
        """Get cached data as DataFrame.

        Args:
            var_name: Variable name
            format: 'pandas' or 'polars'
        """
        # Existing pandas code
        if format == 'polars':
            import polars as pl
            return pl.from_pandas(df)
        return df

# 2. kestrel/session.py - Add format parameter
class Session:
    def get_variable(self, var_name: str, format: str = 'pandas'):
        """Retrieve hunt variable.

        Args:
            var_name: Variable name
            format: Output format ('pandas' or 'polars')
        """
        pass
```

**Test strategy:**
```python
# tests/test_polars_integration.py
def test_polars_output():
    session = Session()
    session.execute("procs = GET process FROM data WHERE ...")

    # Pandas (default, backward compatible)
    df_pandas = session.get_variable('procs', format='pandas')
    assert isinstance(df_pandas, pd.DataFrame)

    # Polars (new)
    df_polars = session.get_variable('procs', format='polars')
    assert isinstance(df_polars, pl.DataFrame)
    assert len(df_polars) == len(df_pandas)
```

**Deliverable:** v2.1.0-aether.1 (or v2.2.0 if upstream)

### Phase 3: Ibis Analytics Interface (Weeks 5-6)

**New module:**

```python
# kestrel/analytics/ibis_interface.py
from kestrel.analytics.interface import AbstractAnalyticsInterface
import ibis
import duckdb
import polars as pl

class IbisAnalyticsInterface(AbstractAnalyticsInterface):
    """Execute analytics using Ibis + DuckDB."""

    def __init__(self):
        super().__init__("ibis")
        self.con = ibis.duckdb.connect()
        self._analytics = {}

    def register_analytic(self, name: str, func: Callable):
        """Register Python function as analytic."""
        self._analytics[name] = func

    def execute(self, analytic_name: str, input_df: pl.DataFrame) -> pl.DataFrame:
        """Execute analytic on Polars DataFrame."""
        func = self._analytics[analytic_name]

        # Option 1: Direct Polars
        if hasattr(func, '_polars_native'):
            return func(input_df)

        # Option 2: Via Ibis/DuckDB
        table = self.con.read_pandas(input_df.to_pandas())
        result = func(table)
        return pl.from_arrow(result.to_arrow())
```

**Integration point:**
```python
# kestrel/session.py
class Session:
    def __init__(self):
        # ... existing ...
        ibis_analytics = IbisAnalyticsInterface()
        self.interface_manager = InterfaceManager([
            cache,
            pyanalytics,
            ibis_analytics  # ADD THIS
        ])
```

**Example usage:**
```python
# User's analytic
@polars_native  # Decorator to mark direct Polars
def detect_beaconing(df: pl.DataFrame) -> pl.DataFrame:
    """Detect periodic connections."""
    return df.with_columns([
        pl.col('timestamp').diff().alias('interval')
    ]).filter(
        pl.col('interval').std() < 5  # Low variance = beaconing
    )

# Register
session.register_analytic('detect_beaconing', detect_beaconing)

# Use in Kestrel
session.execute("""
    conns = GET network-traffic FROM siem WHERE dst_port = 443
    beacons = APPLY ibis://detect_beaconing ON conns
    DISP beacons
""")
```

**Deliverable:** v2.2.0-aether.1 (or v2.3.0)

### Phase 4: YAML Playbook Support (Weeks 7-8)

**New module:**

```python
# kestrel/playbook.py
import yaml
from pathlib import Path
import polars as pl
from typing import Dict, Any

class PlaybookRunner:
    """Execute YAML hunt playbooks."""

    def __init__(self, session: Session):
        self.session = session

    def load(self, path: Path) -> Dict[str, Any]:
        """Load and validate YAML playbook."""
        with open(path) as f:
            config = yaml.safe_load(f)
        self._validate(config)
        return config

    def execute(self, path: Path) -> pl.DataFrame:
        """Run playbook steps sequentially."""
        config = self.load(path)

        results = {}
        for step in config['steps']:
            step_name = step['name']

            # Translate YAML to Kestrel code
            kestrel_code = self._yaml_to_kestrel(step)

            # Execute
            self.session.execute(kestrel_code)

            # Store result if output specified
            if 'output' in step:
                results[step_name] = self.session.get_variable(
                    step['output'],
                    format='polars'
                )

        return results[config['final_output']]

    def _yaml_to_kestrel(self, step: Dict) -> str:
        """Convert YAML step to Kestrel code."""
        action = step['action']

        if action == 'get':
            return f"{step['var']} = GET {step['entity']} FROM {step['source']} WHERE {step['where']}"

        elif action == 'apply':
            return f"{step['output']} = APPLY {step['analytic']} ON {step['input']}"

        # ... more actions
```

**Example YAML playbook:**

```yaml
# playbooks/detect_lateral_movement.yaml
name: "Lateral Movement Detection"
description: "Detect potential lateral movement via unusual authentication patterns"

steps:
  - name: get_auth_events
    action: get
    entity: authentication-event
    source: siem
    where: "timestamp > t'2025-10-01T00:00:00Z'"
    var: auth_events

  - name: detect_unusual_auth
    action: apply
    analytic: ibis://detect_unusual_auth_patterns
    input: auth_events
    output: suspicious_auth

  - name: enrich_with_user_context
    action: apply
    analytic: ibis://enrich_user_context
    input: suspicious_auth
    output: enriched_alerts

final_output: enriched_alerts
```

**CLI integration:**
```python
# kestrel/cli.py - Add playbook command
@click.command()
@click.argument('playbook_path')
def run_playbook(playbook_path):
    """Execute a YAML hunt playbook."""
    session = Session()
    runner = PlaybookRunner(session)

    results = runner.execute(Path(playbook_path))
    print(results)

# Usage:
# $ kestrel playbook playbooks/detect_lateral_movement.yaml
```

**Deliverable:** v2.3.0-aether.1 (or v3.0.0 - major feature)

## Testing Strategy

### Test Coverage Goals

```
Current: Unknown (need to run pytest --cov)
Target:  >85% for new code
         >70% overall
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        cd packages/kestrel_core
        pip install -e ".[dev,test]"
        pip install polars ibis-framework[duckdb]

    - name: Run tests
      run: |
        cd packages/kestrel_core
        pytest -v --cov=kestrel --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        files: ./packages/kestrel_core/coverage.xml

  test-integration:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Run integration tests
      run: |
        # Test against real data sources
        docker-compose up -d
        pytest tests/integration/ -v
```

## Critical Success Factors

### 1. **Maintain Backward Compatibility**

Every change must pass this test:

```python
# Existing user code must still work
session = Session()
session.execute("procs = GET process FROM data WHERE pid = 1234")
df = session.get_variable('procs')  # Still returns pandas by default
assert isinstance(df, pd.DataFrame)
```

### 2. **Document Migration Path**

```markdown
# MIGRATION.md

## Migrating to Aether-Kestrel v2.x

### For Users

**No changes required!** Aether-Kestrel is drop-in compatible.

**New features:**
```python
# Use Polars for better performance
df = session.get_variable('procs', format='polars')

# Run YAML playbooks
kestrel playbook my_hunt.yaml
```

### For Analytic Developers

**Old way (still works):**
```python
def my_analytic(df: pd.DataFrame) -> pd.DataFrame:
    return df[df['score'] > 0.8]
```

**New way (recommended):**
```python
import polars as pl

@polars_native
def my_analytic(df: pl.DataFrame) -> pl.DataFrame:
    return df.filter(pl.col('score') > 0.8)
```
```

### 3. **Community Communication**

```markdown
# FORK.md (if forking)

## Why This Fork Exists

The Aether team at [Company] is building a modern threat hunting platform.
We love Kestrel but need:

1. **Modern Python support** (3.10+)
2. **High-performance analytics** (Polars, DuckDB, Ibis)
3. **Declarative playbooks** (YAML-based)
4. **Active maintenance** (monthly releases minimum)

## Our Commitment

- ✅ Maintain backward compatibility
- ✅ Contribute improvements upstream when possible
- ✅ Respond to issues within 48-72 hours
- ✅ Monthly releases minimum
- ✅ Transparent roadmap

## Differences from Upstream

See [DIFFERENCES.md](DIFFERENCES.md) for detailed comparison.

## Getting Involved

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md).

**Contact:**
- Jules: jules@yourcompany.com
- GitHub Discussions: [link]
- Slack: #aether-kestrel
```

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Upstream maintainers object to fork | Medium | High | Engage proactively, contribute first |
| Breaking existing analytics | Low | Critical | Comprehensive testing, backward compat |
| Community fragmentation | Medium | High | Clear communication, merge upstream when possible |
| Maintenance burden too high | Medium | High | Automate CI/CD, focus on core features first |
| Performance regression | Low | Medium | Benchmark before/after, optimize critical paths |

## Success Metrics (Track Weekly)

```markdown
# METRICS.md

## Week 1
- [ ] Tests passing: ___%
- [ ] Test coverage: ___%
- [ ] Python 3.10 compatible: Yes/No
- [ ] Python 3.11 compatible: Yes/No
- [ ] Python 3.12 compatible: Yes/No

## Week 2
- [ ] Polars integration complete: Yes/No
- [ ] Backward compat maintained: Yes/No
- [ ] Performance benchmark: ___x faster

## Week 3
- [ ] Ibis integration complete: Yes/No
- [ ] Analytics tested: ___/10

## Week 4
- [ ] YAML playbooks working: Yes/No
- [ ] Documentation complete: Yes/No
- [ ] Ready for v2.1.0 release: Yes/No
```

## Revised Timeline

| Milestone | Date | Deliverable |
|-----------|------|-------------|
| Week 1 | Nov 5 | Upstream engagement + deep dive complete |
| Week 2 | Nov 12 | Python 3.10+ support, all tests passing |
| Week 3 | Nov 19 | Polars integration complete |
| Week 4 | Nov 26 | **v2.1.0-aether.1 release** |
| Week 5 | Dec 3 | Ibis analytics interface complete |
| Week 6 | Dec 10 | Ibis testing + documentation |
| Week 7 | Dec 17 | YAML playbook support |
| Week 8 | Dec 24 | **v2.2.0-aether.1 release** |

## Next Actions

1. **Run comprehensive test suite:**
   ```bash
   cd packages/kestrel_core
   pytest -v --cov=kestrel --cov-report=html
   open htmlcov/index.html
   ```

2. **Deep dive into IR graph:**
   ```bash
   # Read these files in order:
   cat src/kestrel/ir/instructions.py
   cat src/kestrel/ir/graph.py
   cat src/kestrel/session.py
   ```

3. **Engage upstream (if not forking immediately):**
   ```bash
   gh issue create --title "RFC: Modern analytics and Polars support"
   ```

4. **Set up dev environment:**
   ```bash
   python3.12 -m venv venv-aether
   source venv-aether/bin/activate
   cd packages/kestrel_core
   pip install -e ".[dev,test]"
   pip install polars ibis-framework[duckdb] mypy black pre-commit
   ```

5. **Create tracking board:**
   ```bash
   # GitHub Projects or similar
   # Columns: Backlog, In Progress, Review, Done
   ```

## Conclusion

Your roadmap is **excellent in concept** but needs adjustment for:
1. **Monorepo structure** (not single package)
2. **Better starting position** (already modern)
3. **Upstream engagement** (try contributing first)
4. **Realistic timeline** (8 weeks not 4 for full vision)

**Bottom line:** This is very doable. Start with upstream engagement, then proceed methodically. The codebase is clean and well-architected, which is great news.

**Ready to start? Let me know if you want me to:**
- Run the test suite
- Create the RFC issue for upstream
- Start Phase 1 (Python 3.10+ migration)
- Deep dive into the IR graph architecture
