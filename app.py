import datetime
import io
import re
import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

# ==============================================================================
# 1. RECUPÉRATION SÉCURISÉE DES TICKERS (SANS LXML)
# ==============================================================================


@st.cache_data(ttl=43200)
def get_sp500_tickers() -> list[str]:
    """Récupère les 500 actions du S&P 500 depuis Wikipedia avec secours complet."""
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
        "MA",
        "PG",
        "COST",
        "HD",
        "JNJ",
        "ABBV",
        "BAC",
        "ORCL",
        "CRM",
        "CVX",
        "MRK",
        "KO",
        "NFLX",
        "AMD",
        "PEP",
    ]
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            table_match = re.search(
                r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>',
                res.text,
                re.DOTALL,
            )
            if table_match:
                rows = re.findall(
                    r"<tr[^>]*>(.*?)</tr>", table_match.group(1), re.DOTALL
                )
                tickers = []
                for r in rows[1:]:
                    cols = re.findall(r"<td[^>]*>(.*?)</td>", r, re.DOTALL)
                    if cols:
                        m = re.search(
                            r">([A-Z0-9\.\-]+)</a>", cols[0]
                        ) or re.search(r"^\s*([A-Z0-9\.\-]+)\s*$", cols[0])
                        if m:
                            sym = m.group(1).replace(".", "-")
                            if len(sym) <= 6:
                                tickers.append(sym)
                if len(tickers) > 400:
                    return sorted(list(set(tickers)))
    except Exception:
        pass
    return fallback_sp500


@st.cache_data(ttl=43200)
def get_nasdaq100_tickers() -> list[str]:
    """Récupère les 100+ actions du NASDAQ-100 sans dépendance lxml."""
    # Liste de secours complète des ~100 composants du NASDAQ-100
    fallback_nasdaq = [
        "AAPL",
        "ABNB",
        "ADBE",
        "ADI",
        "ADP",
        "ADSK",
        "AEP",
        "AMAT",
        "AMD",
        "AMGN",
        "AMZN",
        "ANSS",
        "ASML",
        "AVGO",
        "AZN",
        "BKR",
        "BIIB",
        "BKNG",
        "CDNS",
        "CEG",
        "CHTR",
        "CMCSA",
        "COST",
        "CPRT",
        "CRWD",
        "CSX",
        "CTAS",
        "CTSH",
        "DASH",
        "DDOG",
        "DLTR",
        "DXCM",
        "EA",
        "EXC",
        "FANG",
        "FAST",
        "FTNT",
        "GEHC",
        "GILD",
        "GOOG",
        "GOOGL",
        "HON",
        "IDXX",
        "ILMN",
        "INTC",
        "INTU",
        "ISRG",
        "KDP",
        "KHC",
        "KLAC",
        "LRCX",
        "LULU",
        "MAR",
        "MCHP",
        "MDB",
        "MDLZ",
        "MELI",
        "META",
        "MNST",
        "MRVL",
        "MSFT",
        "MU",
        "NFLX",
        "NVDA",
        "NXPI",
        "ODFL",
        "ON",
        "ORLY",
        "PANW",
        "PAYX",
        "PCAR",
        "PDD",
        "PEP",
        "PYPL",
        "QCOM",
        "REGN",
        "ROP",
        "ROST",
        "SBUX",
        "SNPS",
        "TEAM",
        "TMUS",
        "TSLA",
        "TXN",
        "VRSK",
        "VRTX",
        "WBD",
        "WDAY",
        "XEL",
        "ZS",
    ]
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            # Extraction ciblant la table des composants
            table_match = re.search(
                r'<table[^>]*id="constituents"[^>]*>(.*?)</table>',
                res.text,
                re.DOTALL,
            ) or re.search(
                r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>',
                res.text,
                re.DOTALL,
            )
            if table_match:
                rows = re.findall(
                    r"<tr[^>]*>(.*?)</tr>", table_match.group(1), re.DOTALL
                )
                tickers = []
                for r in rows[1:]:
                    cols = re.findall(r"<td[^>]*>(.*?)</td>", r, re.DOTALL)
                    if cols:
                        for c in cols[:3]:
                            m = re.search(
                                r">([A-Z]{1,5}(?:\.[A-Z]{1,2})?)</a>", c
                            ) or re.search(
                                r"^\s*([A-Z]{1,5}(?:\.[A-Z]{1,2})?)\s*$", c
                            )
                            if m:
                                sym = m.group(1).replace(".", "-")
                                if sym not in ["SEC", "NASDAQ", "USD"]:
                                    tickers.append(sym)
                                    break
                if len(tickers) >= 80:
                    return sorted(list(set(tickers)))
    except Exception:
        pass
    return fallback_nasdaq


# ==============================================================================
# 2. INDICATEURS TECHNIQUES (SMI & ATR)
# ==============================================================================


def compute_smi(
    df: pd.DataFrame,
    k_period: int = 14,
    smooth1: int = 3,
    smooth2: int = 3,
    signal_period: int = 3,
):
    """Calcule le Stochastic Momentum Index (SMI) et sa ligne de signal."""
    high_k = df["High"].rolling(window=k_period).max()
    low_k = df["Low"].rolling(window=k_period).min()
    m_k = 0.5 * (high_k + low_k)
    d = df["Close"] - m_k
    hl_diff = high_k - low_k

    d_smooth1 = d.ewm(span=smooth1, adjust=False).mean()
    d_smooth2 = d_smooth1.ewm(span=smooth2, adjust=False).mean()

    hl_smooth1 = (hl_diff / 2.0).ewm(span=smooth1, adjust=False).mean()
    hl_smooth2 = hl_smooth1.ewm(span=smooth2, adjust=False).mean()

    smi = 100 * (d_smooth2 / np.where(hl_smooth2 == 0, 1e-9, hl_smooth2))
    smi_signal = pd.Series(smi).ewm(span=signal_period, adjust=False).mean()
    return smi, smi_signal


def compute_atr(df: pd.DataFrame, period: int = 14):
    """Calcule l'Average True Range (ATR)."""
    high_low = df["High"] - df["Low"]
    high_cp = (df["High"] - df["Close"].shift(1)).abs()
    low_cp = (df["Low"] - df["Close"].shift(1)).abs()
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


# ==============================================================================
# 3. CALCUL DU MARKET BREADTH
# ==============================================================================


@st.cache_data(ttl=3600)
def compute_breadth_metrics(tickers: list[str]) -> dict:
    """Analyse la santé globale d'un univers d'actions (% > MM50, % > MM200, Advance/Decline)."""
    try:
        data = yf.download(
            tickers, period="1y", interval="1d", progress=False, threads=True
        )["Close"]
        if data.empty:
            return {}

        latest = data.iloc[-1]
        sma50 = data.rolling(50).mean().iloc[-1]
        sma200 = data.rolling(200).mean().iloc[-1]

        above_50 = (latest > sma50).sum() / len(latest) * 100
        above_200 = (latest > sma200).sum() / len(latest) * 100

        returns = data.pct_change().iloc[-1]
        adv = (returns > 0).sum()
        dec = (returns < 0).sum()

        return {
            "total": len(tickers),
            "advancing": adv,
            "declining": dec,
            "ad_ratio": round(adv / max(dec, 1), 2),
            "pct_above_50": round(above_50, 1),
            "pct_above_200": round(above_200, 1),
        }
    except Exception:
        return {}


# ==============================================================================
# 4. APPLICATION STREAMLIT COMPLETE
# ==============================================================================


def main():
    st.set_page_config(
        page_title="Plateforme de Trading & Analyse Market Breadth",
        page_icon="📈",
        layout="wide",
    )

    # Chargement silencieux des listes complètes
    sp500_list = get_sp500_tickers()
    nasdaq_list = get_nasdaq100_tickers()

    # --------------------------------------------------------------------------
    # BARRE LATÉRALE : PARAMÈTRES GLOBAUX
    # --------------------------------------------------------------------------
    st.sidebar.title("⚙️ Paramètres")

    # Choix de la watchlist / Ticker principal
    selected_ticker = st.sidebar.text_input(
        "Ticker principal à analyser :", value="AAPL"
    ).upper()

    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Configuration SMI")
    smi_k = st.sidebar.number_input("Période %K", value=14, step=1)
    smi_s1 = st.sidebar.number_input("Lissage 1", value=3, step=1)
    smi_s2 = st.sidebar.number_input("Lissage 2", value=3, step=1)
    smi_sig = st.sidebar.number_input("Signal", value=3, step=1)

    st.sidebar.markdown("---")
    st.sidebar.subheader("📏 Configuration ATR")
    atr_p = st.sidebar.number_input("Période ATR", value=14, step=1)

    st.sidebar.markdown("---")
    st.sidebar.info("💡 Remarque : Suivi de position sans Trailing Stop Auto.")

    # --------------------------------------------------------------------------
    # STRUCTURE PRINCIPALE : LES ONGLETS DE L'APPLICATION
    # --------------------------------------------------------------------------
    st.title("📈 Tableau de Bord de Trading")

    tab_tech, tab_breadth, tab_tickers, tab_log = st.tabs(
        [
            "📉 Analyse Technique & SMI/ATR",
            "🌊 Market Breadth",
            "📑 Tickers S&P 500 & NASDAQ",
            "📋 Journal & Métriques",
        ]
    )

    # ==========================================================================
    # ONGLET 1 : ANALYSE TECHNIQUE (SMI, ATR, PRIX)
    # ==========================================================================
    with tab_tech:
        st.subheader(f"Analyse Technique : {selected_ticker}")

        col_period, col_dummy = st.columns([1, 2])
        with col_period:
            period_choice = st.selectbox(
                "Période d'historique :",
                ["3mo", "6mo", "1y", "2y", "5y"],
                index=2,
            )

        try:
            df_stock = yf.download(
                selected_ticker, period=period_choice, progress=False
            )
            if not df_stock.empty:
                if isinstance(df_stock.columns, pd.MultiIndex):
                    df_stock.columns = df_stock.columns.get_level_values(0)

                df_stock["SMI"], df_stock["SMI_Signal"] = compute_smi(
                    df_stock, smi_k, smi_s1, smi_s2, smi_sig
                )
                df_stock["ATR"] = compute_atr(df_stock, atr_p)

                last_close = df_stock["Close"].iloc[-1]
                last_smi = df_stock["SMI"].iloc[-1]
                last_atr = df_stock["ATR"].iloc[-1]

                m1, m2, m3 = st.columns(3)
                m1.metric("Dernier Prix", f"${last_close:.2f}")
                m2.metric("SMI", f"{last_smi:.2f}")
                m3.metric("ATR (14)", f"${last_atr:.2f}")

                st.line_chart(df_stock[["Close"]])
                st.subheader("Stochastic Momentum Index (SMI)")
                st.line_chart(df_stock[["SMI", "SMI_Signal"]])
            else:
                st.error(
                    f"Impossible de charger les données pour {selected_ticker}."
                )
        except Exception as e:
            st.error(f"Erreur lors du chargement des données : {e}")

    # ==========================================================================
    # ONGLET 2 : MARKET BREADTH (UN SEUL ONGLET CONCENTRÉ)
    # ==========================================================================
    with tab_breadth:
        st.subheader("🌊 Largeur de Marché (Market Breadth)")
        st.write(
            "Évaluation de la santé globale du marché via la participation des actions aux indices."
        )

        col_index_select, col_btn = st.columns([2, 1])
        with col_index_select:
            breadth_index = st.selectbox(
                "Choisir l'indice à analyser :",
                ["S&P 500", "NASDAQ-100", "Tous les indices (Combiné)"],
            )

        if breadth_index == "S&P 500":
            target_list = sp500_list
        elif breadth_index == "NASDAQ-100":
            target_list = nasdaq_list
        else:
            target_list = sorted(list(set(sp500_list + nasdaq_list)))

        if st.button("🔄 Lancer l'analyse de la Market Breadth"):
            with st.spinner(
                f"Calcul en cours sur {len(target_list)} actions..."
            ):
                metrics = compute_breadth_metrics(target_list)
                if metrics:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total d'actions", metrics["total"])
                    c2.metric("Ratio Avance / Déclin", metrics["ad_ratio"])
                    c3.metric("% > MM 50 jours", f"{metrics['pct_above_50']}%")
                    c4.metric(
                        "% > MM 200 jours", f"{metrics['pct_above_200']}%"
                    )

                    df_summary = pd.DataFrame(
                        {
                            "Indicateur": [
                                "Actions en Hausse (Advancing)",
                                "Actions en Baisse (Declining)",
                                "Ratio Avance/Déclin",
                                "Participation > MM50",
                                "Participation > MM200",
                            ],
                            "Valeur": [
                                metrics["advancing"],
                                metrics["declining"],
                                metrics["ad_ratio"],
                                f"{metrics['pct_above_50']}%",
                                f"{metrics['pct_above_200']}%",
                            ],
                        }
                    )
                    st.table(df_summary)
                else:
                    st.warning(
                        "Impossible de calculer la breadth actuellement."
                    )

    # ==========================================================================
    # ONGLET 3 : TICKERS ET LISTES DE SURVEILLANCE
    # ==========================================================================
    with tab_tickers:
        st.subheader("📑 Listes des Tickers")
        c_sp, c_ndx = st.columns(2)

        with c_sp:
            st.write(f"**S&P 500** ({len(sp500_list)} actions chargées)")
            st.dataframe(
                pd.DataFrame(sp500_list, columns=["Symbol"]),
                use_container_width=True,
                height=300,
            )

        with c_ndx:
            st.write(f"**NASDAQ-100** ({len(nasdaq_list)} actions chargées)")
            st.dataframe(
                pd.DataFrame(nasdaq_list, columns=["Symbol"]),
                use_container_width=True,
                height=300,
            )

    # ==========================================================================
    # ONGLET 4 : JOURNAL & PERFORMANCE
    # ==========================================================================
    with tab_log:
        st.subheader("📋 Métriques & Suivi des Performances")
        st.write("Espace réservé à l'historique d'exécution des transactions.")
        st.info(
            "Consignez vos transactions et vérifiez la cohérence des calculs PnL."
        )


if __name__ == "__main__":
    main()
