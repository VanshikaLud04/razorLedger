---
name: RazorLedger Obsidian
colors:
  surface: '#111416'
  surface-dim: '#111416'
  surface-bright: '#373a3c'
  surface-container-lowest: '#0b0f11'
  surface-container-low: '#191c1e'
  surface-container: '#1d2022'
  surface-container-high: '#272a2d'
  surface-container-highest: '#323537'
  on-surface: '#e1e2e5'
  on-surface-variant: '#b9cbc2'
  inverse-surface: '#e1e2e5'
  inverse-on-surface: '#2e3133'
  outline: '#83958d'
  outline-variant: '#3a4a44'
  surface-tint: '#00e0b3'
  primary: '#fdfffc'
  on-primary: '#00382b'
  primary-container: '#00ffcc'
  on-primary-container: '#00725a'
  inverse-primary: '#006b54'
  secondary: '#c0c1ff'
  on-secondary: '#1000a9'
  secondary-container: '#3131c0'
  on-secondary-container: '#b0b2ff'
  tertiary: '#fffeff'
  on-tertiary: '#303129'
  tertiary-container: '#e3e2d7'
  on-tertiary-container: '#64645b'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#24ffcd'
  primary-fixed-dim: '#00e0b3'
  on-primary-fixed: '#002118'
  on-primary-fixed-variant: '#00513f'
  secondary-fixed: '#e1e0ff'
  secondary-fixed-dim: '#c0c1ff'
  on-secondary-fixed: '#07006c'
  on-secondary-fixed-variant: '#2f2ebe'
  tertiary-fixed: '#e4e3d7'
  tertiary-fixed-dim: '#c7c7bc'
  on-tertiary-fixed: '#1b1c15'
  on-tertiary-fixed-variant: '#46473f'
  background: '#111416'
  on-background: '#e1e2e5'
  surface-variant: '#323537'
typography:
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '700'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.3'
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.4'
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: 0.08em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 16px
  margin-mobile: 16px
  margin-desktop: 32px
  density-compact: 4px
  density-comfortable: 12px
---

## Brand & Style
The design system is engineered for forensic precision and high-density technical workflows. It targets analysts and developers who require a cinematic yet utilitarian environment for managing complex infrastructure and cryptographic ledgers.

The aesthetic follows a **Modern-Technical** movement, blending elements of high-end developer tools with cinematic data visualization. It prioritizes low-light environments to reduce eye strain during long-duration monitoring. The personality is authoritative, "obsidian-hard," and unapologetically technical. Key characteristics include:
- **Forensic Density:** Maximum information per square inch without visual clutter.
- **Cinematic Hardware:** UI surfaces that feel like machined graphite or cold glass.
- **Technical Precision:** Use of hairline borders (0.5pt to 1pt) and microscopic details to denote high-integrity data.

## Colors
The palette is rooted in a "Triple-Black" obsidian foundation, providing a deep, non-reflective base for high-contrast status signaling.

- **Obsidian Foundation:** The background utilizes `#080B0D` as the base canvas. Tonal separation is achieved through `#0D1114` (primary containers) and `#12181B` (elevated components/hover states).
- **Electric Mint (#00FFCC):** Reserved exclusively for "Verified," "Online," or "Secured" states. It represents the health of the infrastructure.
- **Intelligence Violet (#6366F1):** Used for non-deterministic data, LLM activity, semantic relationships, and cognitive assistance.
- **Warm Ivory (#FDFCF0):** Applied to primary body text and headers to ensure high legibility against the dark background while reducing the "vibrancy" of pure white text.
- **Critical Safety:** Amber is used for "Uncertain/Pending" states. Red is strictly reserved for "Control Failures" or "Critical Security Breaches."

## Typography
Typography is split between a high-precision contemporary grotesque for reading and a technical monospaced font for data identification.

- **Primary Interface:** **Hanken Grotesk** provides a sharp, neutral, and highly legible face for all functional labels and narrative text. 
- **Technical Data:** **JetBrains Mono** is used for all hashes, transaction IDs, timestamps, and metadata. This font transition alerts the user that they are viewing "hard data" rather than "interface guidance."
- **Scale:** Keep font sizes tight. Most utility text should exist at 12px-14px to maintain forensic density. 
- **Hierarchy:** Use uppercase tracking (0.08em) for small labels to create a "blueprint" or "schematic" feel.

## Layout & Spacing
The layout follows a **Rigid Technical Grid**. Spacing is based on a 4px baseline, ensuring all elements align to a sub-pixel precise rhythm.

- **Grid Model:** A 12-column fluid grid for desktop with 16px gutters. For mobile, a 4-column grid with 16px margins.
- **Density:** This design system favors "Compact" spacing. Vertical padding in lists and tables should be minimized to allow for maximum data visibility.
- **Alignment:** Use hairline vertical separators instead of wide whitespace gaps to guide the eye through columns of data.
- **Reflow:** On mobile, complex data tables must switch to a "Card-Monospace" stack, where the ID is prioritized as the header.

## Elevation & Depth
In this design system, depth is communicated through **Tonal Layering and Precision Outlines** rather than traditional shadows.

- **Stacking:** Surface levels are defined by hex values. The further "forward" an element is, the lighter the grey (from `#080B0D` to `#12181B`).
- **Inner Borders:** Use 1px internal borders (stroke-align: inside) with low opacity (10-15%) white or primary accent to define edges. This mimics the look of high-end hardware panels.
- **No Shadows:** Avoid drop shadows. If an element must float, use a subtle 1px "Electric Mint" glow (spread 2px, opacity 20%) to indicate it is active or modal.
- **Glassmorphism:** Use only for temporary overlays (modals). Apply a 20px background blur with a `#080B0D` fill at 70% opacity.

## Shapes
The shape language is "Hard-Technical." 

- **Radius:** A standard 4px (`0.25rem`) radius is applied to buttons and inputs. This provides just enough softness to be professional without feeling consumer-grade.
- **Large Components:** Larger panels or modals should never exceed 8px (`0.5rem`) radius.
- **Interactive States:** Use sharp corners for data cells and table headers to maintain a "spreadsheet" level of seriousness.

## Components
- **Buttons:** Primary buttons use a solid "Electric Mint" background with black text. Secondary buttons use a 1px "Warm Ivory" border with no fill.
- **Chips/Status:** Use the "JetBrains Mono" font for chips. Mint background for "Active," Violet for "Processing," and Amber for "Awaiting Verification."
- **Lists & Tables:** The core of the system. Use hairline borders (`#12181B`) between rows. Alternate row colors are discouraged; use hover highlights in `#0D1114` instead.
- **Input Fields:** Use a `#080B0D` fill with a `#12181B` border. Upon focus, the border transitions to "Electric Mint" or "Intelligence Violet" depending on whether the input is a standard field or an LLM prompt.
- **Safety Overlays:** When a "Control Failure" occurs (Red), the entire border of the viewport or the specific module should pulse with a 2px red stroke.
- **Data Visualizer:** Graphs and charts should use 1px lines. Avoid area fills unless they have a 10% opacity gradient.