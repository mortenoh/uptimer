# Fix Plan: Project Inconsistencies

## Critical (Fix Immediately)

### 1. Add Missing Stage Metadata
**Files:** `src/uptimer/web/api/stages.py`

Add metadata entries for:
- `dhis2-version` - min_version parameter
- `dhis2-integrity` - check parameters
- `dhis2-job` - job_type parameter
- `dhis2-analytics` - max_age_hours parameter

Remove orphaned `dhis2_checks` entry (line 290).

### 2. Fix Metadata Key Naming
**Files:** `src/uptimer/web/api/stages.py`

Change `json_schema` key to `json-schema` to match actual stage name.

---

## High Priority (Fix Soon)

### 3. Remove Hardcoded Demo Credentials
**Files:**
- `src/uptimer/stages/dhis2.py`
- `src/uptimer/stages/dhis2_checks.py`

Change default password from `"district"` to `None` and require explicit configuration.

### 4. Document All Stage Parameters
**Files:** `src/uptimer/web/api/stages.py`

Ensure every stage has complete options documentation in metadata.

---

## Medium Priority

### 5. Add Pipeline Integration Test
**Files:** `tests/test_pipeline.py` (new)

Test `run_pipeline()` with multiple stages, verify context passing.

### 6. Improve Stage Instantiation Error Handling
**Files:** `src/uptimer/pipeline.py`

Log warning when falling back to no-args instantiation.

### 7. Add Startup Warning for Default Secret Key
**Files:** `src/uptimer/web/app.py` or `src/uptimer/cli.py`

Warn at startup if `UPTIMER_SECRET_KEY` is still the default value.

---

## Low Priority

### 8. Update README Stage Count
**Files:** `README.md`

Change "15+" to "17" check types.

### 9. Add URL maxLength Validation
**Files:** `src/uptimer/schemas.py`

Add `max_length=2048` to URL field.

### 10. Fix Response Type Annotations
**Files:** `src/uptimer/web/routes.py`

Make return type annotations consistent with response models.

### 11. Add MongoDB Connection Validation
**Files:** `src/uptimer/storage.py`

Validate MongoDB connection at Storage init time.

### 12. Update CLAUDE.md Stage List
**Files:** `CLAUDE.md`

List all 17 stages in architecture section.

---

## Implementation Order

1. Stage metadata fixes (critical, affects frontend)
2. Security: credentials and secret key warning
3. Error handling improvements
4. Documentation updates
5. Tests
6. Low priority cleanups

## Estimated Changes

| Priority | Files | Lines Changed |
|----------|-------|---------------|
| Critical | 1 | ~100 |
| High | 3 | ~30 |
| Medium | 3 | ~50 |
| Low | 5 | ~30 |
| **Total** | **12** | **~210** |
