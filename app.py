from html.parser import HTMLParser
import io
import re
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

# ==============================================================================
# Parser HTML natif (ne nécessite PAS lxml ni bs4)
# ==============================================================================


class WikipediaTableParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.tables = []
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._current_cell = ""
        self._current_row = []
        self._current_table = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            attr_dict = dict(attrs)
            if "wikitable" in attr_dict.get("class", ""):
                self._in_table = True
                self._current_table = []
        elif self._in_table and tag == "tr":
            self._in_row = True
            self._current_row = []
        elif self._in_row and tag in ("td", "th"):
            self._in_cell = True
            self._current_cell = ""

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_cell:
            self._in_cell = False
            self._current_row.append(self._current_cell.strip())
        elif tag == "tr" and self._in_row:
            self._in_row = False
            if self._current_row:
                self._current_table.append(self._current_row)
        elif tag == "table" and self._in_table:
            self._in_table = False
            if self._current_table:
                self.tables.append(self._current_table)

    def handle_data(self, data):
        if self._in_cell:
            self._current_cell += data


# ==============================================================================
# Fonctions de récupération des Tickers sans lxml
# ==============================================================================


@st.cache_data(ttl=43200)
def get_sp500_tickers() -> list[str]:
    """Récupère les tickers du S&P 500 sans dépendre de lxml."""
    fallback_sp500 = [
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
    ]
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {"User-Agent": "Mozilla/5.0"}
        req = requests.get(url, headers=headers, timeout=10)
        parser = WikipediaTableParser()
        parser.feed(req.text)

        if parser.tables:
            table = parser.tables[0]
            tickers = []
            for row in table[1:]:
                if row:
                    symbol = row[0].replace(".", "-").strip()
                    if re.match(r"^[A-Z0-9\-]+$", symbol):
                        tickers.append(symbol)
            if tickers:
                return tickers
    except Exception:
        pass
    return fallback_sp500


@st.cache_data(ttl=43200)
def get_nasdaq100_tickers() -> list[str]:
    """Récupère les tickers du NASDAQ-100 sans dépendre de lxml."""
    fallback_nasdaq = [
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
    ]
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        headers = {"User-Agent": "Mozilla/5.0"}
        req = requests.get(url, headers=headers, timeout=10)
        parser = WikipediaTableParser()
        parser.feed(req.text)

        for table in parser.tables:
            if not table:
                continue
            header = [col.lower() for col in table[0]]
            if "ticker" in header or "symbol" in header:
                idx = (
                    header.index("ticker")
                    if "ticker" in header
                    else header.index("symbol")
                )
                tickers = []
                for row in table[1:]:
                    if len(row) > idx:
                        symbol = row[idx].replace(".", "-").strip()
                        if symbol and len(symbol) <= 6:
                            tickers.append(symbol)
                if len(tickers) > 50:
                    return tickers
    except Exception:
        pass
    return fallback_nasdaq


# ==============================================================================
# Calcul de la Market Breadth (Largeur du Marché)
# ==============================================================================


@st.cache_data(ttl=3600)
def calculate_market_breadth(tickers: list[str]) -> pd.DataFrame:
    """Télécharge les données récentes et calcule la largeur de marché (% au-dessus des MM)."""
    # Échantillon pour un rendu rapide ou analyse complète
    data = yf.download(
        tickers, period="1y", interval="1d", progress=False, threads=True
    )["Close"]

    if data.empty:
        return pd.DataFrame()

    latest_prices = data.iloc[-1]
    sma_50 = data.rolling(window=50).mean().iloc[-1]
    sma_200 = data.rolling(window=200).mean().iloc[-1]

    above_50 = (latest_prices > sma_50).sum() / len(latest_prices) * 100
    above_200 = (latest_prices > sma_200).sum() / len(latest_prices) * 100

    daily_change = data.pct_change().iloc[-1]
    advancing = (daily_change > 0).sum()
    declining = (daily_change < 0).sum()

    breadth_summary = pd.DataFrame(
        {
            "Métrique de Largeur (Market Breadth)": [
                "Nombre total d'actions analysées",
                "Hausse du jour (Advancing)",
                "Baisse du jour (Declining)",
                "Ratio Avance / Déclin",
                "% Actions > Moyenne Mobile 50 jours",
                "% Actions > Moyenne Mobile 200 jours",
            ],
            "Valeur": [
                len(tickers),
                advancing,
                declining,
                round(advancing / max(declining, 1), 2),
                f"{round(above_50, 1)}%",
                f"{round(above_200, 1)}%",
            ],
        }
    )

    return breadth_summary


# ==============================================================================
# Interface Utilisateur Streamlit avec Onglets (st.tabs)
# ==============================================================================


def main():
    st.set_page_config(
        page_title="Analyse de la Market Breadth", page_icon="📊", layout="wide"
    )

    st.title("📊 Largeur de Marché (Market Breadth) & Indices")

    # Chargement fluide des données en arrière-plan
    sp500_list = get_sp500_tickers()
    nasdaq_list = get_nasdaq100_tickers()
    combined_list = sorted(list(set(sp500_list + nasdaq_list)))

    # Structure par onglets
    tab1, tab2, tab3 = st.tabs(
        [
            "🏛️ Market Breadth S&P 500",
            "⚡ Market Breadth NASDAQ-100",
            "📊 Comparatif & Titres",
        ]
    )

    # Onglet 1 : S&P 500
    with tab1:
        st.subheader("Largeur de marché du S&P 500")
        if st.button("Calculer la Breadth S&P 500", key="btn_sp"):
            with st.spinner("Analyse des composants S&P 500..."):
                df_breadth_sp = calculate_market_breadth(sp500_list)
                st.table(df_breadth_sp)
        else:
            st.info(
                "Cliquez sur le bouton ci-dessus pour lancer l'analyse de largeur du S&P 500."
            )

    # Onglet 2 : NASDAQ-100
    with tab2:
        st.subheader("Largeur de marché du NASDAQ-100")
        if st.button("Calculer la Breadth NASDAQ-100", key="btn_nasdaq"):
            with st.spinner("Analyse des composants NASDAQ-100..."):
                df_breadth_nasdaq = calculate_market_breadth(nasdaq_list)
                st.table(df_breadth_nasdaq)
        else:
            st.info(
                "Cliquez sur le bouton ci-dessus pour lancer l'analyse de largeur du NASDAQ-100."
            )

    # Onglet 3 : Listes & Filtrage
    with tab3:
        st.subheader("Listes des composants d'indices")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total S&P 500", len(sp500_list))
            st.multiselect(
                "Aperçu Tickers S&P 500 :",
                sp500_list,
                default=sp500_list[:10],
                key="ms_sp",
            )
        with col2:
            st.metric("Total NASDAQ-100", len(nasdaq_list))
            st.multiselect(
                "Aperçu Tickers NASDAQ-100 :",
                nasdaq_list,
                default=nasdaq_list[:10],
                key="ms_nasdaq",
            )


if __name__ == "__main__":
    main()
