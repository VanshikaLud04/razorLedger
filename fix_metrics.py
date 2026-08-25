import os
import glob
import json

# Inverse mapping from update_metrics.py
replacements = {
    "322": "343",
    "122": "101",
    "71.6%": "76.2%",
    "73.7%": "77.8%",
    "326": "354",
    "119": "91",
    "72.4%": "78.6%",
    "71.0%": "76.6%",
    "318": "342",
    "126": "102",
    "70.7%": "76.0%",
    "71.5%": "76.3%",
    "339": "358",
    "103": "84",
    "75.3%": "79.5%",
    "75.1%": "78.9%",
}

# Values for JSON/CSV (floating points)
json_replacements = {
    "0.7155555555555555": "0.7622222222222222",
    "0.7366394153314836": "0.7783165242367975",
    "0.8341968911917098": "0.8650693568726355", # F1
    
    "0.7244444444444444": "0.7866666666666666",
    "0.7101577004439532": "0.7660183423555693",
    "0.8402061855670103": "0.8805970149253731",
    
    "0.7066666666666667": "0.76",
    "0.7146246434051902": "0.763339109431325",
    "0.828125": "0.8636363636363636",
    
    "0.7533333333333333": "0.7955555555555556",
    "0.751334193632932": "0.7896856284884436",
    "0.8593155893536121": "0.8861386138613861",
}

def update_file(filepath, rep_dict):
    if not os.path.exists(filepath): return
    with open(filepath, "r") as f:
        content = f.read()

    for old_val, new_val in rep_dict.items():
        content = content.replace(old_val, new_val)
        
    with open(filepath, "w") as f:
        f.write(content)
    print(f"Updated {filepath}")

# Process text files
for f in ["README.md"] + glob.glob("docs/**/*.md", recursive=True) + glob.glob("app/templates/**/*.html", recursive=True):
    update_file(f, replacements)

# Process JSON/CSV files
for f in glob.glob("reports/final/*.*", recursive=True):
    # apply integer replacements first
    update_file(f, {"322": "343", "122": "101", "326": "354", "119": "91", "318": "342", "126": "102", "339": "358", "103": "84"})
    # apply float replacements
    update_file(f, json_replacements)

