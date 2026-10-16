"""Dashboard + Bet Card PDF built from the workbook's cached (Excel-recalculated) values. Excel's own PDF export needs a printer driver that this machine lacks, so the pages are
rendered with matplotlib from the same cells: output/NBA_Futures_Dashboard_BetCard_<date>.pdf."""
import glob, os, textwrap, datetime
import numpy as np, openpyxl
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
NAVY = "#1F3864"


def pct(v, d=1): return "-" if not isinstance(v, (int, float)) else f"{v * 100:.{d}f}%"
def fx(v): return "-" if v in (None, "-") else str(v)


def table(ax, header, rows, widths, fs=7, wrap=None):
    ax.axis("off"); n = len(header); x = [0]
    for w in widths: x.append(x[-1] + w)
    tot = x[-1]; y = 1.0; hh = 0.03
    for j, h in enumerate(header):
        ax.add_patch(plt.Rectangle((x[j] / tot, y - hh), widths[j] / tot, hh, color=NAVY, transform=ax.transAxes)); ax.text((x[j] + 0.1) / tot, y - hh / 2, h, color="white", fontsize=fs, va="center", transform=ax.transAxes, fontweight="bold")
    y -= hh
    for r in rows:
        lines = max(len(textwrap.wrap(str(c), int(widths[j] * 1.3))) if wrap and j in wrap else 1 for j, c in enumerate(r)); rh = 0.026 * lines
        for j, c in enumerate(r):
            txt = "\n".join(textwrap.wrap(str(c), int(widths[j] * 1.3))) if wrap and j in wrap else str(c)
            ax.text((x[j] + 0.1) / tot, y - 0.005, txt, fontsize=fs, va="top", transform=ax.transAxes)
        y -= rh; ax.plot([0, 1], [y, y], color="#cccccc", lw=0.4, transform=ax.transAxes)
    return y


def main():
    path = sorted(glob.glob(os.path.join(ROOT, "output", "NBA_Futures_Model_v1_*_MS.xlsx")))[-1]; wb = openpyxl.load_workbook(path, data_only=True)
    out = os.path.join(ROOT, "output", f"NBA_Futures_Dashboard_BetCard_{datetime.date.today():%Y%m%d}.pdf")
    D = wb["Dashboard"]; E = wb["Exposure"]; T = wb["Tier1_Card"]; B = wb["Bet_Card"]
    with PdfPages(out) as pdf:
        # ---- page 1: dashboard headline + Tier 1 card
        fig = plt.figure(figsize=(11, 8.5)); fig.text(0.04, 0.95, "NBA 2026-27 Futures Model - Dashboard", fontsize=15, color=NAVY, fontweight="bold")
        fig.text(0.04, 0.925, f"Prices as of 2026-10-15 | workbook {os.path.basename(path)} | {D['B13'].value}", fontsize=8)
        mets = [(D.cell(r, 1).value, D.cell(r, 2).value) for r in range(6, 13)]
        fmt = ["{:.0f}", "{:.0f}", "{:.2%}", "{}", "{:.2%}", "{:.1%}", "{:.2%}"]
        for i, ((k, v), f) in enumerate(zip(mets, fmt)):
            fig.text(0.04, 0.89 - i * 0.022, k, fontsize=8); fig.text(0.42, 0.89 - i * 0.022, f.format(v) if isinstance(v, (int, float)) else str(v), fontsize=8, fontweight="bold")
        ax = fig.add_axes([0.04, 0.05, 0.92, 0.66]); rows = []
        for r in range(8, 20):
            if T.cell(r, 1).value and T.cell(r, 2).value:
                rows.append(("Team", f"{T.cell(r,1).value} {T.cell(r,2).value} {T.cell(r,3).value}", f"{T.cell(r,5).value:+}", pct(T.cell(r, 7).value), pct(T.cell(r, 6).value), pct(T.cell(r, 8).value, 0), pct(T.cell(r, 10).value, 2), str(T.cell(r, 12).value)))
        for r in range(41, 60):
            if T.cell(r, 1).value and T.cell(r, 2).value:
                rows.append(("Player", f"{T.cell(r,1).value} {T.cell(r,2).value}", f"{T.cell(r,4).value:+}", pct(T.cell(r, 6).value), pct(T.cell(r, 5).value), pct(T.cell(r, 7).value, 0), pct(T.cell(r, 9).value, 2), str(T.cell(r, 11).value)))
        fig.text(0.04, 0.73, "Tier 1 card (joint Kelly, total cap 10% of bankroll; stakes as fraction of bankroll)", fontsize=9, color=NAVY, fontweight="bold")
        table(ax, ["Type", "Bet", "Book", "Model", "Fair", "EV", "Stake", "Named driver"], rows, [5, 24, 5, 6, 6, 5, 6, 70], fs=6.5, wrap={7, 1})
        pdf.savefig(fig); plt.close(fig)
        # ---- page 2: charts
        fig, axs = plt.subplots(1, 2, figsize=(11, 8.5)); fig.suptitle("Model vs market", color=NAVY, fontweight="bold")
        names, fair, mod = [], [], []
        for r in range(67, 97):
            if D.cell(r, 1).value and isinstance(D.cell(r, 2).value, (int, float)): names.append(D.cell(r, 1).value); fair.append(D.cell(r, 2).value); mod.append(D.cell(r, 3).value)
        o = np.argsort(fair)[::-1][:12]; y = np.arange(len(o)); ax = axs[0]
        ax.barh(y + 0.2, [fair[i] for i in o], 0.4, label="Market fair", color="#8EA9DB"); ax.barh(y - 0.2, [mod[i] for i in o], 0.4, label="Model", color=NAVY)
        ax.set_yticks(y); ax.set_yticklabels([names[i] for i in o], fontsize=8); ax.invert_yaxis(); ax.set_title("Title probability (top 12 by market)", fontsize=9); ax.legend(fontsize=8)
        bx, by = [], []
        for r in range(32, 62):
            if isinstance(D.cell(r, 2).value, (int, float)): bx.append(D.cell(r, 2).value); by.append(D.cell(r, 3).value)
        ax = axs[1]; ax.scatter(bx, by, color=NAVY, s=14); lim = [min(bx + by) - 1, max(bx + by) + 1]; ax.plot(lim, lim, color="grey", lw=0.6); ax.set_xlabel("Book win total"); ax.set_ylabel("Model mean wins"); ax.set_title("Wins: model vs book", fontsize=9)
        pdf.savefig(fig); plt.close(fig)
        # ---- Bet Card pages (Tier 2 = full card)
        rows = []
        for r in range(8, B.max_row + 1):
            if B.cell(r, 1).value:
                rows.append((B.cell(r, 1).value, B.cell(r, 2).value, B.cell(r, 3).value, fx(B.cell(r, 4).value), f"{B.cell(r,5).value:+}", pct(B.cell(r, 6).value), pct(B.cell(r, 7).value), pct(B.cell(r, 8).value, 0), pct(B.cell(r, 9).value, 0), B.cell(r, 10).value, str(B.cell(r, 15).value)))
        per = 40
        for k in range(0, len(rows), per):
            fig = plt.figure(figsize=(11, 8.5)); fig.text(0.04, 0.95, f"Bet Card - Tier 2 (all qualifying team bets, no stake by default) {k // per + 1}/{-(-len(rows) // per)}", fontsize=12, color=NAVY, fontweight="bold")
            ax = fig.add_axes([0.04, 0.04, 0.92, 0.87]); table(ax, ["Market", "Selection", "Side", "Line", "Book", "Fair", "Model", "EV", "EV lo", "Tier", "Lock (CST)"], rows[k:k + per], [10, 22, 6, 5, 6, 6, 6, 5, 5, 6, 18], fs=6.5)
            pdf.savefig(fig); plt.close(fig)
    return out


if __name__ == "__main__":
    print(main())
