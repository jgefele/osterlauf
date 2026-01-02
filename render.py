import csv
from datetime import datetime
from pathlib import Path

import kaleido
import plotly.graph_objects as go
import plotly.io as pio

DATA_PATH = Path("data.csv")
OUTPUT_PATH = Path("docs/index.html")


def load_series(path: Path):
    timestamps = []
    total_values = []
    rueweler_values: list[float | None] = []
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue
            timestamp = datetime.fromisoformat(row[0])
            total_value = float(row[1])
            rueweler_value: float | None = None
            if len(row) >= 3 and row[2].strip():
                try:
                    rueweler_value = float(row[2])
                except ValueError:
                    rueweler_value = None
            timestamps.append(timestamp)
            total_values.append(total_value)
            rueweler_values.append(rueweler_value)
    if not timestamps:
        raise ValueError("data.csv enthält keine Daten")
    pairs = sorted(
        zip(timestamps, total_values, rueweler_values), key=lambda item: item[0]
    )
    return (
        [item[0] for item in pairs],
        [item[1] for item in pairs],
        [item[2] for item in pairs],
    )


def build_svg(timestamps, total_values) -> str:
    fig = go.Figure(
        data=[
            go.Scatter(
                x=timestamps,
                y=total_values,
                mode="lines",
                name="Anmeldungen gesamt",
                line=dict(color="#4f46e5", width=3),
                hovertemplate="%{x|%d.%m.%Y %H:%M}<br>Gesamt: %{y}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        margin=dict(l=40, r=20, t=10, b=40),
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=False, title_text="Zeit")
    fig.update_yaxes(showgrid=True, gridcolor="#e5e7eb", title_text="Anzahl")

    try:
        svg_bytes = pio.to_image(fig, format="svg")
        return svg_bytes.decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        print(
            "Kaleido konnte kein SVG rendern, weiche auf Plotly.js aus:",
            exc,
        )
        return pio.to_html(
            fig, include_plotlyjs="cdn", full_html=False, config={"displaylogo": False}
        )


def build_html(total_current: float, rueweler_current: float, svg: str) -> str:
    return f"""<!DOCTYPE html>
<html lang=\"de\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Anmeldungen zum Paderborner Osterlauf 2026</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
      background: #f3f4f6;
    }}
    body {{
      margin: 0;
      padding: 32px 20px 48px;
      display: flex;
      justify-content: center;
    }}
    .dashboard {{
      width: min(1100px, 100%);
      background: white;
      border-radius: 24px;
      box-shadow: 0 24px 60px rgba(15, 23, 42, 0.12);
      padding: 32px clamp(20px, 4vw, 40px) 40px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }}
    .value-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
    }}
    .value-card {{
      border-radius: 18px;
      color: white;
      padding: 24px 24px 20px;
      text-align: left;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .value-card h1 {{
      margin: 0;
      font-size: clamp(2.2rem, 3vw, 3.4rem);
      font-weight: 700;
      letter-spacing: 0.02em;
    }}
    .value-card p {{
      margin: 0;
      opacity: 0.9;
      font-size: 0.95rem;
    }}
    .value-card.total {{
      background: linear-gradient(135deg, #4f46e5, #6366f1);
      box-shadow: 0 16px 40px rgba(99, 102, 241, 0.3);
    }}
    .value-card.rueweler {{
      background: linear-gradient(135deg, #10b981, #34d399);
      box-shadow: 0 16px 40px rgba(52, 211, 153, 0.28);
    }}
    .chart-card {{
      background: #f9fafb;
      border-radius: 20px;
      padding: 16px;
      overflow: hidden;
    }}
    .chart-card svg {{
      width: 100%;
      height: auto;
      display: block;
    }}
    @media (max-width: 640px) {{
      .dashboard {{
        padding: 24px 16px 32px;
      }}
      .value-card {{
        padding: 20px;
      }}
    }}
  </style>
</head>
<body>
  <main class=\"dashboard\">
    <section class=\"value-grid\">
      <article class=\"value-card total\">
        <p>Gesamt angemeldet</p>
        <h1>{int(round(total_current))}</h1>
      </article>
      <article class=\"value-card rueweler\">
        <p>Rüweler aktuell</p>
        <h1>{int(round(rueweler_current))}</h1>
      </article>
    </section>
    <section class=\"chart-card\">
      {svg}
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    timestamps, totals, rueweler_counts = load_series(DATA_PATH)
    svg = build_svg(timestamps, totals)
    rueweler_current = next(
        (value for value in reversed(rueweler_counts) if value is not None), 0
    )
    html = build_html(totals[-1], rueweler_current, svg)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"HTML geschrieben nach {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
