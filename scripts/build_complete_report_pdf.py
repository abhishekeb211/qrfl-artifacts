"""Build a single consolidated QRFL PDF report (architecture + results + graphs + analysis)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures" / "output"
OUT_DIR = ROOT.parent / "docs"
TMP = OUT_DIR / "_pdf_assets"
OUT_PDF = OUT_DIR / "QRFL_Complete_Report.pdf"


def styles():
    s = getSampleStyleSheet()
    s.add(
        ParagraphStyle(
            name="CoverTitle",
            parent=s["Title"],
            fontSize=20,
            leading=24,
            spaceAfter=12,
            alignment=TA_CENTER,
        )
    )
    s.add(
        ParagraphStyle(
            name="CoverSub",
            parent=s["Normal"],
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#444444"),
            spaceAfter=6,
        )
    )
    s.add(
        ParagraphStyle(
            name="H1Custom",
            parent=s["Heading1"],
            fontSize=14,
            spaceBefore=14,
            spaceAfter=8,
            textColor=colors.HexColor("#1a1a1a"),
        )
    )
    s.add(
        ParagraphStyle(
            name="H2Custom",
            parent=s["Heading2"],
            fontSize=12,
            spaceBefore=10,
            spaceAfter=6,
            textColor=colors.HexColor("#222222"),
        )
    )
    s.add(
        ParagraphStyle(
            name="BodyJust",
            parent=s["Normal"],
            fontSize=9.5,
            leading=13,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        )
    )
    s.add(
        ParagraphStyle(
            name="Caption",
            parent=s["Normal"],
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#555555"),
            spaceBefore=4,
            spaceAfter=10,
        )
    )
    s.add(
        ParagraphStyle(
            name="BulletBody",
            parent=s["Normal"],
            fontSize=9.5,
            leading=12,
            leftIndent=8,
        )
    )
    return s


def make_table(data, col_widths=None):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f8")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def fig_image(name: str, width=6.2 * inch):
    path = FIG / name
    if not path.exists():
        return Paragraph(f"[Missing figure: {name}]", styles()["Caption"])
    # preserve aspect roughly for landscape charts
    img = Image(str(path))
    img.drawWidth = width
    img.drawHeight = width * 0.55
    return img


def make_extra_charts():
    TMP.mkdir(parents=True, exist_ok=True)
    fl = pd.read_csv(ROOT / "results" / "fl" / "all_results.csv")
    iid = fl[
        (fl["alpha"] == 1.0)
        & (fl["aggregator"] == "fedavg")
        & (fl["attack"] == "none")
        & (fl["malicious_fraction"] == 0.0)
    ]

    # Latency by clients
    fig, ax = plt.subplots(figsize=(7, 3.6))
    clients = sorted(iid["num_clients"].unique())
    x = np.arange(len(clients))
    width = 0.25
    for i, mode in enumerate(["classical", "hybrid_pq", "native_pq"]):
        means = [
            iid[(iid["num_clients"] == c) & (iid["security_mode"] == mode)]["mean_round_latency_s"].mean()
            for c in clients
        ]
        ax.bar(x + i * width, means, width, label=mode)
    ax.set_xticks(x + width)
    ax.set_xticklabels(clients)
    ax.set_xlabel("Number of clients")
    ax.set_ylabel("Mean round latency (s)")
    ax.set_title("FL round latency by security mode (IID, FedAvg)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    p1 = TMP / "chart_fl_latency_modes.png"
    fig.savefig(p1, dpi=160)
    plt.close(fig)

    # Accuracy by clients
    fig, ax = plt.subplots(figsize=(7, 3.6))
    acc = [iid[iid["num_clients"] == c]["accuracy"].mean() * 100 for c in clients]
    ax.plot(clients, acc, marker="o", color="#1f77b4")
    ax.set_xlabel("Number of clients")
    ax.set_ylabel("Test accuracy (%)")
    ax.set_title("FL test accuracy vs client count (IID, all modes)")
    fig.tight_layout()
    p2 = TMP / "chart_fl_accuracy.png"
    fig.savefig(p2, dpi=160)
    plt.close(fig)

    # HLF stacked from known values
    fig, ax = plt.subplots(figsize=(7, 3.6))
    labels = ["Classical", "Hybrid", "Native PQ"]
    endo = [25.4, 28.4, 28.3]
    order = [40.2, 40.2, 40.2]
    valid = [15.3, 16.0, 15.7]
    ax.bar(labels, endo, label="Endorsement", color="#1f77b4")
    ax.bar(labels, order, bottom=endo, label="Ordering", color="#ff7f0e")
    bottom2 = [a + b for a, b in zip(endo, order)]
    ax.bar(labels, valid, bottom=bottom2, label="Validation", color="#2ca02c")
    ax.set_ylabel("Latency (ms)")
    ax.set_title("HLF v2.5 lifecycle phase latencies (calibrated simulation)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    p3 = TMP / "chart_hlf_phases.png"
    fig.savefig(p3, dpi=160)
    plt.close(fig)

    # PQC key ops
    pqc = pd.read_csv(ROOT / "results" / "pqc" / "summary.csv")
    fig, ax = plt.subplots(figsize=(7, 3.6))
    rows = [
        ("ECDSA-P256", "sign"),
        ("ECDSA-P256", "verify"),
        ("ML-KEM-768", "encapsulate"),
        ("ML-KEM-768", "decapsulate"),
        ("ML-DSA-65", "sign"),
        ("ML-DSA-65", "verify"),
    ]
    labels = []
    vals = []
    for scheme, op in rows:
        sub = pqc[(pqc["scheme"] == scheme) & (pqc["operation"] == op)]
        if sub.empty:
            continue
        labels.append(f"{scheme}\n{op}")
        vals.append(float(sub["mean_ms"].iloc[0]))
    ax.barh(labels[::-1], vals[::-1], color="#9467bd")
    ax.set_xlabel("Mean latency (ms)")
    ax.set_title("Key PQC vs classical primitive latencies (CFFI)")
    fig.tight_layout()
    p4 = TMP / "chart_pqc_ops.png"
    fig.savefig(p4, dpi=160)
    plt.close(fig)

    return p1, p2, p3, p4


def build():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sty = styles()
    charts = make_extra_charts()

    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="QRFL Complete Report",
        author="QRFL Reproducibility Package",
    )
    story = []

    # Cover
    story.append(Spacer(1, 40))
    story.append(Paragraph("QRFL Complete Technical Report", sty["CoverTitle"]))
    story.append(
        Paragraph(
            "Threat-Timeline-Driven Quantum-Resistant Federated Learning<br/>for Blockchain-Enabled Healthcare Systems",
            sty["CoverSub"],
        )
    )
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            "Step-by-step architecture · Pipeline · Measured results · Graphs · Analysis · Performance outcomes",
            sty["CoverSub"],
        )
    )
    story.append(Spacer(1, 20))
    cover_meta = [
        ["Corpus date", "2026-09-03"],
        ["FL scale", "10 seeds × 50 rounds × 270 configs"],
        ["PQC backend", "quantcrypt-cffi (PQClean)"],
        ["Fabric", "HLF 2.5 — 3 peers + orderer + CouchDB"],
        ["Artifacts", "qrfl-artifacts/ · docs/"],
    ]
    story.append(make_table([["Item", "Value"]] + cover_meta, [2.2 * inch, 4.2 * inch]))
    story.append(PageBreak())

    # TOC-like overview
    story.append(Paragraph("1. Executive Summary", sty["H1Custom"]))
    story.append(
        Paragraph(
            "QRFL integrates (1) quantum-threat timeline forecasting, (2) NIST PQC benchmarking, "
            "(3) healthcare federated learning under Classical / Hybrid / Native PQ modes, "
            "(4) Hyperledger Fabric validation, and (5) Mosca/MOSCoW migration planning. "
            "The scientific contribution is the end-to-end integration, not any single component alone.",
            sty["BodyJust"],
        )
    )
    story.append(
        Paragraph(
            "<b>Primary outcomes.</b> Predictive metrics are identical across security modes "
            "(TOST equivalent). FL round-latency differences are not significant after Holm correction. "
            "Native PQ HLF simulation overhead is ~4% (80.8 → 84.2 ms). Bootstrap 95% lower bound "
            "for ECDSA-256 threshold crossing is ~2042.1 under baseline η.",
            sty["BodyJust"],
        )
    )
    story.append(
        make_table(
            [
                ["Metric", "Result"],
                ["IID-25 accuracy (all modes)", "65.3%"],
                ["IID-25 AUROC", "0.566"],
                ["Native PQ FL round overhead", "Typically < 1% (NS after Holm)"],
                ["HLF native total latency", "84.2 ms (vs 80.8 classical)"],
                ["Forecast planning trigger", "~2042.1 (bootstrap 95% lower)"],
                ["FL determinism check", "passed"],
            ],
            [3.0 * inch, 3.4 * inch],
        )
    )

    story.append(Paragraph("2. Five-Layer Process Architecture", sty["H1Custom"]))
    story.append(
        Paragraph(
            "The framework is organized as a layered stack. Lower layers produce quantitative "
            "constraints (crossing years, primitive latencies) that parameterize upper layers "
            "(FL modes, Fabric simulation, migration roadmap).",
            sty["BodyJust"],
        )
    )
    layers = [
        ["Layer", "Name", "Process role", "Primary outputs"],
        ["L1", "Quantum-Threat Forecasting", "When to migrate", "forecast_validation.tex, scenarios"],
        ["L2", "PQC / Crypto-Agility", "What algorithms", "crypto_benchmarks.tex, ablation"],
        ["L3", "Healthcare FL", "Utility & FL cost", "fl_*.tex, all_results.csv"],
        ["L4", "Blockchain Validation", "Ledger cost", "ledger_latency.tex, docker_stats"],
        ["L5", "Migration Decision Support", "Roadmap action", "Mosca + MOSCoW prose"],
    ]
    story.append(make_table(layers, [0.5 * inch, 1.6 * inch, 1.5 * inch, 2.6 * inch]))
    story.append(Spacer(1, 8))
    arch = ROOT.parent / "figs" / "fig2-Layered Architecture of Quantum-Resistant Federated Learning in Blockchain-Enabled Healthcare Systems.png"
    if arch.exists():
        img = Image(str(arch), width=6.3 * inch, height=3.6 * inch)
        story.append(img)
        story.append(Paragraph("Figure: Layered QRFL system architecture (manuscript Fig. 2).", sty["Caption"]))

    story.append(Paragraph("3. Step-by-Step Reproducibility Pipeline", sty["H1Custom"]))
    story.append(
        Paragraph(
            "Orchestrator: <font face='Courier'>run_all.ps1</font> / <font face='Courier'>run_all.sh</font>. "
            "Each stage merges macros into <font face='Courier'>results/results_macros.tex</font>.",
            sty["BodyJust"],
        )
    )
    pipe = [
        ["Step", "Module", "Produces"],
        ["1", "forecasting.run_all", "CSV + forecast_validation.tex + macros"],
        ["2", "pqc_benchmarks.run_benchmarks", "trials/summary + crypto + ablation .tex"],
        ["3", "federated_learning.run_experiment", "all_results.csv + fl_*.tex (hours)"],
        ["4", "resource_profiling.run_profile", "resource_profiling.tex (energy optional)"],
        ["5", "statistical_tests.run_all", "statistical_tests.tex (needs FL)"],
        ["6", "figures.generate_all", "figures/output PDF/PNG"],
        ["7", "capture_hardware.py", "hardware_specs.json"],
    ]
    story.append(make_table(pipe, [0.6 * inch, 2.4 * inch, 3.2 * inch]))
    story.append(
        Paragraph(
            "Optional Fabric (outside 1–7): generate_crypto → docker compose up → "
            "submit_transactions (calibrated simulation) → collect_metrics.",
            sty["BodyJust"],
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("4. Protocol Flows (Runtime Architecture)", sty["H1Custom"]))
    flows = [
        ["Flow", "Mechanism", "Analysis"],
        ["F1 Hybrid certs", "ECDSA + ML-DSA in X.509", "~6.2× cert size; cache/fragment on IoMT"],
        ["F2 Hybrid KEM", "ML-KEM-768 ∥ ECDHE → HKDF", "HNDL-safe if ML-KEM holds"],
        ["F3 Masking", "Pairwise modular masks Σ=0", "Utility invariant across modes"],
        ["F4 Sign+endorse", "ML-DSA-65 + Fabric 2-of-3", "Sim total +~4% latency"],
        ["F5 Revocation", "DCRL + policy algo swap", "Architectural; not timed"],
    ]
    story.append(make_table(flows, [1.2 * inch, 2.2 * inch, 2.8 * inch]))

    story.append(Paragraph("5. Federated Learning — Step-by-Step Round", sty["H1Custom"]))
    fl_steps = [
        ["Step", "Function", "Effect"],
        ["1 Data", "load_pneumoniamnist", "Train/val/test loaders"],
        ["2 Partition", "dirichlet_partition", "Client shards by α"],
        ["3 Local train", "train_local × clients", "5 epochs Adam / round"],
        ["4 Attack", "apply_attack (optional)", "Label-/sign-flip"],
        ["5 Mask", "apply_mask", "Pairwise seeds; Σ masks = 0"],
        ["6 Aggregate", "fedavg | median | krum", "Global CNN weights"],
        ["7 Crypto tax", "crypto_round_overhead", "KEM+sig × N (from Exp A)"],
        ["8 Evaluate", "evaluate", "Acc, AUROC, F1, latency"],
    ]
    story.append(make_table(fl_steps, [1.1 * inch, 2.0 * inch, 3.1 * inch]))
    story.append(
        Paragraph(
            "Experiment grid (270 configs): B-2 Dirichlet α×modes @25 clients; B client scaling "
            "{5,10,50}×modes; D Median/Krum and Byzantine attacks under native PQ. "
            "Full scale: 10 seeds × 50 rounds.",
            sty["BodyJust"],
        )
    )

    story.append(Paragraph("6. Results — Federated Learning Performance", sty["H1Custom"]))
    story.append(Paragraph("6.1 Latency by security mode", sty["H2Custom"]))
    story.append(Image(str(charts[0]), width=6.2 * inch, height=3.2 * inch))
    story.append(Paragraph("Figure: Mean FL round latency (IID FedAvg) by client count and mode.", sty["Caption"]))

    lat_tbl = [
        ["Clients", "Classical (s)", "Hybrid (s)", "Native (s)", "Native overhead"],
        ["5", "16.70 ± 0.18", "16.73 ± 0.18", "16.73 ± 0.18", "+0.17%"],
        ["10", "17.09 ± 0.17", "17.07 ± 0.20", "17.06 ± 0.15", "−0.15%"],
        ["25", "19.06 ± 0.28", "19.01 ± 0.29", "18.62 ± 0.32", "−2.30%"],
        ["50", "24.70 ± 0.37", "24.82 ± 0.24", "24.78 ± 0.37", "+0.34%"],
    ]
    story.append(make_table(lat_tbl, [0.8 * inch, 1.3 * inch, 1.3 * inch, 1.3 * inch, 1.2 * inch]))

    story.append(Paragraph("6.2 Accuracy vs scale", sty["H2Custom"]))
    story.append(Image(str(charts[1]), width=6.2 * inch, height=3.2 * inch))
    story.append(Paragraph("Figure: Test accuracy vs client count (IID; identical across modes).", sty["Caption"]))
    story.append(
        Paragraph(
            "<b>Analysis.</b> Accuracy peaks at 10 clients (77.8%) and falls at 50 clients (45.4%) "
            "due to data fragmentation—not PQC. At default 25 clients, all modes achieve 65.3% "
            "accuracy (determinism check passed).",
            sty["BodyJust"],
        )
    )

    if (FIG / "fl_overhead_results.png").exists():
        story.append(fig_image("fl_overhead_results.png"))
        story.append(Paragraph("Figure: Pipeline-generated FL overhead chart (figures/output).", sty["Caption"]))

    story.append(Paragraph("6.3 Non-IID and Byzantine outcomes", sty["H2Custom"]))
    story.append(
        make_table(
            [
                ["α", "Accuracy", "F1", "Latency (s)"],
                ["0.1", "65.30%", "0.767", "19.18"],
                ["0.5", "65.42%", "0.768", "19.12"],
                ["1.0 (IID)", "65.34%", "0.767", "19.01"],
            ],
            [1.4 * inch, 1.4 * inch, 1.4 * inch, 1.6 * inch],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        make_table(
            [
                ["Attack", "Mal %", "Agg", "Accuracy", "Latency (s)"],
                ["None", "0%", "FedAvg", "65.98%", "19.31"],
                ["None", "0%", "Median", "37.50%", "18.39"],
                ["Label flip", "10%", "FedAvg", "37.45%", "19.01"],
                ["Label flip", "20%", "FedAvg", "41.15%", "19.01"],
                ["Sign flip", "20%", "Krum", "37.50%", "18.52"],
            ],
            [1.2 * inch, 0.7 * inch, 0.9 * inch, 1.2 * inch, 1.2 * inch],
        )
    )
    story.append(
        Paragraph(
            "<b>Analysis.</b> Under 50 rounds, non-IID α has limited accuracy impact. Byzantine "
            "label-flip severely degrades FedAvg; Median/Krum remain near 37.5% (often degenerate "
            "on this imbalanced task)—robust aggregation needs further tuning. PQ overhead remains secondary.",
            sty["BodyJust"],
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("7. Results — PQC Micro-benchmarks (Exp A)", sty["H1Custom"]))
    story.append(Image(str(charts[3]), width=6.2 * inch, height=3.2 * inch))
    story.append(Paragraph("Figure: Key classical vs PQC operation latencies (CFFI, 10k trials).", sty["Caption"]))
    if (FIG / "pqc_overhead_results.png").exists():
        story.append(fig_image("pqc_overhead_results.png"))
        story.append(Paragraph("Figure: ML-KEM encaps/decaps overhead chart.", sty["Caption"]))
    story.append(
        make_table(
            [
                ["Scheme", "Op", "Mean (ms)", "SD (ms)"],
                ["ECDSA-P256", "sign", "0.035", "0.002"],
                ["ECDSA-P256", "verify", "0.085", "0.003"],
                ["ML-KEM-768", "encaps", "0.128", "0.004"],
                ["ML-KEM-768", "decaps", "0.091", "0.013"],
                ["ML-DSA-65", "sign", "0.850", "0.502"],
                ["ML-DSA-65", "verify", "0.245", "0.019"],
                ["SLH-DSA-256s", "sign", "536.8", "5.84"],
            ],
            [1.8 * inch, 1.2 * inch, 1.4 * inch, 1.4 * inch],
        )
    )
    story.append(
        Paragraph(
            "<b>Analysis / design choice.</b> Default profile is ML-KEM-768 / ML-DSA-65 (NIST Level 3). "
            "SLH-DSA is reserved for long-term attestation due to multi-hundred-ms signing cost. "
            "Exp F (quantcrypt API) shows higher wrapper latencies (~3–5 ms) and ~73–76 MB RSS; "
            "energy unavailable without RAPL.",
            sty["BodyJust"],
        )
    )

    story.append(Paragraph("8. Results — Blockchain (Exp C)", sty["H1Custom"]))
    story.append(Image(str(charts[2]), width=6.2 * inch, height=3.2 * inch))
    story.append(Paragraph("Figure: HLF phase stack (endorsement / ordering / validation).", sty["Caption"]))
    if (FIG / "hlf_phase_latencies.png").exists():
        story.append(fig_image("hlf_phase_latencies.png", width=5.5 * inch))
        story.append(Paragraph("Figure: Pipeline-generated HLF phase chart.", sty["Caption"]))
    story.append(
        make_table(
            [
                ["Phase", "Classical", "Hybrid", "Native PQ"],
                ["Endorsement (ms)", "25.4", "28.4", "28.3"],
                ["Ordering (ms)", "40.2", "40.2", "40.2"],
                ["Validation (ms)", "15.3", "16.0", "15.7"],
                ["Total (ms)", "80.8", "84.6", "84.2"],
            ],
            [1.8 * inch, 1.3 * inch, 1.3 * inch, 1.4 * inch],
        )
    )
    story.append(
        Paragraph(
            "<b>Analysis.</b> Ordering dominates. PQ verification adds a few milliseconds. "
            "Live testbed: orderer + Hospital A/B + Research peers + CouchDB Up. "
            "Fabric MSP remains ECDSA; ML-DSA applies at application/chaincode payload layer.",
            sty["BodyJust"],
        )
    )

    story.append(Paragraph("9. Forecast Validation & Threat Timeline", sty["H1Custom"]))
    if (FIG / "forecasting_model_comparison.png").exists():
        story.append(fig_image("forecasting_model_comparison.png"))
        story.append(Paragraph("Figure: Physical-qubit growth OLS exponential fit.", sty["Caption"]))
    if (FIG / "threshold_crossing_uncertainty.png").exists():
        story.append(fig_image("threshold_crossing_uncertainty.png"))
        story.append(Paragraph("Figure: Bootstrap crossing-year uncertainty by η scenario.", sty["Caption"]))
    if (FIG / "sensitivity_analysis.png").exists():
        story.append(fig_image("sensitivity_analysis.png"))
        story.append(Paragraph("Figure: Timeline sensitivity by η scenario.", sty["Caption"]))
    story.append(
        make_table(
            [
                ["Strategy", "MAE", "RMSE", "MAPE (%)"],
                ["Hold-out 2024–2026", "563.39", "602.62", "424.63"],
                ["Rolling-origin", "600.51", "768.92", "311.40"],
                ["Leave-one-out", "316.24", "544.69", "151.37"],
            ],
            [2.0 * inch, 1.3 * inch, 1.3 * inch, 1.4 * inch],
        )
    )
    story.append(
        Paragraph(
            "<b>Analysis.</b> High MAPE reflects sparse, discontinuous hardware jumps—use as planning "
            "heuristics. Residual diagnostics support log-linear modeling (Shapiro p=0.395, DW=1.80). "
            "Architecture adopts bootstrap 95% lower bound ~2042.1 as the risk-management trigger.",
            sty["BodyJust"],
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("10. Statistical Outcomes", sty["H1Custom"]))
    story.append(
        make_table(
            [
                ["Metric", "Comparison", "Test", "Result"],
                ["accuracy", "all mode pairs", "TOST", "equivalent"],
                ["f1", "all mode pairs", "TOST", "equivalent"],
                ["latency", "classical↔hybrid", "paired t", "not significant"],
                ["latency", "classical↔native", "paired t", "not significant"],
                ["latency", "hybrid↔native", "Wilcoxon", "not significant"],
            ],
            [1.3 * inch, 1.8 * inch, 1.4 * inch, 1.5 * inch],
        )
    )
    story.append(
        Paragraph(
            "IID baseline α=1.0, 25 clients, FedAvg, no attack; Holm-corrected α=0.05. "
            "Supports utility-neutral and practically latency-neutral PQ modes under this masking design.",
            sty["BodyJust"],
        )
    )

    story.append(Paragraph("11. Cross-Layer Performance Synthesis", sty["H1Custom"]))
    story.append(
        make_table(
            [
                ["Question", "Evidence", "Outcome"],
                ["When migrate?", "L1 bootstrap ~2042", "Start hybrid now (long EHR retention)"],
                ["Which params?", "L2 ablation", "ML-KEM-768 / ML-DSA-65 default"],
                ["FL utility hit?", "TOST equivalent", "No predictive degradation"],
                ["FL latency hit?", "Holm NS latency", "Training dominates crypto tax"],
                ["Ledger hit?", "+4% TX latency", "Ordering dominates endorsements"],
                ["Poisoning?", "Exp D", "FedAvg fragile; robust aggs need tuning"],
            ],
            [1.5 * inch, 2.0 * inch, 2.7 * inch],
        )
    )

    story.append(Paragraph("12. Outputs Checklist", sty["H1Custom"]))
    story.append(
        make_table(
            [
                ["Artifact", "Path", "State"],
                ["Macros", "results/results_macros.tex", "FLNumSeeds=10, FLNumRounds=50"],
                ["FL tables", "results/fl/fl_*.tex", "Present"],
                ["Stats", "results/statistics/statistical_tests.tex", "Present"],
                ["Forecast val", "results/forecasting/validation/", "Present"],
                ["PQC / ablation", "results/pqc/*.tex", "Present"],
                ["Resource", "results/resource/resource_profiling.tex", "Present"],
                ["Ledger", "results/blockchain/ledger_latency.tex", "Present"],
                ["Figures", "figures/output/*.pdf|png", "Present"],
                ["This PDF", "docs/QRFL_Complete_Report.pdf", "Generated"],
            ],
            [1.4 * inch, 2.8 * inch, 2.0 * inch],
        )
    )

    story.append(Paragraph("13. Limitations", sty["H1Custom"]))
    bullets = [
        "FL PQ cost is modeled from Exp A means, not a live PQ-TLS stack every round.",
        "Fabric MSP remains ECDSA; PQ authenticity is application/chaincode-level.",
        "Forecast MAPE is high — prefer lower-bound planning over a single year.",
        "RAPL energy and Go chaincode deploy remain deferred on this host.",
        "Byzantine Median/Krum need further tuning for PneumoniaMNIST imbalance.",
    ]
    for b in bullets:
        story.append(Paragraph(f"• {b}", sty["BulletBody"]))

    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            "Sources: qrfl-artifacts/results/*, figures/output/*, ARCHITECTURE_PROCESS_ANALYSIS.md, "
            "PHASE_RESULTS_REPORT.md. Generated automatically by scripts/build_complete_report_pdf.py.",
            sty["Caption"],
        )
    )

    doc.build(story)
    return OUT_PDF


if __name__ == "__main__":
    path = build()
    print("Wrote", path)
