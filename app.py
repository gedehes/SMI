import io
import re
import pandas as pd
import requests
import streamlit as st

# ==============================================================================
# Extracteur Regex en pur Python (contourne le besoin de lxml / bs4)
# ==============================================================================


def _extract_tickers_regex(html_text: str) -> list[str]:
    """Extrait les symboles boursiers directement du HTML sans dépendance externe (sans lxml)."""
    match = re.search(
        r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>',
        html_text,
        re.DOTALL,
    )
    if not match:
        return []

    table_content = match.group(1)
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_content, re.DOTALL)

    tickers = []
    for row in rows[1:]:
        cols = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        if cols:
            for col in cols[:2]:
                text_match = re.search(
                    r'<a[^>]*>([^<]+)</a>', col
                ) or re.search(r'^\s*([A-Z0-9\.\-]+)\s*$', col)
                if text_match:
                    symbol = text_match.group(1).strip()
                    if (
                        re.match(r"^[A-Z]{1,5}(\.[A-Z]{1,2})?$", symbol)
                        and symbol != "SEC"
                    ):
                        tickers.append(symbol.replace(".", "-"))
                        break
    return tickers


# ==============================================================================
# Fonctions de récupération silencieuses (sans aucun avertissement UI)
# ==============================================================================


@st.cache_data(ttl=43200)
def get_sp500_tickers() -> list[str]:
    default_sp500 = [
        "AAPL",
        "MSFT",
        "NVDA",
        "AMZN",
        "GOOGL",
        "META",
        "BRK-B",
        "LLY",
        "AVGO",
        "TSLA",
        "JPM",
        "WMT",
        "UNH",
        "V",
        "XOM",
        "MA",
        "PG",
        "COST",
        "HD",
        "JNJ",
    ]
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # 1. Tentative via Pandas
        try:
            tables = pd.read_html(io.StringIO(response.text))
            df = tables[0]
            tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
            return [
                str(t).strip().upper()
                for t in tickers
                if isinstance(t, str) and t.strip()
            ]
        except Exception:
            # 2. Secours automatique via Regex (ne requiert pas lxml)
            fallback = _extract_tickers_regex(response.text)
            if fallback:
                return fallback
    except Exception:
        pass

    # 3. Secours ultime silencieux
    return default_sp500


@st.cache_data(ttl=43200)
def get_nasdaq100_tickers() -> list[str]:
    default_nasdaq = [
        "AAPL",
        "MSFT",
        "NVDA",
        "AMZN",
        "GOOGL",
        "META",
        "TSLA",
        "AVGO",
        "COST",
        "NFLX",
        "AMD",
        "TMUS",
        "PEP",
        "CSCO",
        "ADBE",
        "TXN",
        "AMAT",
        "QCOM",
        "INTC",
        "AMGN",
    ]
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # 1. Tentative via Pandas
        try:
            tables = pd.read_html(io.StringIO(response.text))
            for t in tables:
                col = (
                    "Ticker"
                    if "Ticker" in t.columns
                    else ("Symbol" if "Symbol" in t.columns else None)
                )
                if col:
                    tickers = t[col].str.replace(".", "-", regex=False).tolist()
                    return [
                        str(x).strip().upper()
                        for x in tickers
                        if isinstance(x, str) and x.strip()
                    ]
        except Exception:
            # 2. Secours automatique via Regex (ne requiert pas lxml)
            fallback = _extract_tickers_regex(response.text)
            if fallback:
                return fallback
    except Exception:
        pass

    # 3. Secours ultime silencieux
    return default_nasdaq


# ==============================================================================
# Interface Utilisateur uniquement structurée en Onglets
# ==============================================================================


def main():
    st.set_page_config(
        page_title="Sélecteur d'Indices", page_icon="📈", layout="wide"
    )

    st.title("📈 Analyse et Sélection d'Indices")

    # Chargement silencieux en arrière-plan
    sp500_list = get_sp500_tickers()
    nasdaq_list = get_nasdaq100_tickers()
    combined_list = sorted(list(set(sp500_list + nasdaq_list)))

    # Organisation exclusive par onglets
    tab_sp, tab_nasdaq, tab_combined = st.tabs(
        ["🏛️ S&P 500", "⚡ NASDAQ-100", "🔄 S&P 500 + NASDAQ-100"]
    )

    # Onglet 1 : S&P 500
    with tab_sp:
        st.subheader("Indice S&P 500")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("Total symboles S&P 500", len(sp500_list))
            selected_sp = st.multiselect(
                "Filtrer les actions S&P 500 :",
                options=sp500_list,
                default=sp500_list[:10],
                key="select_sp",
            )
        with col2:
            st.dataframe(
                pd.DataFrame(selected_sp, columns=["Ticker"]),
                use_container_width=True,
                hide_index=True,
            )

    # Onglet 2 : NASDAQ-100
    with tab_nasdaq:
        st.subheader("Indice NASDAQ-100")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("Total symboles NASDAQ-100", len(nasdaq_list))
            selected_nasdaq = st.multiselect(
                "Filtrer les actions NASDAQ-100 :",
                options=nasdaq_list,
                default=nasdaq_list[:10],
                key="select_nasdaq",
            )
        with col2:
            st.dataframe(
                pd.DataFrame(selected_nasdaq, columns=["Ticker"]),
                use_container_width=True,
                hide_index=True,
            )

    # Onglet 3 : Combiné
    with tab_combined:
        st.subheader("Union des deux indices (sans doublons)")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("Total symboles uniques", len(combined_list))
            selected_combined = st.multiselect(
                "Filtrer les actions combinées :",
                options=combined_list,
                default=combined_list[:10],
                key="select_combined",
            )
        with col2:
            st.dataframe(
                pd.DataFrame(selected_combined, columns=["Ticker"]),
                use_container_width=True,
                hide_index=True,
            )


if __name__ == "__main__":
    main()
