# Test Data

## Golden Files (`golden/`)

Golden file snapshots capture the exact Rich text output for known test data
across various flag combinations. They serve as regression guards during
refactoring (especially Phase 3 THAC0 integration): after wrapping render
calls in `emit()`, the default output must remain identical.

### Regenerating

After intentional output changes, regenerate with:

```bash
python -m tests.generate_golden
```

### Verifying

Golden files are automatically checked by pytest via `tests/test_golden.py`.
You can also verify manually:

```bash
python -m tests.generate_golden --check
```

### What's captured

| File | Scenario |
|------|----------|
| `diagnosis_default.golden` | All tiers, no paging |
| `diagnosis_verbose.golden` | `-v` mode |
| `diagnosis_tier0.golden` | `--tier 0` only |
| `diagnosis_tier1.golden` | `--tier 1` only |
| `diagnosis_tier2.golden` | `--tier 2` only |
| `diagnosis_tier01.golden` | `--tier 0,1` |
| `history_default.golden` | Restart history table |
| `history_empty.golden` | Empty history |
| `diagnosis_empty.golden` | Empty/minimal data |

Test data uses fixed timestamps and values from `conftest.py` fixtures,
so no normalization is needed.
