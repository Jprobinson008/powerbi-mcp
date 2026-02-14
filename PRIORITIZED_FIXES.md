# PRIORITIZED FIXES FOR ISSUES FOUND

## CRITICAL FIXES (Do First - Security/Data Loss)

### 1. Add Microseconds to Backup Timestamps
**File**: `src/powerbi_pbip_connector.py`  
**Line**: ~467  
**Current**:
```python
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
```
**Issue**: Two operations in same second create identical backup names  
**Fix**:
```python
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")  # Add microseconds
```
**Time**: 5 minutes

---

### 2. Improve External Reference Pattern for M-Code
**File**: `src/powerbi_pbip_connector.py`  
**Line**: ~160  
**Current**:
```python
external_pattern = r'\{\[entity="[^"]+",version="[^"]*"\]\}\[Data\]'
```
**Issue**: Doesn't match all dataflow reference formats  
**Fix**:
```python
# Match multiple dataflow reference patterns:
# Pattern 1: {[entity="...",version=""]}[Data]
# Pattern 2: {[entity="...",version=""]} (without [Data])
# Pattern 3: Other variations
external_patterns = [
    r'\{\[entity="[^"]+",version="[^"]*"\]\}\[Data\]',  # Standard with [Data]
    r'\{\[entity="[^"]+",version="[^"]*"\]\}(?!["\w])',  # Without [Data]
    r'dataflow\s*\.\s*\w+\s*\(\s*["\']?(\w+)["\']?\s*\)',  # Alternative format
]

for external_pattern in external_patterns:
    content_with_placeholders = re.sub(external_pattern, replace_external, content_with_placeholders)
```
**Time**: 15 minutes

---

### 3. Add File Encoding Detection with Fallback
**File**: `src/powerbi_pbip_connector.py`  
**Impact**: ~250+ file read operations  
**Current**:  
```python
with open(tmdl_file, 'r', encoding='utf-8') as f:
    content = f.read()
```
**Issue**: Crashes on non-UTF-8 files  
**Fix**:
```python
def read_file_safe(file_path: Path, encodings: List[str] = None) -> str:
    """Read file with encoding fallback"""
    if encodings is None:
        encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']  # Windows encodings
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.error(f"Error reading {file_path} with {encoding}: {e}")
            continue
    
    # Last resort: read as binary and decode with errors='replace'
    logger.warning(f"Could not read {file_path} with standard encodings, using lossy decode")
    with open(file_path, 'rb') as f:
        return f.read().decode('utf-8', errors='replace')

# Usage: Replace all `open(..., encoding='utf-8')` with `read_file_safe()`
```
**Time**: 1 hour (search/replace all occurrences)

---

### 4. Add Path Validation to Prevent Directory Traversal
**File**: `src/powerbi_pbip_connector.py`  
**New Function**:
```python
def _validate_file_in_project(self, file_path: Path) -> bool:
    """
    Validate that file_path is within current project bounds.
    Prevents directory traversal attacks.
    """
    if not self.current_project:
        return False
    
    try:
        # Resolve to absolute paths to catch symlinks and ../ tricks
        real_path = file_path.resolve()
        project_root = self.current_project.root_path.resolve()
        
        # Check if file is within project
        try:
            real_path.relative_to(project_root)
            return True
        except ValueError:
            logger.error(f"File {real_path} is outside project root {project_root}")
            return False
    except Exception as e:
        logger.error(f"Error validating file path: {e}")
        return False

# Usage in file operations:
for tmdl_file in self.current_project.tmdl_files:
    if not self._validate_file_in_project(tmdl_file):
        raise ValueError(f"File {tmdl_file} is outside project directory")
```
**Time**: 30 minutes

---

## HIGH PRIORITY FIXES (Important Correctness)

### 5. Add "Rename to Same Name" Detection
**File**: `src/powerbi_pbip_connector.py`  
**Location**: `rename_table_in_files()`, `rename_column_in_files()`, etc.  
**Add Check**:
```python
def rename_table_in_files(self, old_name: str, new_name: str) -> RenameResult:
    # NEW: Check for no-op rename
    if old_name == new_name:
        return RenameResult(
            success=False,
            message="Old name and new name are identical - no changes needed",
            files_modified=[],
            references_updated=0
        )
    
    # ... rest of function
```
**Time**: 15 minutes

---

### 6. Validate PBIP Structure on Load
**File**: `src/powerbi_pbip_connector.py`  
**Function**: `_parse_pbip_project()`  
**Add Validation**:
```python
def _validate_pbip_structure(project: PBIPProject) -> List[str]:
    """Validate PBIP has required files. Returns list of issues."""
    issues = []
    
    # Check for required semantic model files
    if not project.semantic_model_folder:
        issues.append("No .SemanticModel folder found")
    elif not list(project.semantic_model_folder.glob("definition/tables/*.tmdl")):
        issues.append("No table definitions found in .SemanticModel/definition/tables/")
    
    # Check for required report
    if not project.report_json_path:
        issues.append("No report.json found")
    
    return issues

# In _parse_pbip_project():
if not is_pbir_enhanced and not is_pbir_legacy:
    logger.warning(f"Project structure unclear - might be corrupted")
```
**Time**: 30 minutes

---

### 7. Add Validation that Column Names Have Proper Quoting
**File**: `src/powerbi_pbip_connector.py`  
**Issue**: Renamed columns in reports not checked for quote necessity  
**Add**:
```python
def _ensure_column_name_quoted_if_needed(self, column_name: str) -> str:
    """Ensure column name is quoted if it contains special characters"""
    if needs_tmdl_quoting(column_name):
        return quote_tmdl_name(column_name)
    return column_name

# Use in rename_column_in_visual_files():
new_name_safe = self._ensure_column_name_quoted_if_needed(new_name)
```
**Time**: 1 hour

---

## MEDIUM PRIORITY FIXES (Code Quality)

### 8. Extract Magic Strings to Constants
**File**: `src/powerbi_pbip_connector.py`  
**At Top of File**:
```python
# PBIR Format Constants
PBIR_LEGACY_FORMAT = "PBIR-Legacy"
PBIR_ENHANCED_FORMAT = "PBIR-Enhanced"

# File Patterns
PATTERN_TMDL = "*.tmdl"
PATTERN_TDM = "*.tmd"
PATTERN_CULTURES = "*.tmdl"

# Folder Names
FOLDER_SEMANTIC_MODEL_SUFFIX = ".SemanticModel"
FOLDER_REPORT_SUFFIX = ".Report"
FOLDER_DEFINITION = "definition"
FOLDER_PAGES = "pages"
FOLDER_VISUALS = "visuals"
FOLDER_TABLES = "tables"
FOLDER_CULTURES = "cultures"

# File Names
FILE_REPORT_JSON = "report.json"
FILE_PAGES_JSON = "pages.json"
FILE_PAGE_JSON = "page.json"
FILE_VISUAL_JSON = "visual.json"
FILE_DIAGRAM_LAYOUT = "diagramLayout.json"
```
**Time**: 1 hour

---

### 9. Add Column Number to Validation Errors
**File**: `src/powerbi_pbip_connector.py`  
**Modify ValidationError**:
```python
@dataclass
class ValidationError:
    file_path: str
    line_number: int
    column_number: int = 0  # NEW
    error_type: str
    message: str
    context: str
    severity: str = "error"  # NEW: "error" | "warning" | "info"
    suggestion: str = ""  # NEW: auto-fix suggestion
```

**Time**: 2 hours

---

### 10. Better M-Code Reserved Words
**File**: `src/powerbi_pbip_connector.py`  
**Current**: Incomplete TMDL_RESERVED_WORDS set  
**Expand to**:
```python
TMDL_RESERVED_WORDS = {
    'table', 'column', 'measure', 'relationship', 'partition', 'hierarchy', 'level',
    'annotation', 'expression', 'from', 'to', 'true', 'false', 'null', 'blank',
    'calculated', 'variable', 'and', 'or', 'not', 'in', 'if', 'then', 'else',
    'datetime', 'date', 'time', 'int', 'real', 'text', 'logical',
    'select', 'where', 'order', 'by', 'let', 'in', 'as',  # More Power Query
}
```
**Time**: 15 minutes

---

## IMPLEMENTATION PRIORITY TIMELINE

### Phase 1: CRITICAL (4 hours - Do immediately)
1. Backup timestamp fix (5 min)
2. External reference pattern improvement (15 min)
3. File encoding detection (1 hr)
4. Path validation (30 min)
5. Testing (2 hrs)

### Phase 2: HIGH (2 hours - This week)
6. No-op rename detection (15 min)
7. PBIP structure validation (30 min)
8. Column quoting validation (1 hr)
9. Testing (15 min)

### Phase 3: MEDIUM (3 hours - This sprint)
10. Extract magic strings (1 hr)
11. Add column number to errors (2 hrs)

### Phase 4: LOW (1 hour - Next sprint)
12. Expand reserved words (15 min)

**Total**: 10 hours to fully address all issues

---

## TESTING ADDITIONS NEEDED

After each fix, add tests for:
- ✓ Rapid succession operations (backup collision)
- ✓ Files with non-UTF-8 encoding
- ✓ Symlinks and path traversal attempts  
- ✓ Renaming to same name
- ✓ Corrupted PBIP files
- ✓ M-Code with various dataflow formats
- ✓ Very deep directory structures

Each test: 15-30 minutes to write and validate
