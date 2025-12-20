import csv
from datetime import datetime
from pathlib import Path

import kaleido
import plotly.graph_objects as go
import plotly.io as pio

DATA_PATH = Path("data.csv")
OUTPUT_PATH = Path("site/index.html")


def load_series(path: Path):
    timestamps = []
    values = []
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue
            timestamp = datetime.fromisoformat(row[0])
            value = float(row[1])
            timestamps.append(timestamp)
            values.append(value)
    if not timestamps:
        raise ValueError("data.csv enthält keine Daten")
    pairs = sorted(zip(timestamps, values), key=lambda item: item[0])
    return [item[0] for item in pairs], [item[1] for item in pairs]


def build_svg(timestamps, values) -> str:
    fig = go.Figure(
        data=[
            go.Scatter(
                x=timestamps,
                y=values,
                mode="lines",
                line=dict(color="#4f46e5", width=3),
                hovertemplate="%{x|%d.%m.%Y %H:%M}<br>Wert: %{y}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        margin=dict(l=40, r=20, t=10, b=40),
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=420,
    )
    fig.update_xaxes(showgrid=False, title_text="Zeit")
    fig.update_yaxes(showgrid=True, gridcolor="#e5e7eb", title_text="Wert")

    try:
        svg_bytes = pio.to_image(fig, format="svg")
    except RuntimeError as exc:
        if "requires Google Chrome" not in str(exc) and "requires Chrome" not in str(exc):
            raise
        kaleido.get_chrome_sync()
        svg_bytes = pio.to_image(fig, format="svg")
    return svg_bytes.decode("utf-8")


def build_html(current_value: float, svg: str) -> str:
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
    .value-card {{
      background: linear-gradient(135deg, #4f46e5, #6366f1);
      border-radius: 20px;
      color: white;
      padding: 28px;
      text-align: center;
    }}
    .value-card h1 {{
      margin: 0;
      font-size: clamp(2.4rem, 4vw, 3.6rem);
      font-weight: 700;
      letter-spacing: 0.03em;
    }}
    .value-card p {{
      margin: 8px 0 0;
      opacity: 0.85;
      font-size: 0.95rem;
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
    <section class=\"value-card\">
      <h1>{int(round(current_value))}</h1>
      <p>Anmeldungen</p>
    </section>
    <section class=\"chart-card\">
      {svg}
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    timestamps, values = load_series(DATA_PATH)
    svg = build_svg(timestamps, values)
    html = build_html(values[-1], svg)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"HTML geschrieben nach {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
