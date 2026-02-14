# DAX Validation Improvements & Enhancements

## Current Issues

1. **Performance**: `validate_tmdl_syntax()` is the bottleneck (~10 seconds for large projects)
2. **Limited Information**: Errors don't include line context or suggestions
3. **No Staged Validation**: Can't skip deep validation if not needed
4. **Single Pass Inefficiency**: Opens and processes files multiple times

## Proposed Enhancements

### 1. Optimized Validation (Fast path)
- Cache file contents on project load
- Pre-compile patterns at class initialization
- Single pass through content
- Early exit option with max errors

### 2. Enhanced Error Reporting
```python
class ValidationError:
    file_path: str
    line_number: int
    column_number: int  # NEW
    error_type: str
    message: str
    context: str
    suggestion: str    # NEW - auto-fix suggestions
    severity: str      # "error" | "warning" | "info"
```

### 3. DAX-Specific Validation
- Detect common DAX mistakes:
  - Unbalanced parentheses
  - Invalid function calls
  - Missing column references
  - Circular dependencies
  - Performance anti-patterns

### 4. Semantic Analysis
- Track column/table dependencies
- Detect orphaned references
- Validate relationships
- Check measure filter context

## Implementation Plan

### Phase 1: Performance (This session)
- Pre-compile regex patterns
- Cache file content during project load
- Lazy evaluation of errors
- Max errors limit

### Phase 2: Enhanced Errors (Next)
- Add column and severity information
- Implement auto-fix suggestions
- Add context snippets

### Phase 3: DAX Intelligence (Future)
- DAX syntax validation
- Semantic analysis
- Performance checks
- Best practice enforcement

## Code Example: Optimized Validator

```python
class OptimizedValidator:
    def __init__(self):
        # Pre-compile patterns once
        self.patterns = {
            'quoted_table': re.compile(r"^table\s+'([^']+)'", re.MULTILINE),
            'unquoted_table': re.compile(r"^table\s+(\w+)\s*$", re.MULTILINE),
            'unquoted_in_dax': re.compile(r"(?<!['\w])({})(?=\s*\[)"),
        }
        self.file_cache = {}
    
    def validate(self, max_errors=None):
        """Validate with optional early exit"""
        errors = []
        error_count = 0
        
        for file_path, content in self.file_cache.items():
            for error in self._validate_file(file_path, content):
                errors.append(error)
                error_count += 1
                
                if max_errors and error_count >= max_errors:
                    yield error
                    return  # Early exit
                
                yield error
```

## Expected Impact

| Operation | Before | After | Improvement |
|-----------|--------|-------|-------------|
| Validate Small (10 tables) | 565ms | 150ms | 73% faster |
| Validate Medium (50 tables) | 2608ms | 650ms | 75% faster |
| Validate Large (200 tables) | 9961ms | 2500ms | 75% faster |

## Recommendations

1. **Immediate** (< 30 min):
   - Add max_errors parameter for early exit
   - Pre-compile regex patterns
   - Use file cache from project load

2. **Short-term** (1-2 hours):
   - Add column number and severity
   - Implement auto-fix suggestions
   - Add context snippets

3. **Medium-term** (4-6 hours):
   - Implement DAX parser
   - Add semantic analysis
   - Create performance checks

4. **Long-term**:
   - Machine learning for error pattern detection
   - Integration with Power BI service diagnostics
   - Real-time validation during editing
