import os
import re
import glob

# Old -> New mappings
replacements = {
    # DEV
    "343": "322",
    "101": "122",
    "76.2%": "71.6%",
    "77.8%": "73.7%",

    # VALIDATION
    "354": "326",
    "91": "119",
    "78.6%": "72.4%",
    "76.6%": "71.0%",

    # ADVERSARIAL
    "342": "318",
    "102": "126",
    "76.0%": "70.7%",
    "76.3%": "71.5%",

    # FROZEN_UNSEEN
    "358": "339",
    "84": "103",
    "79.5%": "75.3%",
    "78.9%": "75.1%",
    
    # Text changes in FINAL_FINDINGS and FROZEN_UNSEEN_FINAL
    # Note: the baseline 15.1% remains 15.1%
    "79.0%": "75.1%", # FROZEN_UNSEEN value coverage in FROZEN_UNSEEN_FINAL.md
}

def update_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    original_content = content
    # Order matters slightly, but since these are unique strings it should be fine.
    # To be safe, we replace specific composite strings first if there are any collisions, 
    # but the numbers above are distinct enough.

    # Special handling for "317 / 450" if it exists, though `safe_merge.py` turned it into 343 / 450.
    
    for old_val, new_val in replacements.items():
        content = content.replace(old_val, new_val)
        
    if content != original_content:
        with open(filepath, "w") as f:
            f.write(content)
        print(f"Updated {filepath}")

def main():
    files_to_check = []
    
    # Root README
    if os.path.exists("README.md"):
        files_to_check.append("README.md")
        
    # Docs
    for md_file in glob.glob("docs/**/*.md", recursive=True):
        files_to_check.append(md_file)
        
    # UI Templates
    for html_file in glob.glob("app/templates/**/*.html", recursive=True):
        files_to_check.append(html_file)

    for f in files_to_check:
        update_file(f)

if __name__ == "__main__":
    main()
