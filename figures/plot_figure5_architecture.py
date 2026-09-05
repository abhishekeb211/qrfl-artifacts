"""Figure 5: layered QRFL architecture (seaborn theme + Plotly vector export).

Seaborn supplies the paper theme and derived pastel washes. Plotly draws the
five-layer diagram (rounded containers, cards, annotated flows). Kaleido writes
300 dpi PNG and vector PDF for the Elsevier manuscript.

Numerics match the manuscript: n=20, Td=1.86 y, L≈19.26M, bootstrap 95% LB
Z=2042.08, Mosca X=15 / Y=5, ML-KEM-768, ML-DSA-65, SLH-DSA-SHAKE-256s,
HLF v2.5 / etcdraft, four-phase 2026–2041 roadmap.

Usage
-----
    python plot_figure5_architecture.py
    python -m figures.plot_figure5_architecture
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import matplotlib.colors as mcolors
import plotly.graph_objects as go
import seaborn as sns

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_ARTIFACTS = _THIS_DIR.parent
_MANUSCRIPT_ROOT = _ARTIFACTS.parent
_DEFAULT_OUT = _THIS_DIR / "output"
_MANUSCRIPT_FIGS = _MANUSCRIPT_ROOT / "figs"
STEM = "system_architecture"

# ---------------------------------------------------------------------------
# Canvas — 13.5 × 8.5 in at 300 dpi (CSS px at 96 dpi, then Kaleido scale)
# ---------------------------------------------------------------------------
FIG_W = 13.5
FIG_H = 8.5
DPI = 300
CSS_DPI = 96.0
CSS_W = int(round(FIG_W * CSS_DPI))
CSS_H = int(round(FIG_H * CSS_DPI))
EXPORT_SCALE = DPI / CSS_DPI

# pt → CSS px (1 pt = 1/72 in)
def _pt(size: float) -> float:
    return size * CSS_DPI / 72.0


FS_TITLE = _pt(15.0)
FS_LAYER = _pt(13.5)
FS_HEAD = _pt(12.0)
FS_BODY = _pt(10.5)
FS_LABEL = _pt(9.5)
FS_BADGE = _pt(9.5)

LW = 1.2
R_LAYER = 0.11
R_CARD = 0.075
R_CHIP = 0.055

C_TEXT = "#1a1a1a"
C_MUTED = "#3d4450"
C_WHITE = "#ffffff"
C_DATA = "#1f3d5c"
C_POLICY = "#6b2d2d"
FONT = "Times New Roman, DejaVu Serif, STIXGeneral, serif"

# User-specified layer fills / borders
LAYER_SPEC = (
    {"id": 1, "short": "Forecast", "title": "Quantum Threat Timeline & Forecasting Engine",
     "fill": "#eef3f8", "edge": "#295b88"},
    {"id": 2, "short": "PQC", "title": "Post-Quantum Cryptographic & Crypto-Agility Engine",
     "fill": "#f4f1fa", "edge": "#5a3e85"},
    {"id": 3, "short": "FL", "title": "Privacy-Preserving Healthcare Federated Learning Layer",
     "fill": "#eef6f0", "edge": "#2d6a4f"},
    {"id": 4, "short": "Ledger", "title": "Permissioned Blockchain Governance & Ledger Layer",
     "fill": "#fdf7ee", "edge": "#b37400"},
    {"id": 5, "short": "Migration", "title": "Strategic Migration & Decision Support Layer",
     "fill": "#fdf2f2", "edge": "#9b2c2c"},
)

MODULES = {
    1: (
        ("Hardware Corpus (n=20)",
         "IBM, Google, Rigetti,<br>Quantinuum, Atom Computing<br>Status-classified, 2016–2026"),
        ("Forecasting Models",
         "Log-linear OLS (T<sub>d</sub>=1.86 y)<br>"
         "Logistic saturation (L≈19.26M)<br>"
         "ECDSA-256 crossing ≈ 2050.19"),
        ("Risk Trigger &amp; UQ",
         "Bootstrap 95% lower bound 2042.08<br>"
         "Feeds Mosca horizon <i>Z</i><br>"
         "Planning heuristic, not a compromise date"),
    ),
    2: (
        ("Hybrid PKI / CA",
         "Dual X.509 issuance<br>ECDSA-P256 + ML-DSA-65<br>Hybrid certificates in transition"),
        ("KEM Session Channel",
         "ML-KEM-768 + ephemeral ECDHE<br>HKDF-derived <i>K</i><sub>session</sub><br>NIST Level 3, hybrid then native"),
        ("Digital Signatures",
         "ML-DSA-65 (node / FL updates)<br>SLH-DSA-SHAKE-256s (archival)<br>Long-lived attestation anchors"),
        ("Crypto-Agility Engine",
         "Runtime algorithm swapping<br>Cipher-suite negotiation<br>Policy-driven suite updates"),
    ),
    3: (
        ("Clinical Edge Nodes",
         "Hospitals 1,…,<i>K</i>; local EHR<br>PneumoniaMNIST benchmark<br>Dirichlet α ∈ {0.1, 0.5, 1.0}"),
        ("Lattice-Compatible Masking",
         "Additive ring masking<br>"
         "<i>W</i><sub>u</sub><sup>*</sup> = <i>W</i><sub>u</sub> + <i>M</i><sub>u</sub>,  Σ <i>M</i><sub>u</sub> = 0<br>"
         "PQ-ready secure aggregation"),
        ("Flower Aggregator &amp; Defense",
         "FedAvg with robust filters<br>Coordinate-wise Median; Krum<br>Byzantine / poisoning resistance"),
    ),
    4: (
        ("Consortium Network",
         "3-peer Hyperledger Fabric v2.5<br>Permissioned hospital consortium<br>Channel qrflchannel"),
        ("Ordering Engine",
         "Raft crash-fault tolerance<br>etcdraft ordering service<br>Live test-network validated"),
        ("Smart Chaincode",
         "Contract flupdate<br>Validates ML-DSA-65 on <i>W</i><sub>u</sub><sup>*</sup><br>SubmitUpdate invoke path"),
        ("Ledger &amp; DCRL",
         "Immutable audit trail<br>Decentralized revocation list<br>Consent / provenance records"),
    ),
}

PHASES = (
    ("I", "2026–2029", "Inventory / hybrid TLS"),
    ("II", "2029–2032", "Archival PQC"),
    ("III", "2032–2036", "Native FL / ledger"),
    ("IV", "2036–2041", "Native-PQC policy"),
)


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self) -> float:
        return self.x + 0.5 * self.w

    @property
    def cy(self) -> float:
        return self.y + 0.5 * self.h

    @property
    def top(self) -> float:
        return self.y + self.h

    @property
    def right(self) -> float:
        return self.x + self.w


def _apply_seaborn_theme() -> dict[int, dict[str, str]]:
    """Paper theme + seaborn-derived header/card washes from the layer edges."""
    sns.set_theme(
        context="paper",
        style="white",
        font="DejaVu Serif",
        rc={
            "axes.edgecolor": C_TEXT,
            "text.color": C_TEXT,
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif", "STIXGeneral"],
        },
    )
    styled: dict[int, dict[str, str]] = {}
    for spec in LAYER_SPEC:
        edge = spec["edge"]
        wash = [mcolors.to_hex(c) for c in sns.light_palette(edge, n_colors=10, input="hex")]
        styled[spec["id"]] = {
            **spec,
            "header": wash[3],
            "card": wash[1],
            "chip": wash[2],
        }
    return styled


def _rounded_path(box: Box, radius: float) -> str:
    r = min(radius, 0.48 * box.w, 0.48 * box.h)
    x0, y0, x1, y1 = box.x, box.y, box.right, box.top
    return (
        f"M {x0 + r},{y0} L {x1 - r},{y0} Q {x1},{y0} {x1},{y0 + r} "
        f"L {x1},{y1 - r} Q {x1},{y1} {x1 - r},{y1} "
        f"L {x0 + r},{y1} Q {x0},{y1} {x0},{y1 - r} "
        f"L {x0},{y0 + r} Q {x0},{y0} {x0 + r},{y0} Z"
    )


def _add_round(
    fig: go.Figure,
    box: Box,
    *,
    fill: str,
    edge: str,
    radius: float,
    lw: float = LW,
    dash: str | None = None,
) -> None:
    fig.add_shape(
        type="path",
        path=_rounded_path(box, radius),
        fillcolor=fill,
        line=dict(color=edge, width=lw, dash=dash or "solid"),
        layer="below",
    )


def _text(
    fig: go.Figure,
    x: float,
    y: float,
    text: str,
    *,
    size: float,
    color: str = C_TEXT,
    bold: bool = False,
    align: str = "center",
    xanchor: str = "center",
    yanchor: str = "middle",
    bgcolor: str | None = None,
    border: str | None = None,
    pad: int = 3,
) -> None:
    fig.add_annotation(
        x=x,
        y=y,
        text=f"<b>{text}</b>" if bold else text,
        showarrow=False,
        xref="x",
        yref="y",
        xanchor=xanchor,
        yanchor=yanchor,
        align=align,
        font=dict(family=FONT, size=size, color=color),
        bgcolor=bgcolor,
        bordercolor=border,
        borderwidth=0.9 if border else 0,
        borderpad=pad,
    )


def _arrow(
    fig: go.Figure,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    color: str,
) -> None:
    fig.add_annotation(
        x=x1,
        y=y1,
        ax=x0,
        ay=y0,
        xref="x",
        yref="y",
        axref="x",
        ayref="y",
        text="",
        showarrow=True,
        arrowhead=3,
        arrowsize=0.95,
        arrowwidth=LW,
        arrowcolor=color,
        standoff=1,
        startstandoff=1,
    )


def _polyline(
    fig: go.Figure,
    verts: list[tuple[float, float]],
    *,
    color: str,
    dash: str | None = None,
) -> None:
    xs, ys = zip(*verts)
    fig.add_scatter(
        x=list(xs),
        y=list(ys),
        mode="lines",
        line=dict(color=color, width=LW, dash=dash or "solid"),
        hoverinfo="skip",
        showlegend=False,
    )
    _arrow(fig, verts[-2][0], verts[-2][1], verts[-1][0], verts[-1][1], color=color)


def _layout_layers() -> dict[int, Box]:
    ml, mr, mb, mt = 0.16, 0.16, 0.12, 0.10
    title_h = 0.38
    left_rail, right_rail = 1.58, 1.48
    gap = 0.335
    top = FIG_H - mt - title_h
    bottom = mb
    layer_h = (top - bottom - 4 * gap) / 5
    x = ml + left_rail
    w = FIG_W - ml - mr - left_rail - right_rail
    boxes: dict[int, Box] = {}
    y = top - layer_h
    for i in range(1, 6):
        boxes[i] = Box(x, y, w, layer_h)
        y -= layer_h + gap
    return boxes


def _draw_title(fig: go.Figure) -> None:
    _text(
        fig,
        0.5 * FIG_W,
        FIG_H - 0.16,
        "Layered Threat-Timeline-Driven Quantum-Resistant Federated Learning (QRFL) Architecture",
        size=FS_TITLE,
        bold=True,
    )
    _text(
        fig,
        0.5 * FIG_W,
        FIG_H - 0.36,
        "Forecast  →  PQC agility  →  healthcare FL  →  Fabric governance  →  Mosca migration policy",
        size=FS_BODY,
        color=C_MUTED,
    )


def _draw_layer_shell(fig: go.Figure, spec: dict[str, str], box: Box) -> None:
    _add_round(fig, box, fill=spec["fill"], edge=spec["edge"], radius=R_LAYER)
    header = Box(box.x + 0.045, box.top - 0.33, box.w - 0.09, 0.285)
    _add_round(fig, header, fill=spec["header"], edge=spec["edge"], radius=R_CARD, lw=0.9)
    badge = Box(header.x + 0.05, header.y + 0.04, 0.78, header.h - 0.08)
    _add_round(fig, badge, fill=spec["edge"], edge=spec["edge"], radius=R_CHIP, lw=0.0)
    _text(
        fig,
        badge.cx,
        badge.cy,
        f"L{spec['id']}  {spec['short']}",
        size=FS_BADGE,
        color=C_WHITE,
        bold=True,
    )
    _text(
        fig,
        badge.right + 0.10,
        header.cy,
        spec["title"],
        size=FS_LAYER,
        color=spec["edge"],
        bold=True,
        xanchor="left",
    )


def _draw_cards(fig: go.Figure, spec: dict[str, str], box: Box, modules: tuple) -> None:
    n = len(modules)
    pad_x, pad_y, gap = 0.10, 0.07, 0.085
    header_h = 0.33
    top = box.top - header_h - 0.07
    bot = box.y + pad_y
    h = top - bot
    inner = box.w - 2 * pad_x
    cw = (inner - (n - 1) * gap) / n
    for i, (head, body) in enumerate(modules):
        card = Box(box.x + pad_x + i * (cw + gap), bot, cw, h)
        _add_round(fig, card, fill=spec["card"], edge=spec["edge"], radius=R_CARD, lw=1.05)
        _text(
            fig,
            card.x + 0.09,
            card.top - 0.11,
            head,
            size=FS_HEAD,
            bold=True,
            xanchor="left",
        )
        _text(
            fig,
            card.x + 0.09,
            card.top - 0.24,
            body,
            size=FS_BODY,
            color=C_MUTED,
            align="left",
            xanchor="left",
            yanchor="top",
        )


def _draw_layer5(fig: go.Figure, spec: dict[str, str], box: Box) -> None:
    pad_x, pad_y, gap = 0.10, 0.07, 0.09
    header_h = 0.33
    top = box.top - header_h - 0.07
    bot = box.y + pad_y
    h = top - bot
    inner = box.w - 2 * pad_x - gap
    mosca = Box(box.x + pad_x, bot, 0.40 * inner, h)
    road = Box(mosca.right + gap, bot, 0.60 * inner, h)
    for card, title in ((mosca, "Mosca Risk Assessment"), (road, "Phased Roadmap")):
        _add_round(fig, card, fill=spec["card"], edge=spec["edge"], radius=R_CARD, lw=1.05)
        _text(fig, card.x + 0.09, card.top - 0.10, title, size=FS_HEAD, bold=True, xanchor="left")
    _text(
        fig,
        mosca.x + 0.09,
        mosca.top - 0.24,
        "<i>X</i> + <i>Y</i> &gt; <i>Z</i><br>"
        "<i>X</i>=15 y PHI retention,  <i>Y</i>=5 y migration<br>"
        "Trigger <i>Z</i>=2042.08 (bootstrap 95% LB)<br>"
        "Finish native PQC before 2041",
        size=FS_BODY,
        color=C_MUTED,
        align="left",
        xanchor="left",
        yanchor="top",
    )
    pill_gap = 0.06
    pill_w = (road.w - 0.16 - 3 * pill_gap) / 4
    pill_h = 0.40
    py = road.y + 0.08
    for i, (num, years, action) in enumerate(PHASES):
        px = road.x + 0.08 + i * (pill_w + pill_gap)
        pill = Box(px, py, pill_w, pill_h)
        _add_round(fig, pill, fill=spec["chip"], edge=spec["edge"], radius=R_CHIP, lw=0.85)
        _text(fig, pill.cx, pill.top - 0.11, f"{num}  {years}", size=_pt(9.0), color=spec["edge"], bold=True)
        _text(fig, pill.cx, pill.y + 0.13, action, size=_pt(8.5), color=C_MUTED)
        if i < 3:
            _arrow(fig, pill.right + 0.01, pill.cy, pill.right + pill_gap - 0.01, pill.cy, color=spec["edge"])


def _draw_flows(fig: go.Figure, layers: dict[int, Box], styled: dict[int, dict[str, str]]) -> None:
    l1, l2, l3, l4, l5 = (layers[i] for i in range(1, 6))
    spine = l1.cx
    left_outer = 0.80
    left_inner = l1.x - 0.30
    right_rail = l1.right + 0.32
    right_label = FIG_W - 0.84

    data = (
        (l1, l2, "Cryptographic Parameter Selection<br>(NIST Level 3)"),
        (l2, l3, "Session Encryption &amp; Mask Primitives<br>(ML-KEM-768)"),
        (l3, l4, "Signed Masked Updates Proposal<br>(<i>W</i><sub>u</sub><sup>*</sup>, σ<sub>u</sub>, Cert<sub>u</sub>)"),
    )
    for upper, lower, label in data:
        _arrow(fig, spine, upper.y + 0.02, spine, lower.top - 0.02, color=C_DATA)
        _text(
            fig,
            spine,
            0.5 * (upper.y + lower.top),
            label,
            size=FS_LABEL,
            bgcolor=C_WHITE,
            border=C_DATA,
            pad=5,
        )

    # L1 → L5  threat horizon
    _polyline(
        fig,
        [(l1.x + 0.03, l1.cy), (left_outer, l1.cy), (left_outer, l5.cy), (l5.x - 0.01, l5.cy)],
        color=styled[1]["edge"],
        dash="dash",
    )
    _text(
        fig,
        left_outer,
        l2.cy,
        "Threat Horizon<br>(<i>Z</i>=2042.08)",
        size=FS_LABEL,
        bgcolor=styled[1]["chip"],
        border=styled[1]["edge"],
        pad=4,
    )

    # L5 → L3 / L4  governance
    _polyline(
        fig,
        [
            (l5.x + 0.40, l5.top - 0.02),
            (l5.x + 0.40, l5.top + 0.10),
            (left_inner, l5.top + 0.10),
            (left_inner, l4.cy),
            (l4.x - 0.01, l4.cy),
        ],
        color=C_POLICY,
        dash="dash",
    )
    _polyline(
        fig,
        [(left_inner, l4.cy), (left_inner, l3.cy), (l3.x - 0.01, l3.cy)],
        color=C_POLICY,
        dash="dash",
    )
    _text(
        fig,
        left_outer,
        0.5 * (l4.y + l5.top),
        "Governance Deadlines<br>&amp; Migration Milestones",
        size=FS_LABEL,
        bgcolor=styled[5]["chip"],
        border=C_POLICY,
        pad=4,
    )

    # L4 → L2  DCRL / agility
    _polyline(
        fig,
        [(l4.right + 0.01, l4.cy), (right_rail, l4.cy), (right_rail, l2.cy), (l2.right + 0.01, l2.cy)],
        color=styled[4]["edge"],
        dash="dash",
    )
    _text(
        fig,
        right_label,
        0.5 * (l2.cy + l4.cy),
        "On-Chain DCRL Revocation<br>&amp; Agility Policies",
        size=FS_LABEL,
        bgcolor=styled[4]["chip"],
        border=styled[4]["edge"],
        pad=4,
    )


def plot_architecture(out_dir: Path | None = None, stem: str = STEM) -> go.Figure:
    styled = _apply_seaborn_theme()
    fig = go.Figure()
    fig.update_layout(
        width=CSS_W,
        height=CSS_H,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor=C_WHITE,
        plot_bgcolor=C_WHITE,
        showlegend=False,
        font=dict(family=FONT, color=C_TEXT, size=FS_BODY),
    )
    fig.update_xaxes(range=[0, FIG_W], visible=False, fixedrange=True, constrain="domain")
    fig.update_yaxes(
        range=[0, FIG_H],
        visible=False,
        fixedrange=True,
        scaleanchor="x",
        scaleratio=1,
        constrain="domain",
    )

    layers = _layout_layers()
    _draw_title(fig)
    for spec in (styled[i] for i in range(1, 6)):
        box = layers[spec["id"]]
        _draw_layer_shell(fig, spec, box)
        if spec["id"] != 5:
            _draw_cards(fig, spec, box, MODULES[spec["id"]])
        else:
            _draw_layer5(fig, spec, box)
    _draw_flows(fig, layers, styled)

    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        fig.write_image(out_dir / f"{stem}.pdf", width=CSS_W, height=CSS_H, scale=EXPORT_SCALE)
        fig.write_image(out_dir / f"{stem}.png", width=CSS_W, height=CSS_H, scale=EXPORT_SCALE)

    return fig


def copy_to_manuscript_figs(src_dir: Path, stem: str = STEM) -> None:
    if not _MANUSCRIPT_FIGS.exists():
        _MANUSCRIPT_FIGS.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        src = src_dir / f"{stem}.{ext}"
        if src.exists():
            shutil.copy2(src, _MANUSCRIPT_FIGS / f"{stem}.{ext}")


def main() -> None:
    fig = plot_architecture(_DEFAULT_OUT)
    copy_to_manuscript_figs(_DEFAULT_OUT)
    print("Wrote:")
    for ext in ("pdf", "png"):
        print(f"  {_DEFAULT_OUT / f'{STEM}.{ext}'}")
        print(f"  {_MANUSCRIPT_FIGS / f'{STEM}.{ext}'}")
    _ = fig


if __name__ == "__main__":
    main()
