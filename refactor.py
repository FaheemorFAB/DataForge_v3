import re
from pathlib import Path

app_path = Path("d:/pcdownload/DataForge_v3-main/DataForge_v3-main/services/web/app.py")
content = app_path.read_text(encoding="utf-8")

# 1. Update _load("key") -> _load(upload_id, "key")
# But only if it's not already _load(upload_id, "key")
content = re.sub(r'_load\(\s*(["\'][^"\']+["\'])\s*\)', r'_load(upload_id, \1)', content)

# 2. Update _save("key", obj) -> _save(upload_id, "key", obj)
content = re.sub(r'_save\(\s*(["\'][^"\']+["\'])\s*,\s*([^)]+)\s*\)', r'_save(upload_id, \1, \2)', content)

# 3. Update _path("key") -> _upath(upload_id, "key")
content = re.sub(r'_path\(\s*(["\'][^"\']+["\'])\s*\)', r'_upath(upload_id, \1)', content)

# 4. _db_log_analysis updates
content = content.replace('def _db_log_analysis(type_: str, summary: str = ""):', 
                          'def _db_log_analysis(upload_id: int, type_: str, summary: str = ""):')
# Replace usages of _db_log_analysis
content = re.sub(r'_db_log_analysis\(\s*(["\'][^"\']+["\'])\s*,', r'_db_log_analysis(upload_id, \1,', content)

# 5. Fix _db_log_analysis internal logic (remove session)
internal_log = """def _db_log_analysis(upload_id: int, type_: str, summary: str = ""):
    \"\"\"Save an analysis record to DB and push real-time WS event.\"\"\"
    if not current_user.is_authenticated:
        return
    try:
        an = Analysis(
            user_id   = current_user.id,
            upload_id = upload_id,
            type      = type_,
            summary   = summary,
        )"""
content = re.sub(r'def _db_log_analysis\(upload_id: int, type_: str, summary: str = ""\):[\s\S]*?summary\s*=\s*summary,\s*\)', internal_log, content)

# 6. Remove session.get("db_upload_id") assignments and retrievals
# We will just remove the lines that set it
content = re.sub(r'\s*session\[["\']db_upload_id["\']\] = .*?\n', '\n', content)
content = re.sub(r'\s*session\[["\']filename["\']\] = .*?\n', '\n', content)
content = re.sub(r'\s*session\[["\']profile["\']\] = .*?\n', '\n', content)

content = re.sub(r'upload_id = session\.get\(["\']db_upload_id["\']\)', '', content)
content = re.sub(r'upload_id = session\.get\(["\']db_upload_id["\'], None\)', '', content)
content = re.sub(r'upload_id = body\.get\(["\']upload_id["\']\) or session\.get\(["\']db_upload_id["\']\)', 'upload_id = _get_upload_id()', content)

# 7. Add `upload_id` parameter to routes decorated with `@_require_df`
# Because our wrapper already does `return fn(upload_id=upload_id, *args, **kwargs)`
def add_upload_id_param(match):
    decorator_block = match.group(1)
    def_line = match.group(2)
    func_name = match.group(3)
    params = match.group(4)
    if 'upload_id' not in params:
        if params.strip() == '':
            new_def = f"def {func_name}(upload_id):"
        else:
            new_def = f"def {func_name}(upload_id, {params}):"
        return f"{decorator_block}\n{new_def}"
    return match.group(0)

content = re.sub(r'(@_require_df[\s\S]*?)\ndef (\w+)\((.*?)\):', add_upload_id_param, content)

# 8. Replace `session.get("filename", "")` and similar with dynamic fetch or just `""`
# Usually, we need the Upload object. `_get_upload_or_403` fetches it.
# Inside `@_require_df` routes, we can just do:
# `up = db.session.get(Upload, upload_id); filename = up.filename if up else ""`
# We'll just replace `session.get("filename", "...")` with `_get_filename(upload_id)`
file_helper = """
def _get_filename(upload_id: int) -> str:
    up = db.session.get(Upload, upload_id)
    return up.filename if up else "Dataset"
"""
if "_get_filename" not in content:
    content = content.replace('def _require_df', file_helper + '\ndef _require_df')

content = re.sub(r'session\[["\']filename["\']\]', r'_get_filename(upload_id)', content)
content = re.sub(r'session\.get\(["\']filename["\'][^)]*\)', r'_get_filename(upload_id)', content)

# We need to make sure _load doesn't conflict with its definition
# Find def _load(upload_id: int, key: str): and ensure it replaced correctly
content = content.replace("def _load(upload_id, upload_id: int, key: str):", "def _load(upload_id: int, key: str):")
content = content.replace("def _save(upload_id, upload_id: int, key: str,", "def _save(upload_id: int, key: str,")
content = content.replace("def _db_log_analysis(upload_id, upload_id: int,", "def _db_log_analysis(upload_id: int,")

app_path.write_text(content, encoding="utf-8")
print("Refactored successfully!")
