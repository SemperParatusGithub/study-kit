"""Block diagrams (signal flow) built on `schemdraw.dsp`, drawn onto a house-styled axes.

    block.feedback_loop(forward=['G_R(s)', 'G_S(s)'], feedback='H(s)', sign='-')
    block.chain(['G_1(s)', 'G_2(s)'], signals=['U(s)', None, 'Y(s)'])
    block.parallel(['G_1(s)', 'G_2(s)'], signals=['U(s)', 'Y(s)'], signs='+-')

Labels are TeX math without dollars (`'G_R(s)'`); text that already contains `$` is used
as is. The overall transfer function is computed with SymPy from the drawn structure
and recorded in the facts, so a figure and its caption cannot disagree.

This module also holds the small diagram toolkit that `graph.py` builds on: text
measurement in drawing units and `Sheet`, which renders a schemdraw `Drawing` at a fixed
scale (one drawing unit = `UNIT_PT` points, labels at house font size) and shrinks it to
the requested width only when it does not fit.
"""

from __future__ import annotations

import functools
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import schemdraw
import schemdraw.elements as elm
import sympy as sp
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure as MplFigure
from matplotlib.transforms import Bbox
from schemdraw import dsp
from schemdraw.segments import SegmentText

from studykit.figures import core
from studykit.figures.palette import FG

# ---------------------------------------------------------------------------------------
# Diagram toolkit (shared with graph.py)
# ---------------------------------------------------------------------------------------

UNIT_PT = 18.0  # one schemdraw drawing unit, in points, at natural scale
FONT_PT = 9.0  # text inside blocks, states and boxes (house font size)
LABEL_PT = 8.0  # signal names, transition labels, junction signs
LW_PT = 1.0  # line width of diagram strokes
MIN_SCALE = 0.72  # never shrink text below ~6.5 pt to fit a width
MARGIN = 0.12  # drawing units of white space around the drawing
LINESPACING = 1.15
FONT = "DejaVu Sans"


@functools.cache
def _measure_figure() -> MplFigure:
    fig = MplFigure(dpi=72)  # at 72 dpi one pixel is one point
    FigureCanvasAgg(fig)
    return fig


@functools.cache
def text_size(
    text: str, fontsize: float = FONT_PT, math: bool = True, weight: str = "normal"
) -> tuple[float, float]:
    """Width and height of rendered text, in drawing units (multi-line text allowed)."""
    fig = _measure_figure()
    t = fig.text(
        0,
        0,
        text,
        fontsize=fontsize,
        fontfamily=FONT,
        fontweight=weight,
        parse_math=math,
        linespacing=LINESPACING,
        multialignment="center",
    )
    bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
    t.remove()
    return bb.width / UNIT_PT, bb.height / UNIT_PT


def tex(label: str) -> str:
    """A TeX label as Matplotlib mathtext: wrap in dollars unless it already has some."""
    label = label.strip()
    if not label or "$" in label:
        return label
    return f"${core.localize_tex(label)}$"


def plain(label: str) -> str:
    """Label text for alt text: TeX without dollars."""
    return label.replace("$", "").strip()


@dataclass
class _Text:
    xy: tuple[float, float]
    text: str
    size: float
    ha: str
    va: str
    color: str
    math: bool
    weight: str
    bg: str | None


class Sheet:
    """A schemdraw drawing plus house-drawn texts, rendered at a fixed scale.

    Coordinates are schemdraw drawing units (1 unit = `UNIT_PT` points, y up).
    """

    def __init__(self) -> None:
        self.drawing = schemdraw.Drawing(show=False)
        self.drawing.config(color=FG, lw=LW_PT, fontsize=FONT_PT, font=FONT)
        self.texts: list[_Text] = []

    def add(self, element):
        return self.drawing.add(element)

    def text(
        self,
        xy: tuple[float, float],
        text: str,
        *,
        size: float = LABEL_PT,
        ha: str = "center",
        va: str = "center",
        color: str = FG,
        math: bool = True,
        weight: str = "normal",
        bg: str | None = None,
    ) -> None:
        """Place text; `bg` (a palette colour) puts a box behind it that hides lines."""
        self.texts.append(
            _Text((float(xy[0]), float(xy[1])), text, size, ha, va, color, math, weight, bg)
        )

    def _view(self, fig, ax, box: Bbox, scale: float) -> None:
        inch = UNIT_PT * scale / 72
        fig.set_size_inches(max(box.width, 0.1) * inch, max(box.height, 0.1) * inch)
        ax.set_position((0, 0, 1, 1))
        ax.set_xlim(box.x0, box.x1)
        ax.set_ylim(box.y0, box.y1)

    def _extent(self, fig, ax) -> Bbox:
        fig.draw_without_rendering()  # positions the background boxes of texts
        renderer = fig.canvas.get_renderer()
        to_data = ax.transData.inverted()
        boxes = []
        for artist in [*ax.lines, *ax.patches, *ax.texts, *ax.collections]:
            if not artist.get_visible():
                continue
            ext = artist.get_window_extent(renderer)
            if hasattr(artist, "get_bbox_patch") and artist.get_bbox_patch() is not None:
                ext = Bbox.union([ext, artist.get_bbox_patch().get_window_extent(renderer)])
            if ext.width > 0 or ext.height > 0:
                boxes.append(ext.transformed(to_data))
        return Bbox.union(boxes)

    def render(self, size: str, alt: str, facts: dict, min_scale: float = MIN_SCALE) -> core.Figure:
        """Draw onto a house axes; shrink (never grow) to the width of `size`."""
        target_w = core.size(size)[0]
        fig, ax = core.new_figure(size)
        fig.set_layout_engine("none")
        ax.set_axis_off()

        bb = self.drawing.get_bbox()
        xs = [bb.xmin, bb.xmax, *(t.xy[0] for t in self.texts)]
        ys = [bb.ymin, bb.ymax, *(t.xy[1] for t in self.texts)]
        rough = Bbox.from_extents(min(xs) - 1, min(ys) - 1, max(xs) + 1, max(ys) + 1)
        self._view(fig, ax, rough, 1.0)
        self.drawing.draw(canvas=ax, show=False)
        for t in self.texts:
            bbox = {"boxstyle": "square,pad=0.15", "facecolor": t.bg, "edgecolor": "none"}
            ax.text(
                *t.xy,
                t.text,
                fontsize=t.size,
                fontfamily=FONT,
                fontweight=t.weight,
                color=t.color,
                ha=t.ha,
                va=t.va,
                parse_math=t.math,
                linespacing=LINESPACING,
                multialignment="center",
                bbox=bbox if t.bg else None,
                zorder=6,
            )

        ext = self._extent(fig, ax)
        ext = Bbox.from_extents(ext.x0 - MARGIN, ext.y0 - MARGIN, ext.x1 + MARGIN, ext.y1 + MARGIN)
        natural_w = ext.width * UNIT_PT / 72
        scale = max(min(1.0, target_w / natural_w), min_scale)
        self._view(fig, ax, ext, scale)
        for t in ax.texts:
            t.set_fontsize(t.get_fontsize() * scale)
        for artist in [*ax.lines, *ax.patches]:
            artist.set_linewidth(artist.get_linewidth() * scale)
        for artist in [*ax.lines, *ax.patches, *ax.texts, *ax.collections]:
            artist.set_clip_on(False)
        facts = {
            **facts,
            "scale": round(scale, 3),
            "width_in": round(ext.width * UNIT_PT * scale / 72, 3),
        }
        return core.finish(fig, alt, facts)


# ---------------------------------------------------------------------------------------
# Block diagram building blocks
# ---------------------------------------------------------------------------------------

PAD_X = 0.45  # text to block edge
PAD_Y = 0.35
BLOCK_MIN_W = 1.9
BLOCK_MIN_H = 1.35
R_SUM = 0.3  # summing junction radius
GAP_MIN = 1.3  # shortest connecting arrow
LABEL_LIFT = 0.1  # signal name above its line
SIGN_OFS = 0.2  # sign distance outside the junction
SIGN_LIFT = 0.25  # sign above a horizontal input line
SIGN_SIDE = 0.32  # sign beside a vertical input line
SIGMA_PT = 6.5
JUNCTIONS = ("circle", "plus", "sigma")
SIGNS = ("+", "-")


def _display(label: str) -> str:
    """Block text as mathtext; fractions at full size (\\frac -> \\dfrac)."""
    return re.sub(r"\\frac(?![a-z])", r"\\dfrac", tex(label))


def _block_size(label: str) -> tuple[float, float]:
    w, h = text_size(_display(label), FONT_PT)
    return max(w + 2 * PAD_X, BLOCK_MIN_W), max(h + 2 * PAD_Y, BLOCK_MIN_H)


SIGN_ROOM = 0.45  # extra length of a link that touches a junction, for the input sign


def _link_len(label: str | None, junction_end: bool = False) -> float:
    extra = SIGN_ROOM if junction_end else 0.0
    if not label:
        return GAP_MIN + extra
    return max(GAP_MIN, text_size(tex(label), LABEL_PT)[0] + 0.6) + extra


def _block(sheet: Sheet, center: tuple[float, float], w: float, h: float, label: str):
    return sheet.add(
        dsp.Box(w=w, h=h).at(center).anchor("center").label(_display(label), fontsize=FONT_PT)
    )


def _junction(sheet: Sheet, center: tuple[float, float], style: str):
    if style not in JUNCTIONS:
        raise ValueError(f"unknown junction {style!r}; use one of {', '.join(JUNCTIONS)}")
    element = {"circle": dsp.Circle, "plus": dsp.Sum, "sigma": dsp.SumSigma}[style]()
    for segment in element.segments:
        if isinstance(segment, SegmentText):  # the Sigma; schemdraw would draw it at 14 pt
            segment.fontsize = SIGMA_PT
    return sheet.add(element.at(center).anchor("center").scale(R_SUM / 0.5))


def _sign(sheet: Sheet, center: tuple[float, float], side: str, sign: str) -> None:
    """Sign of a junction input, on the left-hand side of the arriving signal."""
    cx, cy = center
    d = R_SUM + SIGN_OFS
    pos = {
        "W": (cx - d, cy + SIGN_LIFT),
        "S": (cx - SIGN_SIDE, cy - d),
        "N": (cx + SIGN_SIDE, cy + d),
        "E": (cx + d, cy - SIGN_LIFT),
    }[side]
    sheet.text(pos, "$+$" if sign == "+" else "$-$", size=LABEL_PT)


def _signal(
    sheet: Sheet,
    x0: float,
    x1: float,
    y: float,
    label: str | None,
    into_junction: bool = False,
    from_junction: bool = False,
) -> None:
    """Signal name centred above a horizontal line from x0 to x1, clear of junction signs."""
    if label:
        x1 -= SIGN_ROOM if into_junction else 0.0
        x0 += SIGN_ROOM if from_junction else 0.0
        sheet.text(((x0 + x1) / 2, y + LABEL_LIFT), tex(label), va="bottom")


def _check_sign(sign: str) -> str:
    sign = sign.replace("\u2212", "-")  # accept a typographic minus
    if sign not in SIGNS:
        raise ValueError(f"sign must be '+' or '-', not {sign!r}")
    return sign


def _symbols(prefix: str, labels: Sequence[str]) -> tuple[list[sp.Symbol], dict]:
    syms = [sp.Symbol(f"{prefix}{i + 1}") for i in range(len(labels))]
    names = {s: core.localize_tex(plain(lbl)) for s, lbl in zip(syms, labels, strict=True)}
    return syms, names


def _expr_facts(expr: sp.Expr, names: dict) -> dict:
    expr = sp.factor(sp.cancel(expr))
    return {"expr": str(expr), "latex": sp.latex(expr, symbol_names=names)}


# ---------------------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------------------

DEFAULT_SIGNALS = {"r": "W(s)", "e": "E(s)", "u": "U(s)", "y": "Y(s)"}


def _internal_signals(u, n: int) -> list[str | None]:
    """Names of the n-1 signals between forward blocks; `u` is one name or a list."""
    if n < 2:
        return []
    if u is None or isinstance(u, str):
        return [u] + [None] * (n - 2)
    names = list(u)
    if len(names) != n - 1:
        raise ValueError(f"signals['u'] needs {n - 1} names for {n} forward blocks")
    return names


def _loop_algebra(n: int, has_h: bool, sign: str, dist_at: str | None):
    """Solve the loop equations; returns (symbols, Y/R, E/R, Y/Z)."""
    g = [sp.Symbol(f"G{i + 1}") for i in range(n)]
    h = sp.Symbol("H") if has_h else sp.Integer(1)
    r, z, e, y = sp.symbols("R Z E Y")
    s = -1 if sign == "-" else 1
    plant_in = sp.prod(g[:-1]) * e + (z if dist_at == "input" else 0)
    out = g[-1] * plant_in + (z if dist_at == "output" else 0)
    sol = sp.solve([sp.Eq(e, r + s * h * y), sp.Eq(y, out)], [e, y], dict=True)[0]
    t_ref = sp.diff(sol[y], r)
    t_err = sp.diff(sol[e], r)
    t_dist = sp.diff(sol[y], z) if dist_at else None
    return g, h, t_ref, t_err, t_dist


def feedback_loop(
    forward: Sequence[str] = ("G_R(s)", "G_S(s)"),
    feedback: str | None = "H(s)",
    signals: Mapping[str, str | Sequence[str] | None] | None = None,
    disturbance: str | None = None,
    sign: str = "-",
    *,
    disturbance_at: str = "input",
    junction: str = "circle",
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """Standard control loop: reference, summing junction, forward blocks, feedback.

    signals: 'r' reference, 'e' error, 'u' signal(s) between forward blocks (one name or
    a list of n-1 names), 'y' output, 'm' fed-back signal (optional).
    feedback=None draws unity feedback. disturbance: name of a signal added at the input
    of the last forward block (disturbance_at='input') or at the output ('output').
    """
    forward = list(forward)
    if not forward:
        raise ValueError("feedback_loop needs at least one forward block")
    sign = _check_sign(sign)
    if disturbance_at not in ("input", "output"):
        raise ValueError("disturbance_at must be 'input' or 'output'")
    sig = {**DEFAULT_SIGNALS, **(signals or {})}
    n = len(forward)
    links = _internal_signals(sig.get("u"), n)
    dist_at = disturbance_at if disturbance else None

    sheet = Sheet()
    sizes = [_block_size(b) for b in forward]
    main_h = max(h for _, h in sizes)

    # Main path, left to right along y = 0.
    x = 0.0
    l_in = _link_len(sig.get("r"), junction_end=True)
    _signal(sheet, x, x + l_in, 0, sig.get("r"), into_junction=True)
    x += l_in
    s1 = (x + R_SUM, 0.0)
    _junction(sheet, s1, junction)
    sheet.add(dsp.Arrow().at((0, 0)).to((x, 0)))
    _sign(sheet, s1, "W", "+")
    _sign(sheet, s1, "S", sign)
    x = s1[0] + R_SUM

    junctions = [{"at": "reference", "inputs": {"W": "+", "S": sign}}]
    d_center = None
    pending = sig.get("e")  # label of the link that leaves the previous element
    for i, (label, (w, _h)) in enumerate(zip(forward, sizes, strict=True)):
        if dist_at == "input" and i == n - 1:
            length = _link_len(pending, junction_end=True)
            sheet.add(dsp.Arrow().at((x, 0)).to((x + length, 0)))
            _signal(sheet, x, x + length, 0, pending, into_junction=True)
            d_center = (x + length + R_SUM, 0.0)
            _junction(sheet, d_center, junction)
            x = d_center[0] + R_SUM
            pending = None
        length = _link_len(pending)
        sheet.add(dsp.Arrow().at((x, 0)).to((x + length, 0)))
        _signal(sheet, x, x + length, 0, pending)
        x += length
        _block(sheet, (x + w / 2, 0), w, main_h, label)
        x += w
        pending = links[i] if i < n - 1 else None
    if dist_at == "output":
        length = _link_len(None, junction_end=True)
        sheet.add(dsp.Arrow().at((x, 0)).to((x + length, 0)))
        d_center = (x + length + R_SUM, 0.0)
        _junction(sheet, d_center, junction)
        x = d_center[0] + R_SUM

    # Output with the branch point of the feedback path.
    x_branch = x + 0.6
    l_out = _link_len(sig.get("y"))
    sheet.add(dsp.Line().at((x, 0)).to((x_branch, 0)))
    sheet.add(dsp.Arrow().at((x_branch, 0)).to((x_branch + l_out, 0)))
    sheet.add(dsp.Dot(radius=0.09).at((x_branch, 0)))
    _signal(sheet, x_branch, x_branch + l_out, 0, sig.get("y"))

    if d_center is not None:
        top = max(main_h / 2, R_SUM) + 0.9
        sheet.add(dsp.Arrow().at((d_center[0], top)).to((d_center[0], R_SUM)))
        sheet.text((d_center[0], top + LABEL_LIFT), tex(disturbance), va="bottom")
        _sign(sheet, d_center, "W", "+")
        _sign(sheet, d_center, "N", "+")
        junctions.append({"at": f"disturbance-{dist_at}", "inputs": {"W": "+", "N": "+"}})

    # Feedback path below, right to left.
    m_label = sig.get("m")
    if feedback:
        fw, fh = _block_size(feedback)
        y_fb = -(main_h / 2 + 0.8 + fh / 2)
        cx = (s1[0] + x_branch) / 2
        _block(sheet, (cx, y_fb), fw, fh, feedback)
        sheet.add(elm.Wire("|-", arrow="->").at((x_branch, 0)).to((cx + fw / 2, y_fb)))
        sheet.add(elm.Wire("-|", arrow="->").at((cx - fw / 2, y_fb)).to((s1[0], -R_SUM)))
        x_m0, x_m1 = s1[0], cx - fw / 2
    else:
        y_fb = -(main_h / 2 + 0.8)
        sheet.add(elm.Wire("n", k=y_fb, arrow="->").at((x_branch, 0)).to((s1[0], -R_SUM)))
        x_m0, x_m1 = s1[0], (s1[0] + x_branch) / 2
    if m_label:
        sheet.text(((x_m0 + x_m1) / 2, y_fb - LABEL_LIFT), tex(m_label), va="top")

    g, h, t_ref, t_err, t_dist = _loop_algebra(n, bool(feedback), sign, dist_at)
    names = {s: core.localize_tex(plain(lbl)) for s, lbl in zip(g, forward, strict=True)}
    if feedback:
        names[h] = core.localize_tex(plain(feedback))
    loop_gain = sp.prod(g) * h
    facts = {
        "template": "block.feedback_loop",
        "forward": forward,
        "feedback": feedback,
        "sign": sign,
        "signals": {k: v for k, v in sig.items() if v},
        "disturbance": disturbance,
        "disturbance_at": dist_at,
        "junction": junction,
        "junctions": junctions,
        "symbols": {str(s): lbl for s, lbl in names.items()},
        "loop_gain": _expr_facts(loop_gain, names),
        "reference_tf": _expr_facts(t_ref, names),
        "error_tf": _expr_facts(t_err, names),
        "disturbance_tf": _expr_facts(t_dist, names) if t_dist is not None else None,
    }
    if alt is None:
        alt = _feedback_alt(forward, feedback, sign, sig, disturbance, dist_at, facts)
    return sheet.render(size, alt, facts)


def _feedback_alt(forward, feedback, sign, sig, disturbance, dist_at, facts) -> str:
    chain_txt = " → ".join(plain(b) for b in forward)
    tf = facts["reference_tf"]["expr"]
    for sym, lbl in facts["symbols"].items():
        tf = tf.replace(sym, lbl)
    r, y = plain(sig.get("r") or "r"), plain(sig.get("y") or "y")
    if core.locale() == "de":
        fb = f"über {plain(feedback)}" if feedback else "direkt (Einheitsrückführung)"
        kind = "negativ" if sign == "-" else "positiv"
        text = (
            f"Blockschaltbild eines Regelkreises: Führungsgröße {r}, Vorwärtszweig "
            f"{chain_txt}, Ausgang {y}; der Ausgang wird {fb} {kind} zurückgeführt."
        )
        if disturbance:
            ort = "am Eingang des letzten Blocks" if dist_at == "input" else "am Ausgang"
            text += f" Die Störgröße {plain(disturbance)} greift {ort} an."
        return text + f" Führungsübertragungsfunktion: {tf}."
    fb = f"through {plain(feedback)}" if feedback else "directly (unity feedback)"
    kind = "negative" if sign == "-" else "positive"
    text = (
        f"Block diagram of a control loop: reference {r}, forward path {chain_txt}, "
        f"output {y}; the output is fed back {fb} with {kind} sign."
    )
    if disturbance:
        where = "at the input of the last block" if dist_at == "input" else "at the output"
        text += f" Disturbance {plain(disturbance)} enters {where}."
    return text + f" Closed-loop transfer function: {tf}."


def chain(
    blocks: Sequence[str],
    signals: Sequence[str | None] | None = None,
    *,
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """Series connection; signals: len(blocks)+1 names (input, links, output), None to omit."""
    blocks = list(blocks)
    if not blocks:
        raise ValueError("chain needs at least one block")
    sig = list(signals) if signals is not None else [None] * (len(blocks) + 1)
    if len(sig) != len(blocks) + 1:
        raise ValueError(f"chain of {len(blocks)} blocks needs {len(blocks) + 1} signals")

    sheet = Sheet()
    sizes = [_block_size(b) for b in blocks]
    h_all = max(h for _, h in sizes)
    x = 0.0
    for label, (w, _), name in zip(blocks, sizes, sig, strict=False):
        length = _link_len(name)
        sheet.add(dsp.Arrow().at((x, 0)).to((x + length, 0)))
        _signal(sheet, x, x + length, 0, name)
        x += length
        _block(sheet, (x + w / 2, 0), w, h_all, label)
        x += w
    length = _link_len(sig[-1])
    sheet.add(dsp.Arrow().at((x, 0)).to((x + length, 0)))
    _signal(sheet, x, x + length, 0, sig[-1])

    syms, names = _symbols("G", blocks)
    facts = {
        "template": "block.chain",
        "blocks": blocks,
        "signals": sig,
        "symbols": {str(s): lbl for s, lbl in names.items()},
        "transfer": _expr_facts(sp.prod(syms), names),
    }
    if alt is None:
        path = " → ".join(plain(b) for b in blocks)
        tf = " · ".join(plain(b) for b in blocks)
        if core.locale() == "de":
            alt = f"Reihenschaltung der Blöcke {path}; Gesamtübertragungsfunktion {tf}."
        else:
            alt = f"Series connection of blocks {path}; overall transfer function {tf}."
    return sheet.render(size, alt, facts)


def parallel(
    blocks: Sequence[str],
    signals: Sequence[str | None] | None = None,
    *,
    signs: str | Sequence[str] | None = None,
    junction: str = "circle",
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """Parallel connection of 2 or 3 blocks whose outputs are summed.

    signals: [input, output] names (None to omit); signs: one '+'/'-' per block.
    """
    blocks = list(blocks)
    n = len(blocks)
    if n not in (2, 3):
        raise ValueError("parallel draws 2 or 3 blocks")
    sig = list(signals) if signals is not None else [None, None]
    if len(sig) != 2:
        raise ValueError("parallel signals are [input, output]")
    sgn = [_check_sign(s) for s in (signs if signs is not None else "+" * n)]
    if len(sgn) != n:
        raise ValueError(f"parallel needs {n} signs")

    sheet = Sheet()
    sizes = [_block_size(b) for b in blocks]
    w_all = max(w for w, _ in sizes)
    h_all = max(h for _, h in sizes)
    pitch = h_all + 0.7
    ys = [pitch * ((n - 1) / 2 - i) for i in range(n)]

    l_in = _link_len(sig[0])
    _signal(sheet, 0, l_in, 0, sig[0])
    x_branch = l_in
    x_block = x_branch + 0.9
    sheet.add(dsp.Line().at((0, 0)).to((x_branch, 0)))
    centre = (x_block + w_all + 0.9 + R_SUM, 0.0)
    _junction(sheet, centre, junction)
    sides = ["N", "S"] if n == 2 else ["N", "W", "S"]
    for y, label, side, s in zip(ys, blocks, sides, sgn, strict=True):
        if y != 0:
            sheet.add(dsp.Line().at((x_branch, 0)).to((x_branch, y)))
        sheet.add(dsp.Arrow().at((x_branch, y)).to((x_block, y)))
        _block(sheet, (x_block + w_all / 2, y), w_all, h_all, label)
        start = (x_block + w_all, y)
        if side == "W":
            sheet.add(dsp.Arrow().at(start).to((centre[0] - R_SUM, 0)))
        else:
            end = (centre[0], R_SUM if side == "N" else -R_SUM)
            sheet.add(elm.Wire("-|", arrow="->").at(start).to(end))
        _sign(sheet, centre, side, s)
    sheet.add(dsp.Dot(radius=0.09).at((x_branch, 0)))
    x_out = centre[0] + R_SUM
    l_out = _link_len(sig[1], junction_end=True)
    sheet.add(dsp.Arrow().at((x_out, 0)).to((x_out + l_out, 0)))
    _signal(sheet, x_out, x_out + l_out, 0, sig[1], from_junction=True)

    syms, names = _symbols("G", blocks)
    total = sum((sym if s == "+" else -sym for sym, s in zip(syms, sgn, strict=True)), sp.S.Zero)
    facts = {
        "template": "block.parallel",
        "blocks": blocks,
        "signals": sig,
        "signs": sgn,
        "junction": junction,
        "symbols": {str(s): lbl for s, lbl in names.items()},
        "transfer": _expr_facts(total, names),
    }
    if alt is None:
        terms = " ".join(f"{s} {plain(b)}" for s, b in zip(sgn, blocks, strict=True)).lstrip("+ ")
        listed = ", ".join(plain(b) for b in blocks)
        if core.locale() == "de":
            alt = f"Parallelschaltung der Blöcke {listed}, Ausgänge summiert: {terms}."
        else:
            alt = f"Parallel connection of blocks {listed}, outputs summed: {terms}."
    return sheet.render(size, alt, facts)


__all__ = [
    "FONT_PT",
    "LABEL_PT",
    "UNIT_PT",
    "Sheet",
    "chain",
    "feedback_loop",
    "parallel",
    "plain",
    "tex",
    "text_size",
]
