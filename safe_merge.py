import os
import re

TEMPLATE_DIR = "app/templates"

# Universal exact sidebar
universal_sidebar = """<nav class="bg-surface-container-lowest flex flex-col h-screen fixed left-0 top-0 w-64 border-r border-outline-variant z-50">
    <div class="p-margin-desktop border-b border-outline-variant">
        <div class="flex items-center gap-3">
            <h1 class="font-headline-md text-headline-md font-bold text-primary">RazorLedger</h1>
        </div>
    </div>
    <div class="flex-1 py-unit flex flex-col gap-1 overflow-y-auto px-unit">
        <a class="flex items-center gap-3 px-4 py-3 rounded-DEFAULT text-on-surface-variant font-label-caps text-label-caps hover:bg-surface-container-high transition-colors" href="/ui/dashboard">
            <span class="material-symbols-outlined">dashboard</span>
            Dashboard
        </a>
        <a class="flex items-center gap-3 px-4 py-3 rounded-DEFAULT text-on-surface-variant font-label-caps text-label-caps hover:bg-surface-container-high transition-colors" href="/ui/reconciliation_run">
            <span class="material-symbols-outlined">account_balance</span>
            Reconciliation Run
        </a>
        <a class="flex items-center gap-3 px-4 py-3 rounded-DEFAULT text-on-surface-variant font-label-caps text-label-caps hover:bg-surface-container-high transition-colors" href="/ui/decision_detail">
            <span class="material-symbols-outlined">queue</span>
            Forensic Review
        </a>
        <a class="flex items-center gap-3 px-4 py-3 rounded-DEFAULT text-on-surface-variant font-label-caps text-label-caps hover:bg-surface-container-high transition-colors" href="/ui/allocation_visual">
            <span class="material-symbols-outlined">analytics</span>
            Allocation Visual
        </a>
        <a class="flex items-center gap-3 px-4 py-3 rounded-DEFAULT text-on-surface-variant font-label-caps text-label-caps hover:bg-surface-container-high transition-colors" href="/ui/controls_and_safety">
            <span class="material-symbols-outlined">shield</span>
            Safety & Controls
        </a>
        <a class="flex items-center gap-3 px-4 py-3 rounded-DEFAULT text-on-surface-variant font-label-caps text-label-caps hover:bg-surface-container-high transition-colors" href="/ui/model_performance">
            <span class="material-symbols-outlined">assessment</span>
            Model Performance
        </a>
    </div>
</nav>"""

nav_regex = re.compile(r'<nav class="bg-surface-container-lowest flex flex-col h-screen fixed left-0 top-0 w-64 border-r border-outline-variant z-50">.*?</nav>', re.DOTALL)
nav_regex_2 = re.compile(r'<nav class="flex flex-col gap-xs flex-1 overflow-y-auto px-sm">.*?</nav>', re.DOTALL)
nav_regex_3 = re.compile(r'<nav[^>]*>.*?</nav>', re.DOTALL)  # Fallback

# 1. Rename match_review_queue to decision_detail
if os.path.exists(os.path.join(TEMPLATE_DIR, "match_review_queue.html")):
    # we overwrite the 46-byte decision_detail.html
    os.rename(os.path.join(TEMPLATE_DIR, "match_review_queue.html"), os.path.join(TEMPLATE_DIR, "decision_detail.html"))

# 2. Fix the files
def fix_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()
    
    # Update sidebar
    if nav_regex.search(content):
        content = nav_regex.sub(universal_sidebar, content)
    elif nav_regex_2.search(content):
        content = nav_regex_2.sub(universal_sidebar, content)
    else:
        # manual fallback for sidebars we missed
        content = nav_regex_3.sub(universal_sidebar, content, count=1)
        
    # Apply exact canonical metrics if present
    content = content.replace("80.2%", "76.2%")
    content = content.replace("84.7%", "79.5%")
    content = content.replace("92.6%", "78.6%")
    content = content.replace("70.4%", "76.2%")
    content = content.replace("317 / 450", "343 / 450")
    
    # Ensure active states are visually removed from the universal block, or we can use a script to add the active state on the client side based on window.location!
    # That's much safer than hardcoding it per file via python!
    active_js = """<script>
    document.addEventListener("DOMContentLoaded", function() {
        const path = window.location.pathname;
        const links = document.querySelectorAll("nav a");
        links.forEach(link => {
            if (link.getAttribute("href") === path) {
                link.classList.remove("text-on-surface-variant", "hover:bg-surface-container-high");
                link.classList.add("text-primary-fixed", "bg-on-primary-fixed-variant/10", "border-r-2", "border-primary-fixed");
            }
        });
    });
    </script>
    """
    if "</body>" in content:
        content = content.replace("</body>", f"{active_js}\n</body>")
        
    with open(filepath, "w") as f:
        f.write(content)

for filename in ["dashboard.html", "reconciliation_run.html", "decision_detail.html", "controls_and_safety.html", "model_performance.html"]:
    fix_file(os.path.join(TEMPLATE_DIR, filename))

# 3. Create allocation_visual.html if it's the broken stub
with open(os.path.join(TEMPLATE_DIR, "allocation_visual.html"), "r") as f:
    av_content = f.read()
if len(av_content) < 500: # Broken stub
    # Copy dashboard but clear main content
    with open(os.path.join(TEMPLATE_DIR, "dashboard.html"), "r") as f:
        dash = f.read()
    # Strip main content and replace with placeholder
    main_regex = re.compile(r'<main[^>]*>.*?</main>', re.DOTALL)
    av_new = main_regex.sub('<main class="flex-1 overflow-y-auto p-margin-mobile md:p-margin-desktop"><h2 class="font-headline-lg-mobile md:font-headline-lg text-primary tracking-tight mb-2">1:N Allocation Visual</h2><p class="text-on-surface-variant font-body-md">Dedicated home for the 1:N structural grouping visualization.</p></main>', dash)
    with open(os.path.join(TEMPLATE_DIR, "allocation_visual.html"), "w") as f:
        f.write(av_new)

print("Safe merge completed.")
