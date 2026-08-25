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

for filename in os.listdir(TEMPLATE_DIR):
    if filename.endswith(".html"):
        filepath = os.path.join(TEMPLATE_DIR, filename)
        with open(filepath, "r") as f:
            content = f.read()
        
        # Replace sidebar
        if nav_regex.search(content):
            content = nav_regex.sub(universal_sidebar, content)
        elif nav_regex_2.search(content):
            content = nav_regex_2.sub(universal_sidebar, content)
            
        with open(filepath, "w") as f:
            f.write(content)

print("Done fixing sidebars")
