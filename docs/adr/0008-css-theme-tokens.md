# ADR 0008: Shared CSS theme tokens and a System-first toggle

- Status: accepted
- Date: 2026-10-04
- PRD: [docs/prds/dark-mode.md](../prds/dark-mode.md)

## Context

Enact has three HTML surfaces that already share a light token set (zinc neutrals, teal accent, pass/fail/wait pills). Adding dark mode could mean three independent palettes, a runtime CSS framework, or a hosted theme API. The report must remain a single file that works from `file://`. Product code cannot grow outbound calls (ADR 0007). We also need Light / Dark / System, a live OS follow, no first-paint flash, and WCAG 2.2 AA in both themes.

## Decision

1. **One Python module** (`enact.theme`) owns the light and dark CSS custom-property maps, the contrast pairs, the pre-paint bootstrap script, the Appearance toggle markup, and the interactive script.
2. Surfaces **apply** those bytes; they do not invent palettes. The report inlines them. The Pages landing commits generated `site/theme.css` and `site/theme.js` (kept in lockstep by tests). `enact ui` serves the same stylesheet and script from the module.
3. Theming is `[data-theme="light"|"dark"]` plus `color-scheme`. The stored preference is `light` | `dark` | `system` in `localStorage` key `enact-theme`. **System is the default** and follows `prefers-color-scheme` live. A tiny inline bootstrap (hashed in each surface CSP) sets `data-theme` before paint.
4. No remote fonts, icon packs, or CDNs. Status stays labelled text, not colour alone.

## Consequences

- Token drift is a test failure instead of a visual surprise.
- The report CSP allows only inline style/script and `connect-src 'none'`, so `file://` stays offline.
- We rejected a CSS-framework theme switcher (new dependency, harder to inline) and a `class="dark"`-only approach (weaker `color-scheme` story, easier to miss a surface).
- Light `--line` is darkened relative to the original `#e4e4e7` so borders meet 3:1. Layout is unchanged.
