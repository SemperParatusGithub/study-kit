---
name: figures
description: Figures as code for study-kit courses - which studykit.figures template to use for circuits, Bode/Nyquist/step plots, phasors, signals, block diagrams, state machines and function plots, how to write figures/<slug>.py, and the mandatory render, look at the PNG, fix loop with its overlap, clipping and anchor checklist. Use whenever a course item needs a figure or a figure build fails.
user-invocable: false
---

# Figures

A figure is a Python script `<course>/figures/<slug>.py` that defines `build()` and
returns the `Figure` of one `studykit.figures` template. Never hand-write SVG, never draw
with raw Matplotlib outside `plot.custom()`. The full API is in
[reference.md](reference.md); `tests/fixtures/figures/gallery/figures/` has one working
script per template and `examples/sample-course/figures/` shows real course figures.

## Writing a figure

1. Pick the template (table below). Prefer a template over `plot.custom()`: templates
   place labels, check margins and record facts.
2. Write `figures/<slug>.py` (slug = kebab-case, usually `<item-prefix>-<what>`, e.g.
   `rc-tp-bode`, `pk1-rc-reihe`). Start from the content-format skill's
   `templates/figure.py`.
3. Pass `alt=` in the course language: what the figure shows and its key values (the
   caption in the Markdown is short; the alt text is complete). Component values are
   strings with units (`'4,7 kΩ'`, `'100 nF'`), SI numbers, or symbols (`'R'`, `'2R'`);
   never SPICE shorthand like `'4.7k'`.
4. Reference it from the Markdown as `![Caption](fig:<slug>)` alone in its paragraph.
5. Build and look (below). A figure that is not referenced anywhere is SK-FIG-UNUSED.

| Need | Template |
|---|---|
| voltage divider, loaded divider | `circuit.voltage_divider(R1, R2, U0, RL=…)` |
| RC / RL two-port (low- or high-pass) | `circuit.rc('lowpass', R, C)`, `circuit.rl('highpass', R, L)` |
| series or parallel RLC with source | `circuit.rlc('series', R, L, C, U0=…)` |
| op-amp circuits | `circuit.opamp('inverting', R1, R2)` (non_inverting, follower, integrator, differentiator) |
| Wheatstone bridge | `circuit.bridge('wheatstone', R1, R2, R3, R4, U0, R5=…)` |
| any other circuit | `with circuit.drawing(alt=…) as c:` + `c.resistor/capacitor/inductor/source_v/source_i/wire/dot/ground/terminal`, `circuit.zaehlpfeil_u/_i` |
| Bode diagram | `plot.bode(G, w=(lo, hi), unit='Hz', asymptotes=True, margins=False)` |
| Nyquist, pole-zero, root locus | `plot.nyquist(G)`, `plot.pole_zero(G)`, `plot.root_locus(G)` |
| step response | `plot.step_response(G, annotate=('final', 'overshoot', 'rise', 'settling'))` |
| phasor diagram | `plot.phasor({'U_R': (mag, deg), …}, chain=True, reference={'I': (mag, 0)})` |
| time signals, sequences | `plot.signals(t, {'u_1': array, …}, stem=False, y_unit='V')` |
| function plot with key points | `plot.functions([('f', 'x**2-2')], x=(-3, 3), mark=('roots', 'extrema'))` |
| control loop, chain, parallel blocks | `block.feedback_loop(…)`, `block.chain(…)`, `block.parallel(…)` |
| state machine, flowchart | `graph.state_machine(…)`, `graph.flowchart(…)` |
| anything else | `with plot.custom(alt=…) as c:` (house-styled axes, `c.facts`) |

`G` is a SymPy string in `s` (`'1/(1 + 1e-4*s)'`), a `(num, den)` pair or a
`control.TransferFunction`. Sizes: `'col'` (default), `'half'`, `'full'`, `'cs'` (cheat
sheet).

## Render → look at the PNG → fix

Every figure you write or change is built and looked at before you finish:

```bash
uv run --frozen studykit fig build <course> --only <slug>
```

Then Read `<course>/_build/figures/<slug>.png` (and `<slug>.facts.json` for the computed
values). A build error names the script and line; fix and rebuild. Go through the
checklist on the PNG, fix the script, rebuild, look again. At most three rounds; if a
template cannot do it, say so in your result instead of shipping a broken figure.

**Checklist:**

- **Overlap:** no label, value or arrow covers another label, a line, a component symbol
  or a tick label; legends sit clear of curves.
- **Clipping:** nothing is cut at the figure edge (labels, arrowheads, the top of a
  curve, asymptote ends, long tick labels); axis limits include every marked point.
- **Anchors:** every label sits next to the thing it names (the voltage arrow beside its
  component, the point label at its point, the phasor name at its phasor's head); leader
  lines point at the right element; reference arrows go from + to − (voltage) and along
  the current direction.
- **Correctness:** values, units and names match the item text exactly (same symbols,
  decimal comma in German); the facts (`facts.json`: divider ratio, τ, f_c, margins,
  roots) agree with the solution; the curve shape is right (slope, sign, asymptotes).
- **Readability:** text at its default size, nothing squeezed; axes labelled
  `U in V` style (the templates do this); colour is never the only key.
- **Alt text:** describes the figure fully enough to answer the item without seeing it.

## Rules the validator enforces

The runner rejects scripts that fail, SVGs with scripts, `<text>` or external links,
non-palette colours, text in colours other than fg, muted or c1, files over 400 KB and
missing glyphs (SK-FIG-BUILD). Use `color('fg')`, `color('muted')`, `color(0)` (c1) …
`color(5)` from `studykit.figures` for any colour in `plot.custom()`.
