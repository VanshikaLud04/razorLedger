import re

filepath = "app/templates/allocation_visual.html"
with open(filepath, "r") as f:
    content = f.read()

new_visual = """<div class="lg:col-span-2 bg-surface-container-low cyber-border rounded-lg p-5 min-h-[500px] flex flex-col relative overflow-hidden group">
<div class="absolute inset-0 bg-gradient-to-br from-surface-container/50 to-transparent pointer-events-none z-0"></div>
<div class="flex justify-between items-center z-10 relative mb-6">
<h2 class="font-label-caps text-label-caps text-outline">1:N Allocation Telemetry</h2>
<span class="font-code-sm text-[10px] text-surface-tint bg-surface-tint/10 px-2 py-0.5 rounded border border-surface-tint/30">SAMPLE DATA (DEMO)</span>
</div>

<div class="flex-1 w-full relative z-10 flex flex-col items-center justify-center py-4 bg-surface-dim rounded-lg cyber-border overflow-y-auto">
    
    <!-- SOURCE SETTLEMENT -->
    <div class="w-full max-w-md border border-outline-variant bg-surface-container rounded p-3 flex flex-col items-center shadow-sm relative z-10">
        <div class="text-on-surface-variant font-label-caps text-label-caps tracking-widest text-[11px] mb-1">SOURCE SETTLEMENT</div>
        <div class="text-primary font-code-sm text-sm">$45,000.00 <span class="text-on-surface-variant text-xs ml-2">BULK-STL-902</span></div>
    </div>
    
    <!-- Arrow down -->
    <div class="w-px h-6 bg-outline-variant flex items-end justify-center relative">
        <div class="w-2 h-2 border-b border-r border-outline-variant rotate-45 transform translate-y-1"></div>
    </div>
    
    <!-- CANDIDATE DISCOVERY -->
    <div class="w-full max-w-md border border-outline-variant bg-surface-container rounded p-3 flex justify-center text-on-surface-variant font-label-caps text-label-caps tracking-widest shadow-sm text-[11px] relative z-10">
        CANDIDATE DISCOVERY
    </div>

    <!-- Arrow down -->
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
    
    <!-- Arrow down -->
    <div class="w-px h-6 bg-outline-variant flex items-end justify-center relative">
        <div class="w-2 h-2 border-b border-r border-outline-variant rotate-45 transform translate-y-1"></div>
    </div>
    
    <!-- VALIDATION MATRIX -->
    <div class="w-full max-w-md border border-outline-variant bg-surface-container rounded p-4 flex flex-col relative z-10 shadow-sm">
        <div class="text-on-surface-variant font-label-caps text-label-caps tracking-widest text-center border-b border-outline-variant/50 pb-2 mb-2 text-[11px]">
            VALIDATION MATRIX
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
    
    <!-- Arrow down -->
    <div class="w-px h-6 bg-outline-variant flex items-end justify-center relative">
        <div class="w-2 h-2 border-b border-r border-outline-variant rotate-45 transform translate-y-1"></div>
    </div>
    
    <!-- FINANCIAL CONTROL ENGINE -->
    <div class="w-full max-w-md border border-primary-fixed bg-surface-container-high rounded p-3 flex justify-center text-primary-fixed font-label-caps text-label-caps tracking-widest shadow-md text-[11px] relative z-10 mint-glow">
        FINANCIAL CONTROL ENGINE
    </div>

    <!-- Arrow down (split) -->
    <div class="w-px h-6 bg-outline-variant flex items-end justify-center relative">
        <div class="w-2 h-2 border-b border-r border-outline-variant rotate-45 transform translate-y-1"></div>
    </div>
    
    <!-- OUTCOME -->
    <div class="flex gap-4 w-full max-w-sm justify-center mt-2 relative z-10">
        <div class="border border-primary-fixed bg-primary-fixed/10 text-primary-fixed px-8 py-2 rounded font-label-caps text-label-caps tracking-widest flex items-center shadow-sm text-[11px]">
            MATCH
        </div>
        <div class="border border-error bg-error/10 text-error px-8 py-2 rounded font-label-caps text-label-caps tracking-widest flex items-center shadow-sm text-[11px] opacity-50">
            REVIEW
        </div>
    </div>
    
</div>
</div>"""

# we replace the div with class="lg:col-span-2 ..." up to the next lg:col-span-1
canvas_pattern = re.compile(r'<div class="lg:col-span-2 .*?<!-- Abstention Log / Match List', re.DOTALL)
content = canvas_pattern.sub(new_visual + "\n<!-- Abstention Log / Match List", content)

with open(filepath, "w") as f:
    f.write(content)
