import re

filepath = "app/templates/controls_and_safety.html"
with open(filepath, "r") as f:
    content = f.read()

# 1. Change layout width
content = content.replace('lg:col-span-8', 'lg:col-span-7')
content = content.replace('lg:col-span-4', 'lg:col-span-5')

# 2. Remove "Stat 2" completely
stat2_regex = re.compile(r'<!-- Stat 2 -->.*?</div>\s*</div>', re.DOTALL)
content = stat2_regex.sub('', content)

# Also fix the unclosed divs if any. In the original, Stat 2 was followed by `</div></div>`. Wait.
# Let's just be very precise.
# In the current file:
#         </div>
#     </div>
# </div>
# <!-- Stat 2 -->
# <div class="bg-surface-container-low rounded-lg hairline-border p-4 flex flex-col justify-between flex-1 relative overflow-hidden">
# ...
# </div>
# </div>
# </div>
# <!-- Controls List -->
#
# Actually, the grid container closes after Stat 2. Let's do string replacement to be safe.

# Let's extract the exact grid block to rewrite it.
grid_regex = re.compile(r'<!-- Architecture Diagram -->.*?<!-- Controls List -->', re.DOTALL)
match = grid_regex.search(content)
if match:
    # Rewrite the whole grid section safely
    new_grid = """<!-- Architecture Diagram -->
<div class="lg:col-span-7 bg-surface-container-low rounded-lg hairline-border p-4 flex flex-col gap-4 relative overflow-hidden group">
<div class="absolute inset-0 bg-gradient-to-br from-surface-container/50 to-transparent pointer-events-none z-0"></div>
<div class="flex justify-between items-center z-10 relative">
<h3 class="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-widest">Architecture: Control Gate</h3>
<span class="font-code-sm text-code-sm text-surface-tint bg-surface-tint/10 px-2 py-0.5 rounded hairline-border">ACTIVE</span>
</div>
<div class="flex-1 w-full relative z-10 flex items-center justify-center p-8 py-12 bg-surface-dim rounded-lg cyber-border">
<div class="flex flex-col items-center w-full max-w-md gap-3 relative">
    <div class="w-full border border-outline-variant bg-surface-container rounded-md p-4 flex justify-center text-on-surface-variant font-label-caps text-label-caps tracking-widest relative z-10 shadow-sm text-[11px]">
        PROVISIONAL MATCH
    </div>
    <div class="w-px h-8 bg-outline-variant flex items-end justify-center relative">
        <div class="w-2 h-2 border-b border-r border-outline-variant rotate-45 transform translate-y-1"></div>
    </div>
    <div class="w-full border border-outline-variant bg-surface-container rounded-md p-4 flex justify-center text-on-surface-variant font-label-caps text-label-caps tracking-widest relative z-10 shadow-sm text-[11px]">
        ALLOCATED VALUE
    </div>
    <div class="w-px h-8 bg-outline-variant flex items-end justify-center relative">
        <div class="w-2 h-2 border-b border-r border-outline-variant rotate-45 transform translate-y-1"></div>
    </div>
    <div class="w-full border border-primary-fixed bg-surface-container-high rounded-md p-5 flex flex-col gap-3 relative z-10 mint-glow shadow-md">
        <div class="flex flex-col items-center border-b border-outline-variant pb-3 mb-2">
            <div class="text-primary-fixed font-label-caps text-label-caps tracking-widest text-[12px]">FINANCIAL CONTROL ENGINE</div>
            <div class="text-on-surface-variant/70 font-code-sm text-[10px] mt-1 tracking-wider uppercase">INDEPENDENT VERIFICATION</div>
        </div>
        <div class="flex justify-between items-center text-code-sm font-code-sm px-2">
            <span class="text-on-surface">CTRL-001 <span class="text-on-surface-variant/50 text-[11px] ml-2">No double alloc</span></span>
            <span class="material-symbols-outlined text-[16px] text-primary-fixed">check</span>
        </div>
        <div class="flex justify-between items-center text-code-sm font-code-sm px-2">
            <span class="text-on-surface">CTRL-002 <span class="text-on-surface-variant/50 text-[11px] ml-2">Currency consis.</span></span>
            <span class="material-symbols-outlined text-[16px] text-primary-fixed">check</span>
        </div>
        <div class="flex justify-between items-center text-code-sm font-code-sm px-2">
            <span class="text-on-surface">CTRL-003 <span class="text-on-surface-variant/50 text-[11px] ml-2">Value conserv.</span></span>
            <span class="material-symbols-outlined text-[16px] text-primary-fixed">check</span>
        </div>
        <div class="flex justify-between items-center text-code-sm font-code-sm px-2">
            <span class="text-on-surface">CTRL-004 <span class="text-on-surface-variant/50 text-[11px] ml-2">Gross/net consis.</span></span>
            <span class="material-symbols-outlined text-[16px] text-primary-fixed">check</span>
        </div>
        <div class="flex justify-center mt-2 opacity-50">
            <div class="w-1 h-1 rounded-full bg-outline-variant mx-1"></div>
            <div class="w-1 h-1 rounded-full bg-outline-variant mx-1"></div>
            <div class="w-1 h-1 rounded-full bg-outline-variant mx-1"></div>
        </div>
    </div>
    <div class="w-px h-8 bg-outline-variant flex items-end justify-center relative">
        <div class="w-2 h-2 border-b border-r border-outline-variant rotate-45 transform translate-y-1"></div>
    </div>
    <div class="flex gap-6 w-full justify-center mt-2 relative z-10">
        <div class="flex flex-col items-center gap-1">
            <div class="text-outline-variant font-code-sm text-[10px]">PASS</div>
            <div class="border border-primary-fixed bg-primary-fixed/10 text-primary-fixed px-8 py-3 rounded-md font-label-caps text-label-caps tracking-widest flex items-center shadow-sm text-[11px]">
                MATCH
            </div>
        </div>
        <div class="flex flex-col items-center gap-1">
            <div class="text-outline-variant font-code-sm text-[10px]">FAIL</div>
            <div class="border border-error bg-error/10 text-error px-8 py-3 rounded-md font-label-caps text-label-caps tracking-widest flex items-center shadow-sm text-[11px]">
                REVIEW
            </div>
        </div>
    </div>
</div>
</div>
</div>
<!-- Analytics Stack -->
<div class="lg:col-span-5 flex flex-col gap-6">
    <div class="bg-surface-container-low rounded-lg hairline-border p-6 flex flex-col flex-1 relative overflow-hidden">
        <h3 class="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-widest relative z-10 border-b border-outline-variant pb-4 mb-6">Financial Safety Status</h3>
        <div class="flex flex-col gap-6 relative z-10 font-code-sm text-code-sm text-[14px]">
            <div class="flex items-center justify-between">
                <span class="text-on-surface-variant uppercase">Controls Enforced</span>
                <span class="text-primary-fixed bg-primary-fixed/10 px-2 py-1 rounded hairline-border font-bold">10 / 10</span>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-on-surface-variant uppercase">Control Bypasses</span>
                <span class="text-primary font-bold">0</span>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-on-surface-variant uppercase">Over-Allocations</span>
                <span class="text-primary font-bold">0</span>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-on-surface-variant uppercase">Mixed-Currency Passes</span>
                <span class="text-primary font-bold">0</span>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-on-surface-variant uppercase">False Auto-Matches</span>
                <span class="text-primary font-bold">0.0%</span>
            </div>
        </div>
    </div>
</div>
</div>
<!-- Controls List -->"""
    content = grid_regex.sub(new_grid, content)

with open(filepath, "w") as f:
    f.write(content)
