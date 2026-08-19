from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box

from config import PORTFOLIO
from fetcher import fetch_history, fetch_info, fetch_macro
from indicators import rsi, slow_stochastic, ma_deviation
from scorer import valuation_score, technical_score, macro_score, price_score, to_grade

console = Console(width=160)

STARS = {5: "★★★★★", 4: "★★★★☆", 3: "★★★☆☆", 2: "★★☆☆☆", 1: "★☆☆☆☆"}

GRADE_STYLE = {
    "S": "bold magenta",
    "A": "bold green",
    "B": "green",
    "C": "yellow",
    "D": "bold red",
}


def build_table(results: list[dict]) -> Table:
    t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold white on blue",
              expand=False, padding=(0, 1))
    t.add_column("종목",   min_width=5,  style="bold cyan")
    t.add_column("Thesis", min_width=20, no_wrap=True)
    t.add_column("생존",   min_width=7,  justify="center")
    t.add_column("성장",   min_width=7,  justify="center")
    t.add_column("Val",    min_width=4,  justify="right")
    t.add_column("Tech",   min_width=4,  justify="right")
    t.add_column("Macro",  min_width=5,  justify="right")
    t.add_column("Score",  min_width=5,  justify="right")
    t.add_column("Grade",  min_width=5,  justify="center")
    t.add_column("Action", min_width=18, no_wrap=True)

    for r in results:
        grade_text = Text(r["grade"], style=GRADE_STYLE.get(r["grade"], "white"))
        t.add_row(
            r["symbol"],
            r["thesis"],
            STARS.get(r["survival"], "?"),
            STARS.get(r["growth"], "?"),
            f"{r['val']:.0f}" if r["val"] else "—",
            f"{r['tech']:.0f}" if r["tech"] else "—",
            f"{r['macro']:.0f}",
            f"{r['score']:.0f}" if r["score"] else "—",
            grade_text,
            r["action"],
        )
    return t


def main():
    console.print("\n[bold cyan]📊 Investment Dashboard[/bold cyan] — loading...\n")

    # Macro (shared across all tickers)
    try:
        macro = fetch_macro()
        m_score, m_detail = macro_score(macro)
        console.print(f"[dim]Macro: {m_detail}[/dim]\n")
    except Exception as e:
        console.print(f"[yellow]Macro fetch failed ({e}), using defaults[/yellow]\n")
        macro = {"t10y": 4.3, "t30y": 4.6, "t10y2y": 0.1}
        m_score, m_detail = macro_score(macro)

    results = []
    for symbol, cfg in PORTFOLIO.items():
        ticker = cfg["ticker"]
        row = {
            "symbol": symbol,
            "thesis": cfg["thesis"],
            "survival": cfg["survival"],
            "growth": cfg["growth"],
            "macro": m_score,
            "val": None,
            "tech": None,
            "score": None,
            "grade": "—",
            "action": "—",
        }
        try:
            hist = fetch_history(ticker)
            info = fetch_info(ticker)

            closes = hist["Close"]
            v_score, v_detail = valuation_score(info)
            t_score, t_detail = technical_score(
                rsi(closes),
                *slow_stochastic(hist["High"], hist["Low"], closes),
                ma_deviation(closes),
            )
            # valuation N/A(50=neutral)이면 tech+macro만으로 판단
            effective_val = v_score if v_detail != "N/A" else None
            s = price_score(
                effective_val if effective_val is not None else 50,
                t_score, m_score,
            )
            grade, action = to_grade(s)

            row.update({"val": v_score, "tech": t_score, "score": s,
                         "grade": grade, "action": action})
            console.print(f"[dim]  {symbol:<6} val={v_detail}  tech={t_detail}[/dim]")
        except Exception as e:
            row["action"] = f"ERR: {e}"

        results.append(row)

    console.print()
    console.print(build_table(results))
    console.print()


if __name__ == "__main__":
    main()
