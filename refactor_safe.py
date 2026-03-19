import re
import ast

file_path = "d:/pcdownload/DataForge_v3-main/DataForge_v3-main/services/web/app.py"
with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

# Replace _load("...") with _load(upload_id, "...")
code = re.sub(r'_load\(\s*(["\'][a-zA-Z0-9_-]+["\'])\s*\)', r'_load(upload_id, \1)', code)

# Replace _save("...", obj) with _save(upload_id, "...", obj)
code = re.sub(r'_save\(\s*(["\'][a-zA-Z0-9_-]+["\'])\s*,\s*([^)]+)\)', r'_save(upload_id, \1, \2)', code)

# Replace _path("...") with _upath(upload_id, "...")
code = re.sub(r'_path\(\s*(["\'][a-zA-Z0-9_-]+["\'])\s*\)', r'_upath(upload_id, \1)', code)

# Replace session.get("filename", "") with up.filename
# We assume `up = db.session.get(Upload, upload_id)` will be available, or we just use a helper
code = re.sub(r'session\[["\']filename["\']\]', r'""', code)
code = re.sub(r'session\.get\(["\']filename["\'],?\s*["\']?[^)]*["\']?\)', r'_get_filename(upload_id)', code)

file_helper = """
def _get_filename(upload_id: int) -> str:
    up = db.session.get(Upload, upload_id)
    return up.filename if up else "Dataset"
"""
if "_get_filename" not in code:
    code = code.replace("def _require_df", file_helper + "\ndef _require_df")

# Replace @_require_df def my_func(): -> def my_func(upload_id):
def add_uid(match):
    decorator = match.group(1)
    func_name = match.group(2)
    params = match.group(3)
    # Check if upload_id is already there
    if "upload_id" in params:
        return match.group(0)
    if not params.strip():
        new_params = "upload_id"
    else:
        new_params = "upload_id, " + params
    return f"{decorator}\ndef {func_name}({new_params}):"

code = re.sub(r'(@_require_df[^\n]*\n)def (\w+)\s*\((.*?)\):', add_uid, code)

# Replace specific `upload_id = ...` fetches that relied on session
# e.g. upload_id = session.get("db_upload_id") -> upload_id = _get_upload_id()
code = re.sub(r'upload_id\s*=\s*session\.get\(["\']db_upload_id["\']\)', 'upload_id = _get_upload_id()', code)
code = re.sub(r'upload_id\s*=\s*session\.get\(["\']db_upload_id["\'],\s*None\)', 'upload_id = _get_upload_id()', code)
code = re.sub(r'upload_id\s*=\s*body\.get\(["\']upload_id["\']\)\s*or\s*session\.get\(["\']db_upload_id["\']\)', 'upload_id = _get_upload_id()', code)


with open(file_path, "w", encoding="utf-8") as f:
    f.write(code)

print("done")
