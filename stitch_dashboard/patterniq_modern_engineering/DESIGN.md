# Design System Document: Precision & Technical Elegance

## 1. Overview & Creative North Star: "The Blueprint Aesthetic"
This design system moves away from the generic "SaaS" look and toward a high-end editorial experience that mirrors the precision of modern engineering. Our Creative North Star is **"The Blueprint Aesthetic"**—a philosophy where structural clarity meets premium tactility.

We achieve this not through heavy lines or rigid grids, but through **intentional asymmetry and tonal depth**. The UI should feel like a high-end technical schematic: breathable, mathematically precise, and layered. We break the "template" look by using exaggerated typographic scales and overlapping "glass" surfaces that suggest a sophisticated, multi-dimensional workspace.

---

## 2. Colors: Tonal Architecture
The palette is rooted in a technical foundation: Forest Green (`primary`) represents growth and precision, while Charcoal (`secondary/on-surface`) provides the weight of heavy industry.

### The "No-Line" Rule
**Explicit Instruction:** 1px solid borders are prohibited for sectioning. 
Structural boundaries must be defined solely through background color shifts or subtle tonal transitions. For example, a `surface-container-low` section should sit directly on a `surface` background to create a "recessed" or "elevated" feel without the visual clutter of a stroke.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers—like stacked sheets of drafting paper or frosted glass. 
- **Base Level:** `surface` (#f7f9fb)
- **Recessed Areas:** `surface-container-low` (#f2f4f6)
- **Interactive Layers:** `surface-container-lowest` (#ffffff)
- **Information Density:** Use `surface-container-high` (#e6e8ea) for sidebars or utility panels to create a clear "utility" vs "canvas" distinction.

### The "Glass & Gradient" Rule
To elevate the "Modern Engineering" feel, use **Glassmorphism** for floating elements (modals, popovers). Use semi-transparent surface colors with a `20px` backdrop-blur. 
- **Signature Textures:** For primary CTAs or Hero sections, use a subtle linear gradient (135°) from `primary` (#006948) to `primary_container` (#00855d). This provides a "machine-polished" soul that flat hex codes cannot achieve.

---

## 3. Typography: The Technical Voice
We utilize a triad of typefaces to establish a sophisticated hierarchy that feels both human and engineered.

*   **Display & Headline (Manrope):** Large, airy, and geometric. Used for high-level concepts and section starts. The wide tracking in `display-lg` (3.5rem) signals a premium, editorial confidence.
*   **Title & Body (Inter):** A workhorse for clarity. Inter provides the "approachable" side of the "Modern Engineering" prompt. It ensures long-form technical data remains readable.
*   **Labels (Space Grotesk):** This is our "Technical" accent. Used for `label-md` and `label-sm` (0.75rem - 0.6875rem), this monospaced-leaning font should be used for data points, metadata, and captions to mimic engineering blueprints.

---

## 4. Elevation & Depth: Tonal Layering
Traditional dropshadows are often too "muddy" for a precise engineering look. We use **Tonal Layering**.

*   **The Layering Principle:** Depth is achieved by stacking. Place a `surface-container-lowest` card on a `surface-container-low` background. The contrast is the "shadow."
*   **Ambient Shadows:** When a float is required (e.g., a dropdown), use an extra-diffused shadow: `0 20px 40px rgba(30, 41, 59, 0.06)`. The tint is derived from our Charcoal (`on-surface`), making the shadow feel like natural ambient light.
*   **The "Ghost Border" Fallback:** If a border is required for accessibility, use the `outline_variant` (#bccac0) at **15% opacity**. Never use 100% opaque borders.
*   **Frosted Glass:** Use `surface_container_lowest` at 80% opacity with a `blur(12px)` for headers that stay fixed during scroll. This integrates the content rather than severing it.

---

## 5. Components: Minimalist Primitives

### Buttons & Chips
- **Primary Button:** Gradient fill (`primary` to `primary_container`), `8px` (DEFAULT) rounded corners. Text is `on_primary` (#ffffff).
- **Secondary Button:** `surface-container-high` fill. No border.
- **Chips:** Use `label-md` (Space Grotesk) for chip text. Filter chips should use `outline_variant` at 20% opacity for their container to maintain the "Ghost Border" aesthetic.

### Cards & Lists
- **Rule:** Forbid the use of divider lines. 
- **Execution:** Separate list items using the Spacing Scale (e.g., `1.5` or `0.375rem` gap). For cards, use a subtle background shift (`surface-container-low`) instead of a stroke.
- **Asymmetry:** In editorial layouts, offset card heights or use an 8-column grid within a 12-column container to create "white space lungs" in the design.

### Input Fields
- **State:** Active inputs should not use a heavy border. Use a 2px bottom-bar in `primary` (#006948) and a slight background fill shift to `surface_container_high`.
- **Micro-copy:** Use `label-sm` (Space Grotesk) for helper text to maintain the "technical manual" feel.

### Additional Components: The "Data Blueprint"
- **Data Callouts:** Large-scale numbers using `display-md` (Manrope) paired with a small `label-sm` (Space Grotesk) description. 
- **Status Indicators:** Small, glowing pips using `primary` (Forest Green) with a soft outer glow (`4px` spread) instead of flat icons.

---

## 6. Do’s and Don’ts

### Do:
- **Do** use `24` (6rem) or `20` (5rem) spacing for major section vertical padding to allow the design to breathe.
- **Do** use "Ghost Borders" for complex data tables where tonal shifts alone aren't enough for clarity.
- **Do** overlap elements (e.g., an image slightly breaking the boundary of its container) to create a custom, non-templated feel.

### Don’t:
- **Don’t** use pure black (#000000). Use Charcoal (`on_surface` #191c1e) for all high-contrast text.
- **Don’t** use the `full` (9999px) roundedness for anything other than status pips or small tags. The brand's "Precision" identity is tied to the `8px` (DEFAULT) corner.
- **Don’t** use standard 1px gray dividers. They represent "standard" UI; we use white space and tonal shifts to represent "Engineering Excellence."