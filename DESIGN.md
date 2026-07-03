# Public Hurdle Design System

## 1. Atmosphere & Identity

Public Hurdle is a quiet investment control room: dense, exact, and skeptical. The signature is a dark valuation console where market momentum, quality gates, and missing financials are visible at once without marketing composition or decorative noise.

## 2. Color

### Palette

| Role | Token | Light | Dark | Usage |
|---|---|---|---|---|
| Surface/primary | `--surface-primary` | `#f7f8f8` | `#08090a` | Page background |
| Surface/secondary | `--surface-secondary` | `#ffffff` | `#0f1011` | Tool panels |
| Surface/elevated | `--surface-elevated` | `#f3f4f5` | `#17181a` | Metric cards, table rows |
| Surface/warm | `--surface-warm` | `#f4f0e8` | `#1b1813` | Financial coverage emphasis |
| Text/primary | `--text-primary` | `#101113` | `#f7f8f8` | Primary text |
| Text/secondary | `--text-secondary` | `#4d5662` | `#c7ccd4` | Body text |
| Text/tertiary | `--text-tertiary` | `#747b86` | `#858b95` | Metadata |
| Border/subtle | `--border-subtle` | `#e7e9ed` | `rgba(255,255,255,0.06)` | Fine separators |
| Border/default | `--border-default` | `#d4d8df` | `rgba(255,255,255,0.1)` | Controls, panels |
| Accent/primary | `--accent-primary` | `#4f46e5` | `#7170ff` | Primary action, focus |
| Accent/hover | `--accent-hover` | `#4338ca` | `#8584ff` | Hover state |
| Status/success | `--status-success` | `#168a4a` | `#2fbf71` | Quality pass, complete |
| Status/warning | `--status-warning` | `#aa6a00` | `#f2b84b` | Missing financials, caution |
| Status/error | `--status-error` | `#b4232d` | `#e05252` | Failed gates, errors |
| Status/info | `--status-info` | `#2563eb` | `#7aa7ff` | Neutral market context |

### Rules

- Accent is reserved for commands, selected states, and focus rings.
- Status colors carry semantic meaning only; they are never decorative.
- The default theme is dark because repeated valuation review benefits from lower luminance.

## 3. Typography

### Scale

| Level | Size | Weight | Line Height | Tracking | Usage |
|---|---:|---:|---:|---:|---|
| Display | 36px | 590 | 1.12 | 0 | Product title |
| H1 | 28px | 590 | 1.2 | 0 | Page sections |
| H2 | 22px | 590 | 1.25 | 0 | Panel headings |
| H3 | 18px | 590 | 1.35 | 0 | Metric labels |
| Body | 15px | 400 | 1.55 | 0 | Default text |
| Body/sm | 13px | 400 | 1.45 | 0 | Table cells, metadata |
| Caption | 12px | 510 | 1.35 | 0 | Labels |
| Mono | 12px | 500 | 1.4 | 0 | Numeric badges |

### Font Stack

- Primary: `Inter, SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif`
- Mono: `Berkeley Mono, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`

### Rules

- Letter spacing is zero for Korean readability.
- Body text never drops below 13px in dense tables.
- Numeric values use tabular figures through `font-variant-numeric`.

## 4. Spacing & Layout

### Base Unit

All spacing derives from 4px.

| Token | Value | Usage |
|---|---:|---|
| `--space-1` | 4px | Tight inline gaps |
| `--space-2` | 8px | Control inner gaps |
| `--space-3` | 12px | Compact padding |
| `--space-4` | 16px | Default padding |
| `--space-5` | 20px | Panel spacing |
| `--space-6` | 24px | Page gutters |
| `--space-8` | 32px | Major groups |

### Grid

- Max content width: 1440px
- Breakpoints: 720px, 1024px, 1280px
- Primary layout: full-width dashboard with summary strip, control bar, table, and detail panel.

### Rules

- Controls have stable dimensions; hover and loading states cannot resize layout.
- Table and detail panels may scroll independently on desktop.
- Mobile collapses to one column with the detail panel below the table.

## 5. Components

### Top Bar
- **Structure**: header with product mark, status text, and command group.
- **States**: default, loading, error.
- **Accessibility**: commands are real buttons with visible focus rings.

### Metric Card
- **Structure**: label, numeric value, small supporting line.
- **Variants**: neutral, success, warning, error.
- **Spacing**: `--space-4`.
- **States**: default only.

### Control Bar
- **Structure**: search input, select, segmented quality filter, command buttons.
- **States**: default, hover, focus, disabled, loading.
- **Accessibility**: labels are visible or programmatically associated.

### Universe Table
- **Structure**: sticky header, sortable rows, status pills, numeric columns.
- **States**: default, hover, selected, empty.
- **Accessibility**: row buttons expose ticker names and keyboard focus.

### Detail Panel
- **Structure**: selected ticker header, valuation metrics, quality failures, momentum facts.
- **States**: selected, empty, error.
- **Accessibility**: panel updates are announced through status text.

## 6. Motion & Interaction

### Timing

| Type | Duration | Easing | Usage |
|---|---:|---|---|
| Micro | 120ms | ease-out | Button, row hover |
| Standard | 200ms | ease-in-out | Detail panel updates |

### Rules

- Animate only opacity, transform, and background color.
- Respect `prefers-reduced-motion`.
- Motion must mark interaction state; no decorative loops.

## 7. Depth & Surface

### Strategy

Mixed: dark tonal shifts plus hairline borders. Shadows are limited to focused overlays and never used as the primary separator.

| Level | Value | Usage |
|---|---|---|
| Panel border | `1px solid var(--border-default)` | Tool frames |
| Soft border | `1px solid var(--border-subtle)` | Row and metric separators |
| Focus ring | `0 0 0 3px rgba(113,112,255,0.22)` | Keyboard focus |
