import re
import os

filepath = "app/templates/allocation_visual.html"
with open(filepath, "r") as f:
    content = f.read()

new_section = """<section class="grid grid-cols-1 lg:grid-cols-3 gap-gutter">
<div class="lg:col-span-2 bg-surface-container-low cyber-border rounded-lg p-5 min-h-[500px] flex flex-col relative overflow-hidden group">
<div class="absolute inset-0 bg-gradient-to-br from-surface-container/50 to-transparent pointer-events-none z-0"></div>
<div class="flex justify-between items-center z-10 relative mb-6">
<h2 class="font-label-caps text-label-caps text-outline">1:N Allocation Telemetry</h2>
<span class="font-code-sm text-[10px] text-surface-tint bg-surface-tint/10 px-2 py-0.5 rounded border border-surface-tint/30">SAMPLE DATA (DEMO)</span>
</div>

<div class="flex-1 w-full relative z-10 flex flex-col items-center justify-center py-4 bg-surface-dim rounded-lg cyber-border overflow-y-auto">
    <!-- SOURCE SETTLEMENT -->
    <div class="w-full max-w-md border border-outline-variant bg-surface-container rounded p-3 flex flex-col items-center shadow-sm relative z-10">
        <div class="text-on-surface-variant font-label-caps text-label-caps tracking-widest text-[11px] mb-1">BANK SETTLEMENT</div>
        <div class="text-primary font-code-sm text-sm">$45,000.00 <span class="text-on-surface-variant text-xs ml-2">BULK-STL-902</span></div>
    </div>
    
    <div class="w-px h-6 bg-outline-variant flex items-end justify-center relative">
        <div class="w-2 h-2 border-b border-r border-outline-variant rotate-45 transform translate-y-1"></div>
    </div>
    
    <!-- 1:N ALLOCATION -->
    <div class="w-full max-w-md border border-primary-fixed bg-surface-container-high rounded p-4 flex flex-col shadow-md relative z-10 mint-glow">
        <div class="text-primary-fixed font-label-caps text-label-caps tracking-widest text-center border-b border-outline-variant pb-2 mb-3 text-[12px]">
            1:N ALLOCATION
        </div>
        <div class="flex flex-col gap-2 relative">
            <div class="absolute left-[15px] top-4 bottom-4 w-px bg-outline-variant"></div>
            <div class="flex items-center gap-3">
                <div class="w-4 border-b border-outline-variant"></div>
                <div class="bg-surface-dim border border-outline-variant rounded px-3 py-1.5 flex-1 flex justify-between items-center">
                    <span class="font-code-sm text-xs text-on-surface">ENTITY 1: INV-01</span>
                    <span class="font-code-sm text-xs text-secondary-fixed">$20,000.00</span>
                </div>
            </div>
            <div class="flex items-center gap-3">
                <div class="w-4 border-b border-outline-variant"></div>
                <div class="bg-surface-dim border border-outline-variant rounded px-3 py-1.5 flex-1 flex justify-between items-center">
                    <span class="font-code-sm text-xs text-on-surface">ENTITY 2: INV-02</span>
                    <span class="font-code-sm text-xs text-secondary-fixed">$15,000.00</span>
                </div>
            </div>
            <div class="flex items-center gap-3 relative">
                <div class="absolute left-[-15px] bottom-1/2 w-4 h-1/2 bg-surface-container-high"></div>
                <div class="w-4 border-b border-outline-variant"></div>
                <div class="bg-surface-dim border border-outline-variant rounded px-3 py-1.5 flex-1 flex justify-between items-center">
                    <span class="font-code-sm text-xs text-on-surface">ENTITY 3: REF-99</span>
                    <span class="font-code-sm text-xs text-secondary-fixed">$10,000.00</span>
                </div>
            </div>
        </div>
    </div>
    
    <div class="w-px h-6 bg-outline-variant flex items-end justify-center relative">
        <div class="w-2 h-2 border-b border-r border-outline-variant rotate-45 transform translate-y-1"></div>
    </div>
    
    <!-- VALIDATION MATRIX -->
    <div class="w-full max-w-md border border-outline-variant bg-surface-container rounded p-4 flex flex-col relative z-10 shadow-sm">
        <div class="text-on-surface-variant font-label-caps text-label-caps tracking-widest text-center border-b border-outline-variant/50 pb-2 mb-2 text-[11px]">
            ALLOCATION VALIDATION
        </div>
        <div class="flex flex-col gap-1 px-4">
            <div class="flex justify-between items-center font-code-sm text-xs">
                <span class="text-on-surface">Amount Conservation</span>
                <span class="text-primary-fixed">✓</span>
            </div>
            <div class="flex justify-between items-center font-code-sm text-xs">
                <span class="text-on-surface">Currency Consistency</span>
                <span class="text-primary-fixed">✓</span>
            </div>
            <div class="flex justify-between items-center font-code-sm text-xs">
                <span class="text-on-surface">Cardinality Valid</span>
                <span class="text-primary-fixed">✓</span>
            </div>
            <div class="flex justify-between items-center font-code-sm text-xs">
                <span class="text-on-surface">Duplicate Prevention</span>
                <span class="text-primary-fixed">✓</span>
            </div>
        </div>
    </div>
    
    <div class="w-px h-6 bg-outline-variant flex items-end justify-center relative">
        <div class="w-2 h-2 border-b border-r border-outline-variant rotate-45 transform translate-y-1"></div>
    </div>
    
    <!-- FINANCIAL CONTROL ENGINE -->
    <div class="w-full max-w-md border border-primary-fixed bg-surface-container-high rounded p-3 flex justify-center text-primary-fixed font-label-caps text-label-caps tracking-widest shadow-md text-[11px] relative z-10 mint-glow">
        FINANCIAL CONTROL ENGINE
    </div>

    <div class="w-px h-6 bg-outline-variant flex items-end justify-center relative">
        <div class="w-2 h-2 border-b border-r border-outline-variant rotate-45 transform translate-y-1"></div>
    </div>
    
    <!-- OUTCOME -->
    <div class="flex gap-4 w-full max-w-sm justify-center mt-2 relative z-10">
        <div class="border border-primary-fixed bg-primary-fixed/10 text-primary-fixed px-8 py-2 rounded font-label-caps text-label-caps tracking-widest flex items-center shadow-sm text-[11px]">
            MATCH
        </div>
    </div>
</div>
</div>

<!-- Secondary Comparison -->
<div class="lg:col-span-1 bg-surface-container-low cyber-border rounded-lg p-5 flex flex-col gap-6 relative overflow-hidden">
    <div class="absolute inset-0 bg-gradient-to-b from-surface-container/30 to-transparent pointer-events-none z-0"></div>
    <div class="z-10 relative h-full flex flex-col justify-center">
        <h2 class="font-label-caps text-label-caps text-outline mb-6 text-center border-b border-outline-variant/30 pb-2">Architecture Strategy</h2>
        
        <!-- BEFORE -->
        <div class="bg-surface-dim border border-error/30 rounded p-4 mb-6 relative overflow-hidden shadow-sm">
            <div class="absolute left-0 top-0 bottom-0 w-1 bg-error/70"></div>
            <div class="font-label-caps text-[11px] text-error mb-3 tracking-widest flex items-center gap-2">
                <span class="material-symbols-outlined text-[14px]">warning</span> BEFORE — 1:1 ASSUMPTION
            </div>
            <div class="flex flex-col gap-1.5 font-code-sm text-xs text-on-surface-variant ml-1">
                <div class="flex items-center gap-2 text-on-surface"><span class="w-1.5 h-1.5 bg-outline-variant rounded-full"></span> Settlement</div>
                <div class="pl-3 border-l border-outline-variant/30 ml-[3px] py-0.5 text-outline flex items-center gap-2">
                    <span class="material-symbols-outlined text-[12px]">subdirectory_arrow_right</span> repeated pairwise consumption
                </div>
                <div class="pl-3 border-l border-outline-variant/30 ml-[3px] py-0.5 text-error flex items-center gap-2">
                    <span class="material-symbols-outlined text-[12px]">subdirectory_arrow_right</span> CTRL-001 violation
                </div>
                <div class="flex items-center gap-2 text-error mt-2 bg-error/10 px-2 py-1 rounded w-fit border border-error/20">
                    <span class="material-symbols-outlined text-[14px]">gavel</span> REVIEW
                </div>
            </div>
        </div>
        
        <!-- AFTER -->
        <div class="bg-surface-dim border border-primary-fixed/30 rounded p-4 relative overflow-hidden shadow-sm">
            <div class="absolute left-0 top-0 bottom-0 w-1 bg-primary-fixed/70 glow-mint"></div>
            <div class="font-label-caps text-[11px] text-primary-fixed mb-3 tracking-widest flex items-center gap-2">
                <span class="material-symbols-outlined text-[14px]">check_circle</span> AFTER — 1:N ALLOCATION
            </div>
            <div class="flex flex-col gap-1.5 font-code-sm text-xs text-on-surface-variant ml-1">
                <div class="flex items-center gap-2 text-primary-fixed"><span class="w-1.5 h-1.5 bg-primary-fixed rounded-full shadow-[0_0_5px_1px_rgba(36,255,205,0.6)]"></span> Settlement</div>
                <div class="pl-3 border-l border-primary-fixed/30 ml-[3px] py-0.5 text-on-surface flex items-center gap-2">
                    <span class="material-symbols-outlined text-[12px] text-primary-fixed">subdirectory_arrow_right</span> validated grouped allocation
                </div>
                <div class="pl-3 border-l border-primary-fixed/30 ml-[3px] py-0.5 text-on-surface flex items-center gap-2">
                    <span class="material-symbols-outlined text-[12px] text-primary-fixed">subdirectory_arrow_right</span> conservation ✓
                </div>
                <div class="pl-3 border-l border-primary-fixed/30 ml-[3px] py-0.5 text-on-surface flex items-center gap-2">
                    <span class="material-symbols-outlined text-[12px] text-primary-fixed">subdirectory_arrow_right</span> controls ✓
                </div>
                <div class="flex items-center gap-2 text-primary-fixed mt-2 bg-primary-fixed/10 px-2 py-1 rounded w-fit border border-primary-fixed/30">
                    <span class="material-symbols-outlined text-[14px]">verified</span> MATCH
                </div>
            </div>
        </div>
        
    </div>
</div>
</section>"""

section_pattern = re.compile(r'<section class="grid grid-cols-1 lg:grid-cols-3 gap-gutter">.*?</section>', re.DOTALL)
content = section_pattern.sub(new_section, content)

# I should also ensure there's no trace of "SEMANTIC EXTRACT" or "SOURCE" or "CANDIDATE MATCH" in the file if it somehow was there, but my previous grep confirmed it's not. 
# Also remove "CANDIDATE DISCOVERY" from my last change since they want "BANK SETTLEMENT -> 1:N ALLOCATION".

with open(filepath, "w") as f:
    f.write(content)
