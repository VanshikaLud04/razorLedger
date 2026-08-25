import re
import os

filepath = "app/templates/controls_and_safety.html"
with open(filepath, "r") as f:
    content = f.read()

# 1. Replace Architecture Diagram Panel
new_diagram = """<div class="flex-1 w-full relative z-10 flex items-center justify-center p-6 bg-surface-dim">
<div class="flex flex-col items-center w-full max-w-sm gap-2 relative">
    <div class="w-full border border-outline-variant bg-surface-container rounded p-3 flex justify-center text-on-surface-variant font-label-caps text-label-caps tracking-widest relative z-10 shadow-sm">
        PROVISIONAL MATCH
    </div>
    <div class="w-px h-6 bg-outline-variant flex items-end justify-center relative">
        <div class="w-2 h-2 border-b border-r border-outline-variant rotate-45 transform translate-y-1"></div>
    </div>
    <div class="w-full border border-outline-variant bg-surface-container rounded p-3 flex justify-center text-on-surface-variant font-label-caps text-label-caps tracking-widest relative z-10 shadow-sm">
        ALLOCATED VALUE
    </div>
    <div class="w-px h-6 bg-outline-variant flex items-end justify-center relative">
        <div class="w-2 h-2 border-b border-r border-outline-variant rotate-45 transform translate-y-1"></div>
    </div>
    <div class="w-full border border-primary-fixed bg-surface-container-high rounded p-4 flex flex-col gap-3 relative z-10 mint-glow shadow-md">
        <div class="text-primary-fixed font-label-caps text-label-caps tracking-widest text-center border-b border-outline-variant pb-2 mb-1">
            FINANCIAL CONTROL ENGINE
        </div>
        <div class="flex justify-between items-center text-code-sm font-code-sm">
            <span class="text-on-surface">CTRL-001 <span class="text-on-surface-variant/50 text-[10px] ml-1">No double alloc</span></span>
            <span class="material-symbols-outlined text-[14px] text-primary-fixed">check</span>
        </div>
        <div class="flex justify-between items-center text-code-sm font-code-sm">
            <span class="text-on-surface">CTRL-002 <span class="text-on-surface-variant/50 text-[10px] ml-1">Currency consis.</span></span>
            <span class="material-symbols-outlined text-[14px] text-primary-fixed">check</span>
        </div>
        <div class="flex justify-between items-center text-code-sm font-code-sm">
            <span class="text-on-surface">CTRL-003 <span class="text-on-surface-variant/50 text-[10px] ml-1">Value conserv.</span></span>
            <div class="flex items-center gap-1">
                <span class="material-symbols-outlined text-[14px] text-primary-fixed">check</span>
                <span class="text-outline-variant">/</span>
                <span class="material-symbols-outlined text-[14px] text-error opacity-50">close</span>
            </div>
        </div>
        <div class="flex justify-center mt-1">
            <span class="text-outline-variant text-xs">...</span>
        </div>
    </div>
    <div class="w-px h-6 bg-outline-variant flex items-end justify-center relative">
        <div class="w-2 h-2 border-b border-r border-outline-variant rotate-45 transform translate-y-1"></div>
    </div>
    <div class="flex gap-4 w-full justify-center mt-1 relative z-10">
        <div class="border border-primary-fixed bg-primary-fixed/10 text-primary-fixed px-6 py-2 rounded font-label-caps text-label-caps tracking-widest flex items-center gap-2 shadow-sm">
            MATCH
        </div>
        <div class="border border-error bg-error/10 text-error px-6 py-2 rounded font-label-caps text-label-caps tracking-widest flex items-center gap-2 shadow-sm">
            REVIEW
        </div>
    </div>
</div>
</div>"""
# we replace the div with class="flex-1 min-h-[300px] w-full relative z-10 flex items-center justify-center p-4" inside the Architecture section
diag_pattern = re.compile(r'<div class="flex-1 min-h-\[300px\].*?</div>\s*</div>\s*</div>\s*</div>', re.DOTALL)
content = diag_pattern.sub(new_diagram + "\n</div>\n</div>", content)

# 2. Replace Analytics Stack
new_analytics = """<!-- Analytics Stack -->
<div class="lg:col-span-4 flex flex-col gap-6">
    <div class="bg-surface-container-low rounded-lg hairline-border p-5 flex flex-col flex-1 relative overflow-hidden">
        <h3 class="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-widest relative z-10 border-b border-outline-variant pb-3 mb-5">Financial Safety Status</h3>
        <div class="flex flex-col gap-5 relative z-10 font-code-sm text-code-sm">
            <div class="flex items-center justify-between">
                <span class="text-on-surface-variant">Controls Enforced</span>
                <span class="text-primary-fixed bg-primary-fixed/10 px-2 py-0.5 rounded hairline-border">10 / 10</span>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-on-surface-variant">Control Bypasses</span>
                <span class="text-primary">0</span>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-on-surface-variant">Over-Allocations</span>
                <span class="text-primary">0</span>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-on-surface-variant">Mixed-Currency Passes</span>
                <span class="text-primary">0</span>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-on-surface-variant">False Auto-Matches</span>
                <span class="text-primary">0.0%</span>
            </div>
        </div>
    </div>
</div>"""

analytics_pattern = re.compile(r'<!-- Analytics Stack -->.*?</div>\s*</div>\s*</div>', re.DOTALL)
content = analytics_pattern.sub(new_analytics, content)

# 3. Replace Active Control Protocols Rows
controls_data = [
    ("CTRL-001", "No double allocation"),
    ("CTRL-002", "Currency consistency"),
    ("CTRL-003", "Settlement conservation"),
    ("CTRL-004", "Gross/fee/tax/net consistency"),
    ("CTRL-005", "No negative outstanding"),
    ("CTRL-006", "Refund <= captured"),
    ("CTRL-007", "Lifecycle transition validity"),
    ("CTRL-008", "Every source record has disposition"),
    ("CTRL-009", "No duplicate event creates new allocation"),
    ("CTRL-010", "Source semantics respected")
]

rows_html = ""
for i, (cid, desc) in enumerate(controls_data):
    classes = "flex flex-col md:flex-row md:items-center px-4 py-3 hover:bg-surface-container transition-colors group"
    if i < 9:
        classes += " hairline-b"
    rows_html += f"""<!-- Row {i+1} -->
<div class="{classes}">
<div class="w-32 font-code-sm text-code-sm text-primary mb-1 md:mb-0">{cid}</div>
<div class="flex-1 font-body-md text-on-surface text-sm">{desc}</div>
<div class="w-32 flex items-center justify-end">
<span class="font-label-caps text-[10px] text-surface-tint border border-surface-tint/30 bg-surface-tint/10 px-2 py-0.5 rounded">ENFORCED</span>
</div>
</div>
"""

list_pattern = re.compile(r'<div class="flex flex-col">\s*<!-- Row 1 -->.*</div>\s*</div>', re.DOTALL)
content = list_pattern.sub(f'<div class="flex flex-col">\n{rows_html}</div>\n</div>', content)


with open(filepath, "w") as f:
    f.write(content)
