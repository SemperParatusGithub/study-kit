# studykit.figures API reference

Import from `studykit.figures` (`from studykit.figures import plot, circuit, block, graph`).
Every builder returns `Figure(svg, png, alt, facts)` and takes `size=` (`'col'` 3.6×2.4 in,
`'half'` 2.9×2.1, `'full'` 6.2×3.0, `'cs'` 2.4×1.6) and `alt=`. The locale (decimal comma,
`U in V` axis labels) comes from the course. Source: `src/studykit/figures/`.

## plot (function plots, control and signals)

`plot.functions(fns, x=(-3, 3), y=None, mark=(), exact=True, coords=True, x_label='x', y_label='y', legend=True, size='col', alt=None)`
: `fns` are SymPy strings in `x` or `(name, expr)` pairs. `mark` from `'roots'`,
`'intersections'`, `'extrema'`, `'inflections'`: computed numerically (sign scan, brentq,
residual check against poles), exact forms only for display. Points at one place share a
label.

`plot.bode(G, w=None, unit='rad/s', asymptotes=False, margins=False, size='col', alt=None)`
: magnitude in dB over phase in degrees. `w=(lo, hi)` in `unit` (`'rad/s'` or `'Hz'`).
`margins=True` marks gain and phase margin, re-checked with `scipy.signal`.

`plot.nyquist(G, mark_critical=True, w=None, lim=None, name='G', size='col', alt=None)`
: ω > 0 solid with arrows, mirror branch dashed, −1 marked.

`plot.pole_zero(G, discrete=False, stability=True, size='col', alt=None)`
: poles ×, zeros ○, multiplicities in brackets; unit circle for `discrete=True` (G in `z`).

`plot.step_response(G, t=None, annotate=('final', 'overshoot', 'rise', 'settling'), settling_band=0.02, unit='s', size='col', alt=None)`
: h(t) with computed annotations.

`plot.root_locus(G, gains=None, size='col', alt=None)`
: 1 + K·G = 0 for K ≥ 0.

`plot.phasor(vectors, chain=False, total=None, show_angle=True, size='col', alt=None, reference=None, angle_name='\\varphi')`
: `vectors = {'U_R': (magnitude, angle_deg), …}` in TeX names; `chain=True` draws them
head to tail with the sum from the origin (`total='U'` names it); `reference={'I': (2, 0)}`
draws the reference phasor at its own scale beside its axis.

`plot.signals(t, series, stem=False, unit='s', y_label=None, y_unit=None, legend=None, size='col', alt=None)`
: `series = {'u_1': array or callable of t}`; `stem=True` for sequences x[n].

`plot.custom(alt, size='col', **subplot_kw)` (context manager)
: `c.ax` (house-styled axes), `c.facts` (dict for numbers), `c.figure` after the block.
Use `axis_label('u_C', 'V')` for labels and `color(…)` for colours.

`G` (transfer function): SymPy string in `s` (or `z`), `(num, den)` coefficient lists, or
`control.TransferFunction`; dead time is rejected.

## circuit (IEC / DIN EN 60617)

Values: strings with unit (`'4,7 kΩ'`, `'100 nF'`, `'12 V'`), SI numbers, or symbols
(`'R'`, `'2R'`, `'R_1'`); `None` draws the default symbol. facts list each component with
its nodes and SI value, every reference arrow, and derived values (ratio, τ, f_c, ω_0, Q,
gain).

`circuit.voltage_divider(R1=None, R2=None, U0=None, *, RL=None, size='col', alt=None)`
: `RL=True` draws a symbolic load.

`circuit.rc(kind='lowpass', R=None, C=None, *, phasors=False, …)`,
`circuit.rl(kind='lowpass', R=None, L=None, *, phasors=False, …)`
: `kind` is `'lowpass'` or `'highpass'`; two-port with input and output voltage arrows.

`circuit.rlc(topology='series', R=None, L=None, C=None, *, U0=None, I0=None, source=None, ac=True, phasors=False, …)`
: `topology` `'series'` or `'parallel'`.

`circuit.opamp(kind='inverting', R1=None, R2=None, *, R=None, C=None, symbol='din', …)`
: kinds `inverting`, `non_inverting`, `follower`, `integrator`, `differentiator`;
`symbol='triangle'` for the US form.

`circuit.bridge(kind='wheatstone', R1=None, R2=None, R3=None, R4=None, U0=None, *, R5=None, …)`
: nodes T (top), 0, A (R1-R2), B (R3-R4); `R5` between A and B.

`circuit.drawing(alt=None, size='col')` (context manager, schemdraw underneath)
: `c.resistor(symbol, value, nodes=('1', '2'), loc='auto')`, `c.capacitor(…)`,
`c.inductor(…)`, `c.source_v(symbol, value, nodes, ac=False)`, `c.source_i(…)`,
`c.wire(p1, p2)`, `c.dot(xy)`, `c.terminal(xy)`, `c.ground(xy)`, `c.text(xy, tex)`; each
element chains schemdraw placement (`.at((x, y)).down(3)`, `.right()`). Then
`circuit.zaehlpfeil_u(element, 'U_R', side=None, reverse=False)` and
`circuit.zaehlpfeil_i(element, 'I', end='start', reverse=False)`. `c.figure` after the
block. Ground is the IEC earth symbol, an AC source a circle with ~.

## block (schemdraw.dsp)

`block.feedback_loop(forward=('G_R(s)', 'G_S(s)'), feedback='H(s)', signals=None, disturbance=None, sign='-', *, disturbance_at='input', junction='circle', …)`
: facts carry the reference, error and disturbance transfer functions solved with SymPy.

`block.chain(blocks, signals=None, …)`: series blocks; `signals` has len(blocks)+1 names.

`block.parallel(blocks, signals=None, *, signs=None, junction='circle', …)`: 2 or 3
blocks summed.

## graph

`graph.state_machine(states, transitions, initial=None, accepting=(), kind='moore', layout='ring', …)`
: `transitions = [(src, dst, label), …]`; `kind='mealy'` labels edges `in/out`; `layout`
`'ring'`, `'row'`, `'grid'` or `{state: (x, y)}`.

`graph.flowchart(nodes, edges, …)`
: `nodes = [(id, kind, text)]` with kind `start`, `end`, `process`, `decision`, `io`;
`edges = [(src, dst) or (src, dst, label)]`; the first edge out of a node goes straight
down, further decision branches go right, loops run up the outer lane.

`graph.topic_map(course_dir, *, size='full', direction='auto')`
: built automatically for every course as `fig:topic-map`; never write a script for it.

## Helpers

`axis_label(quantity, unit)` → `U in V` (German) or `U / V`; `fmt_number(value, digits=3)`
in the figure locale; `color(role_or_index)` with roles `fg`, `muted`, `grid`, `bg`,
`c1`…`c6` or an index (0 = c1).

## Output

`studykit fig build <course> [--only <slug>] [--force]` writes into
`<course>/_build/figures/`: `<slug>.svg` (Typst), `<slug>.web.svg` (site, themed),
`<slug>.png` (100 dpi, for review), `<slug>.facts.json` (computed values). The build is
cached by script, studykit sources, lock file, style and locale.
