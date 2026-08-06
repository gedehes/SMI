import io
import pandas as pd
import requests
import streamlit as st

# ==============================================================================
# Fonctions d'extraction des tickers
# ==============================================================================


@st.cache_data(ttl=43200)  # Mise en cache pour 12 heures
def get_sp500_tickers() -> list[str]:
    """Récupère la liste des symboles du S&P 500 depuis Wikipedia avec fallback."""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # io.StringIO résout la dépréciation et les incompatibilités de lecture directe de chaîne HTML
        tables = pd.read_html(io.StringIO(response.text))
        df = tables[0]

        # Traitement des symboles (conversion du point '.' en tiret '-' pour compatibilité yfinance)
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        return [
            str(t).strip().upper()
            for t in tickers
            if isinstance(t, str) and t.strip()
        ]

    except Exception as e:
        st.warning(
            f"Impossible de récupérer dynamiquement le S&P 500 ({e}). Chargement de la liste de secours."
        )
        return [
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


@st.cache_data(ttl=43200)  # Mise en cache pour 12 heures
def get_nasdaq100_tickers() -> list[str]:
    """Récupère la liste des symboles du NASDAQ-100 depuis Wikipedia avec fallback."""
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        tables = pd.read_html(io.StringIO(response.text))

        # Recherche de la table contenant la colonne Ticker ou Symbol
        for t in tables:
            target_col = None
            if "Ticker" in t.columns:
                target_col = "Ticker"
            elif "Symbol" in t.columns:
                target_col = "Symbol"

            if target_col:
                tickers = (
                    t[target_col].str.replace(".", "-", regex=False).tolist()
                )
                return [
                    str(x).strip().upper()
                    for x in tickers
                    if isinstance(x, str) and x.strip()
                ]

        raise ValueError(
            "Aucune colonne 'Ticker' ou 'Symbol' identifiée dans le tableau."
        )

    except Exception as e:
        st.warning(
            f"Impossible de récupérer dynamiquement le NASDAQ-100 ({e}). Chargement de la liste de secours."
        )
        return [
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


# ==============================================================================
# Application Streamlit
# ==============================================================================


def main():
    st.set_page_config(
        page_title="Sélecteur de Tickers d'Indices",
        page_icon="📈",
        layout="wide",
    )

    st.title("📈 Extraction dynamique des Tickers (S&P 500 & NASDAQ-100)")
    st.write(
        "Ce script extrait les listes à jour d'actions via Wikipédia et bascule sur une liste de secours en cas d'erreur."
    )

    # Sidebar - Options de sélection
    st.sidebar.header("Configuration")
    index_choice = st.sidebar.radio(
        "Sélectionner un indice :",
        ["S&P 500", "NASDAQ-100", "Union des deux (S&P 500 + NASDAQ-100)"],
    )

    # Chargement selon le choix
    if index_choice == "S&P 500":
        tickers = get_sp500_tickers()
    elif index_choice == "NASDAQ-100":
        tickers = get_nasdaq100_tickers()
    else:
        sp_list = get_sp500_tickers()
        nasdaq_list = get_nasdaq100_tickers()
        tickers = sorted(list(set(sp_list + nasdaq_list)))

    # Métriques et affichage
    col1, col2 = st.columns([1, 2])

    with col1:
        st.metric(label="Nombre de symboles chargés", value=len(tickers))

        selected_tickers = st.multiselect(
            "Filtrer / Sélectionner des symboles :",
            options=tickers,
            default=tickers[:10],
        )

    with col2:
        st.subheader("Aperçu des symboles")
        df_tickers = pd.DataFrame(selected_tickers, columns=["Ticker Symbol"])
        st.dataframe(df_tickers, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
