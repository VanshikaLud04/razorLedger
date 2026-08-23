---
name: RazorLedger Institutional System
colors:
  surface: '#041426'
  surface-dim: '#041426'
  surface-bright: '#2b3a4e'
  surface-container-lowest: '#000f20'
  surface-container-low: '#0c1c2e'
  surface-container: '#112033'
  surface-container-high: '#1c2b3e'
  surface-container-highest: '#273649'
  on-surface: '#d4e4fd'
  on-surface-variant: '#bfc9c3'
  inverse-surface: '#d4e4fd'
  inverse-on-surface: '#223144'
  outline: '#89938e'
  outline-variant: '#404945'
  surface-tint: '#94d3bd'
  primary: '#94d3bd'
  on-primary: '#00382b'
  primary-container: '#67a590'
  on-primary-container: '#00392b'
  inverse-primary: '#2a6957'
  secondary: '#abc7ff'
  on-secondary: '#002f66'
  secondary-container: '#005cbc'
  on-secondary-container: '#c8d9ff'
  tertiary: '#a8c8ff'
  on-tertiary: '#003061'
  tertiary-container: '#6d9ae0'
  on-tertiary-container: '#003162'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#aff0d8'
  primary-fixed-dim: '#94d3bd'
  on-primary-fixed: '#002118'
  on-primary-fixed-variant: '#08513f'
  secondary-fixed: '#d7e2ff'
  secondary-fixed-dim: '#abc7ff'
  on-secondary-fixed: '#001b3f'
  on-secondary-fixed-variant: '#00458f'
  tertiary-fixed: '#d5e3ff'
  tertiary-fixed-dim: '#a8c8ff'
  on-tertiary-fixed: '#001b3c'
  on-tertiary-fixed-variant: '#074687'
  background: '#041426'
  on-background: '#d4e4fd'
  surface-variant: '#273649'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  mono-data:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  mono-label:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 12px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 12px
  margin: 16px
  container-max: 1440px
---

## Brand & Style

The design system is engineered for high-stakes financial reconciliation where precision is the primary value proposition. The brand personality is authoritative, immutable, and hyper-functional, drawing inspiration from Bloomberg Terminal’s density and Stripe’s technical clarity.

The visual style is **Corporate / Modern** with a lean toward **Technical Minimalism**. It prioritizes information density over aesthetic whitespace. Every pixel must serve a functional purpose, facilitating rapid pattern recognition across thousands of ledger entries. The emotional response is one of "Proof-of-Safety"—the user should feel that the system is an infallible auditor that never hides data behind "fluff."

**Key Principles:**
- **Evidence Transparency:** All data states (matched, pending, failed) are visually distinct and immediate.
- **Immutable Financial Controls:** UI elements for sensitive actions use heavy-weighted "Enforced" states to signal finality.
- **High-Density Utility:** Maximizing the data-to-ink ratio to allow reconciliation of complex datasets without excessive scrolling.

## Colors

The palette is anchored in a high-contrast dark mode to reduce eye strain during long reconciliation sessions. The updated palette shifts toward a more nuanced, professional tonal range.

- **Primary (MATCH):** A refined Sage Green (#67a590) is used for successful reconciliations and "Balanced" states. It serves as the psychological "Go" signal, now with a softer, more sophisticated presence.
- **Secondary (ACTION/LINK):** A deep Intellectual Blue (#296fd0) handles primary navigational actions and interactive data points.
- **Tertiary (SYSTEM):** A lighter Sky Blue (#6e9be1) provides accenting for informational highlights and system-level status indicators.
- **Neutral:** Deep Slate Blue (#3a495d) provides a low-energy backdrop, ensuring that status colors "pop" against the dark UI and maintaining structural clarity.
- **Critical (CONTROL FAIL):** Standardized red remains reserved exclusively for ledger breaks, integrity failures, or security breaches.

## Typography

This design system utilizes a dual-font strategy to separate interface logic from financial data.

- **Inter:** Used for all navigational elements, labels, and instructional text. It provides the necessary readability for complex UI layouts.
- **JetBrains Mono:** The "Source of Truth" font. It is strictly enforced for all monetary values, Transaction IDs, Hash strings, and timestamps. Tabular figures ensure that columns of numbers align perfectly for vertical scanning.

**Scaling:** On mobile, font sizes remain largely static to preserve data density; however, `display-lg` should scale down to 24px to ensure dashboard totals remain visible on smaller viewports.

## Layout & Spacing

The layout follows a **Fixed-Fluid Hybrid** model. Navigation and sidebars are fixed-width to ensure tool accessibility, while the central data-grid is fluid to maximize screen real estate.

- **Grid:** A 12-column grid is used for the dashboard, but the primary ledger view utilizes a 100% width CSS Grid for multi-column reconciliation.
- **Density:** We use a 4px base unit. Cell padding in tables is restricted to 8px (y-axis) and 12px (x-axis) to fit as many rows as possible above the fold.
- **Responsive:** On tablet and mobile, non-essential columns are hidden via a priority-ranking system (e.g., Transaction ID and Amount remain, while "Source Metadata" moves to a drill-down view).

## Elevation & Depth

To maintain a "technical tool" feel, this design system avoids soft shadows and organic depth. Instead, it uses **Tonal Layers** and **Low-contrast outlines**.

- **Level 0 (Background):** The base work surface, utilizing the deepest neutral tones.
- **Level 1 (Surface):** Used for primary data containers and card backgrounds.
- **Level 2 (Active/Hover):** Surface color with a subtle 1px border.
- **Borders:** Subtle `1px` borders in Neutral 700/800 are used to define table rows and column separators instead of shadows. This creates a "blueprint" feel that emphasizes structure and alignment.

## Shapes

The shape language is **Rounded (0.5rem)**. This update moves away from the tighter 0.25rem radius toward a more modern, approachable SaaS aesthetic. This increased radius helps soften the high-density data views, making the interface feel more intentional and less clinical.

- **Interactive Elements:** Buttons and Inputs use an 8px (0.5rem) radius.
- **Status Tags:** Use a 4px radius (0.25rem) to distinguish them from larger interactive buttons and containers.
- **Containers:** Large ledger containers and dashboard cards use 8px to maintain a cohesive, rounded structural identity.

## Components

**Buttons & Actions**
- **Primary:** High-contrast background (Sage Green #67a590) with JetBrains Mono bold text.
- **Secondary:** Blue (#296fd0) for standard navigational importance.
- **Ghost:** Used for secondary actions (Export, Filter) with a 1px Neutral border.
- **Enforced Action:** A "Hold to Confirm" button style for irreversible ledger commits.

**The Ledger Table**
- The core component. Must support "Zebra Striping" using alternating neutral surface tones.
- Hover states must highlight the entire row in a translucent tint to help the eye track across wide datasets.

**Status Chips**
- Small, rectangular chips with a background opacity of 15% of the status color and a solid 1px left-border of the status color. This creates a visual "flag" effect in the ledger.

**Inputs**
- Inset styling. Background should be darker than the surface to suggest a "field to be filled." Focus states use a 1px Sage Green #67a590 glow.

**Additional Components**
- **Audit Log Sidebar:** A vertical timeline using monospaced text to show an immutable trail of changes to the current record.
- **Diff-Viewer:** A side-by-side comparison component for reconciling two conflicting transaction records, using red/green text highlighting.