# Power BI PBIP Connector - Optimization Analysis

## Key Performance Bottlenecks

### 1. **Redundant File I/O (HIGH IMPACT)**

**Problem**: Files are read multiple times during validation and fixing operations.

**Examples**:
- `validate_tmdl_syntax()`: Reads each TMDL file twice (once to extract table names, once for validation)
- `fix_all_dax_quoting()`: Reads each file multiple times (extract tables, then fix DAX)

**Solution**: 
- Implement a file content caching layer at project load time
- Create a `_file_cache` dict to store content during operations
- Reuse cached content instead of re-reading

**Estimated Impact**: 30-50% reduction in file I/O time for validation operations

---

### 2. **Inefficient Regex Counting (MEDIUM IMPACT)**

**Problem**: Using `len(re.findall())` to count matches runs the regex twice (once to find, once to count).

**Examples**:
```python
pattern = rf"(?<!['\w]){escaped_name}(?=\s*\[)"
content_before = content
content = re.sub(pattern, table_quoted, content)
file_fixes += len(re.findall(pattern, content_before))  # <-- runs regex AGAIN
```

**Solution**:
- Use `subn()` instead of `sub()` + `findall()` - returns both result and count
- Already partially done for some patterns but not all

**Estimated Impact**: 15-25% faster regex operations

---

### 3. **Pattern Compilation On Every Operation (LOW-MEDIUM IMPACT)**

**Problem**: Regex patterns are compiled inline on every file operation.

**Solution**:
- Compile common patterns once at class initialization
- Store compiled patterns in class attributes
- Reuse for operations

**Estimated Impact**: 5-10% faster for repeated operations

---

### 4. **Unnecessary Full File Scans (MEDIUM IMPACT)**

**Problem**: 
- `validate_tmdl_syntax()` processes all lines even when no validation needed
- Doesn't early-exit when max errors reached
- No batching of similar operations

**Solution**:
- Add optional max_errors parameter to stop early
- Skip validation for large files above size threshold
- Batch process similar file types together

**Estimated Impact**: 20-40% faster validation for large projects

---

### 5. **Inefficient Data Structure for Table Tracking (LOW IMPACT)**

**Problem**: Using `set()` and `list()` conversions repeatedly for table names.

**Solution**:
- Use a single data structure (PBIPProject.table_metadata)
- Store table names with their properties once at load
- Dictionary: `{table_name: {'needs_quoting': bool, 'files': [Path], ...}}`

**Estimated Impact**: 5% improvement for large models (100+ tables)

---

### 6. **Multiple Passes Over Content (MEDIUM IMPACT)**

**Problem**: Multiple regex patterns are applied sequentially to the same content:

```python
for table_name in tables_needing_quotes:
    # Apply pattern 1
    pattern1 = ...
    content = re.sub(pattern1, ...)
    # Apply pattern 2
    pattern2 = ...
    content = re.sub(pattern2, ...)  # Re-scan same content
```

**Solution**:
- Combine related patterns into a single pass where possible
- Use a custom replacement function instead of multiple subs
- Process by operation type rather than by table

**Estimated Impact**: 10-20% reduction in processing time

---

### 7. **No Parallel Processing (MEDIUM IMPACT)**

**Problem**: Files are processed sequentially even though they're independent.

**Solution**:
- Use `multiprocessing` or `concurrent.futures` for file processing
- Process multiple TMDL/visual files in parallel (limit to CPU count)
- Careful synchronization for shared resources

**Estimated Impact**: 50-70% faster for projects with 50+ files (if using 4 cores)

---

## Quick Win Optimizations (Can implement immediately)

### 1. Use `subn()` instead of `sub()` + `findall()`
**Effort**: 30 minutes | **Impact**: 15-25% faster

### 2. Cache file content during operations
**Effort**: 1 hour | **Impact**: 30-50% faster validation

### 3. Early exit in validation when max errors reached
**Effort**: 15 minutes | **Impact**: 20% faster for validation

### 4. Compile patterns at initialization
**Effort**: 45 minutes | **Impact**: 5-10% faster

---

## Medium-term Optimizations

### 1. Implement file content cache dict
**Effort**: 2 hours | **Impact**: 30-50% faster overall

### 2. Add project metadata caching
**Effort**: 1.5 hours | **Impact**: 5% faster, better maintainability

### 3. Batch similar operations
**Effort**: 2 hours | **Impact**: 15-25% faster for multi-operations

---

## Long-term Improvements

### 1. Parallel file processing
**Effort**: 4 hours | **Impact**: 50-70% faster for large projects

### 2. Incremental updates
**Effort**: 8 hours | **Impact**: Smart caching of unchanged sections

### 3. Memory-mapped files for large projects
**Effort**: 6 hours | **Impact**: Better handling of 100MB+ files

---

## Implementation Priority

1. **Immediate** (< 30 min each):
   - Use `subn()` instead of `sub()` + `findall()`
   - Early exit validation

2. **This session** (1-2 hours):
   - File content caching
   - Pattern pre-compilation

3. **Next session**:
   - Batch operations
   - Parallel processing

4. **Future**:
   - Incremental updates
   - Advanced memory management
