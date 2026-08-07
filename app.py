from io import StringIO
import os
import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

# Configuration de la page
st.set_page_config(page_title="Scanner SMI & Breakout", layout="wide")

FILENAME = "mes_tickers.txt"

# En-tête HTTP pour imiter un navigateur web et éviter le blocage 403
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# --- RÉCUPÉRATION AUTOMATIQUE DES TICKERS (SLICKCHARTS -> STOCKANALYSIS -> WIKIPÉDIA -> FALLBACK) ---
@st.cache_data(ttl=86400)
def obtenir_sp500_tickers():
  """Récupère les ~500 actions du S&P 500 depuis Slickcharts, StockAnalysis, Wikipédia ou liste fixe."""
  # 1. Tentative sur Slickcharts
  try:
    url = "https://www.slickcharts.com/sp500"
    response = requests.get(url, headers=HEADERS, timeout=10)
    if response.status_code == 200:
      df = pd.read_html(StringIO(response.text))[0]
      if "Symbol" in df.columns:
        tickers = (
            df["Symbol"]
            .astype(str)
            .str.strip()
            .str.replace(".", "-", regex=False)
            .tolist()
        )
        if len(tickers) >= 400:
          return tickers
  except Exception:
    pass

  # 2. Secours sur StockAnalysis
  try:
    url = "https://stockanalysis.com/list/sp-500-stocks/"
    response = requests.get(url, headers=HEADERS, timeout=10)
    if response.status_code == 200:
      df = pd.read_html(StringIO(response.text))[0]
      col = (
          "Symbol"
          if "Symbol" in df.columns
          else "Ticker" if "Ticker" in df.columns else None
      )
      if col:
        tickers = (
            df[col]
            .astype(str)
            .str.strip()
            .str.replace(".", "-", regex=False)
            .tolist()
        )
        if len(tickers) >= 400:
          return tickers
  except Exception:
    pass

  # 3. Secours sur Wikipédia
  try:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    response = requests.get(url, headers=HEADERS, timeout=10)
    if response.status_code == 200:
      df = pd.read_html(StringIO(response.text))[0]
      tickers = (
          df["Symbol"]
          .astype(str)
          .str.strip()
          .str.replace(".", "-", regex=False)
          .tolist()
      )
      if len(tickers) >= 400:
        return tickers
  except Exception:
    pass

  # 4. Liste fixe de sécurité
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
      "UNH",
      "V",
      "XOM",
      "MA",
      "PG",
      "COST",
      "JNJ",
      "HD",
      "ABBV",
      "MRK",
      "NFLX",
      "AMD",
      "CRM",
      "KO",
      "PEP",
      "ORCL",
      "BAC",
      "WMT",
      "CVX",
      "ADBE",
      "MCD",
      "CSCO",
      "WFC",
      "DIS",
      "ACN",
      "ABT",
      "PM",
      "INTU",
      "IBM",
      "GE",
      "TXN",
      "AMAT",
      "QCOM",
      "DHR",
      "CAT",
      "AMGN",
      "NEE",
      "UNP",
      "LOW",
      "GS",
      "HON",
      "COP",
      "BA",
      "BKNG",
  ]


@st.cache_data(ttl=86400)
def obtenir_nasdaq100_tickers():
  """Récupère les ~100 actions du NASDAQ 100 depuis Slickcharts, StockAnalysis, Wikipédia ou liste fixe."""
  # 1. Tentative sur Slickcharts
  try:
    url = "https://www.slickcharts.com/nasdaq100"
    response = requests.get(url, headers=HEADERS, timeout=10)
    if response.status_code == 200:
      df = pd.read_html(StringIO(response.text))[0]
      if "Symbol" in df.columns:
        tickers = (
            df["Symbol"]
            .astype(str)
            .str.strip()
            .str.replace(".", "-", regex=False)
            .tolist()
        )
        if len(tickers) >= 80:
          return tickers
  except Exception:
    pass

  # 2. Secours sur StockAnalysis
  try:
    url = "https://stockanalysis.com/list/nasdaq-100-stocks/"
    response = requests.get(url, headers=HEADERS, timeout=10)
    if response.status_code == 200:
      df = pd.read_html(StringIO(response.text))[0]
      col = (
          "Symbol"
          if "Symbol" in df.columns
          else "Ticker" if "Ticker" in df.columns else None
      )
      if col:
        tickers = (
            df[col]
            .astype(str)
            .str.strip()
            .str.replace(".", "-", regex=False)
            .tolist()
        )
        if len(tickers) >= 80:
          return tickers
  except Exception:
    pass

  # 3. Secours sur Wikipédia
  try:
    url = "https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies"
    response = requests.get(url, headers=HEADERS, timeout=10)
    if response.status_code == 200:
      tables = pd.read_html(StringIO(response.text))
      for df in tables:
        col = (
            "Ticker"
            if "Ticker" in df.columns
            else "Symbol" if "Symbol" in df.columns else None
        )
        if col:
          tickers = (
              df[col]
              .astype(str)
              .str.strip()
              .str.replace(".", "-", regex=False)
              .tolist()
          )
          if len(tickers) >= 80:
            return tickers
  except Exception:
    pass

  # 4. Liste fixe de sécurité
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
      "PEP",
      "TMUS",
      "ADBE",
      "CSCO",
      "INTU",
      "AMAT",
      "QCOM",
      "TXN",
      "HON",
      "CMCSA",
      "AMGN",
      "BKNG",
      "ISRG",
      "VRTX",
      "PANW",
      "ADP",
      "REGN",
      "LRCX",
      "MDLZ",
  ]


def charger_tickers():
  if os.path.exists(FILENAME):
    with open(FILENAME, "r") as f:
      return [line.strip().upper() for line in f if line.strip()]
  return ["AAPL", "MSFT", "GOOG", "MU"]


def sauvegarder_tickers(liste_str):
  tickers = [t.strip().upper() for t in liste_str.split() if t.strip()]
  with open(FILENAME, "w") as f:
    for ticker in sorted(list(set(tickers))):
      f.write(f"{ticker}\n")
  return tickers


def aplatir_donnees(df):
  if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
  return df


# --- CALCUL DU SMI & VOLUME (ONGLETS 1 & 4) ---
def calculer_smi_watchlist(ticker_list):
  results = []
  for ticker in ticker_list:
    try:
      df = yf.download(ticker, period="3y", interval="1wk", progress=False)
      if df.empty:
        continue
      df = aplatir_donnees(df)
      if not all(
          col in df.columns for col in ["High", "Low", "Close", "Volume"]
      ):
        continue
      if len(df) < 30:
        continue

      période = 14
      df["LL"] = df["Low"].rolling(window=période).min()
      df["HH"] = df["High"].rolling(window=période).max()
      df["HL_Center"] = (df["HH"] + df["LL"]) / 2

      df["D"] = df["Close"] - df["HL_Center"]
      df["HL_Range"] = df["HH"] - df["LL"]

      df["D_Smooth1"] = df["D"].ewm(span=4, adjust=False).mean()
      df["D_Smooth2"] = df["D_Smooth1"].ewm(span=1, adjust=False).mean()

      df["Range_Smooth1"] = df["HL_Range"].ewm(span=4, adjust=False).mean()
      df["Range_Smooth2"] = (
          df["Range_Smooth1"].ewm(span=1, adjust=False).mean()
      )
      df["Range_Smooth2"] = df["Range_Smooth2"].apply(
          lambda x: x if x != 0 else 0.00001
      )

      df["SMI_K"] = 100 * (df["D_Smooth2"] / (0.5 * df["Range_Smooth2"]))
      df["SMI_D"] = df["SMI_K"].ewm(span=14, adjust=False).mean()
      df["Diff"] = df["SMI_K"] - df["SMI_D"]

      df["Vol_MM20"] = df["Volume"].rolling(window=20).mean()

      derniere_ligne = df.iloc[-1]
      ligne_precedente = df.iloc[-2]

      cloture_actuelle = float(derniere_ligne["Close"])
      haut_actuel = float(derniere_ligne["High"])
      bas_actuel = float(derniere_ligne["Low"])

      k_actuel = float(derniere_ligne["SMI_K"])
      d_actuel = float(derniere_ligne["SMI_D"])
      diff_actuelle = float(derniere_ligne["Diff"])
      k_precedent = float(ligne_precedente["SMI_K"])

      tendance = (
          "🔼 Croissant" if k_actuel >= k_precedent else "🔽 Décroissant"
      )

      vol_actuel = float(derniere_ligne["Volume"])
      vol_mm20 = float(derniere_ligne["Vol_MM20"])
      vol_status = "Supérieur" if vol_actuel > vol_mm20 else "Inférieur"

      results.append({
          "ACTIF": ticker,
          "DIFFÉRENCE": diff_actuelle,
          "TENDANCE": tendance,
          "Volume hebdo": vol_status,
          "Volume sem.": vol_actuel,
          "MM20 Vol": vol_mm20,
          "SMI %K (k)": k_actuel,
          "SMI %D (d)": d_actuel,
          "HAUT (W)": haut_actuel,
          "BAS (W)": bas_actuel,
          "CLÔTURE": cloture_actuelle,
      })
    except Exception as e:
      st.error(f"Erreur sur le ticker {ticker} : {str(e)}")
      continue
  return pd.DataFrame(results)


# --- CALCUL DES NIVEAUX D'ENTRÉE (DONCHIAN 20W - ONGLET 2) ---
def calculer_ordres_entree(ticker_list):
  results = []
  for ticker in ticker_list:
    try:
      df = yf.download(ticker, period="2y", interval="1wk", progress=False)
      if df.empty:
        continue
      df = aplatir_donnees(df)
      if "High" not in df.columns or len(df) < 20:
        continue

      prix_max_donchian_20w = float(
          df["High"].rolling(window=20).max().iloc[-1]
      )
      buy_stop = prix_max_donchian_20w * 1.005
      limite = buy_stop * 1.01

      results.append({
          "ACTIF": ticker,
          "Prix Max Donchian 20W": prix_max_donchian_20w,
          "Buy stop": buy_stop,
          "Limite": limite,
      })
    except Exception as e:
      st.error(f"Erreur sur le ticker {ticker} (Onglet Entrée) : {str(e)}")
      continue
  return pd.DataFrame(results)


# --- CALCUL DU MARKET BREADTH COMPLET & HISTORIQUE A/D LINE (ONGLET 3) ---
def calculer_market_breadth(ticker_list, index_name):
  try:
    data = yf.download(ticker_list, period="1y", interval="1d", progress=False)
    if data.empty:
      return None, None

    if isinstance(data.columns, pd.MultiIndex):
      close_data = data["Close"].dropna(how="all", axis=1)
      high_data = data["High"].dropna(how="all", axis=1)
      low_data = data["Low"].dropna(how="all", axis=1)
    else:
      close_data = data[["Close"]].dropna(how="all", axis=1)
      high_data = data[["High"]].dropna(how="all", axis=1)
      low_data = data[["Low"]].dropna(how="all", axis=1)

    # 1. MM200 Daily
    mm200 = close_data.rolling(window=200).mean()
    au_dessus_200 = close_data.iloc[-1] > mm200.iloc[-1]
    tot_200 = au_dessus_200.dropna().count()
    pct_mm200 = (au_dessus_200.sum() / tot_200 * 100) if tot_200 > 0 else 0
    etat_mm200 = "✅ Sain" if pct_mm200 >= 60 else "🚨 Fragile"

    # 2. MM50 Daily (Score + Tendance)
    mm50 = close_data.rolling(window=50).mean()

    au_dessus_50_today = close_data.iloc[-1] > mm50.iloc[-1]
    tot_50_today = au_dessus_50_today.dropna().count()
    pct_mm50_today = (
        (au_dessus_50_today.sum() / tot_50_today * 100) if tot_50_today > 0 else 0
    )

    au_dessus_50_prev = close_data.iloc[-2] > mm50.iloc[-2]
    tot_50_prev = au_dessus_50_prev.dropna().count()
    pct_mm50_prev = (
        (au_dessus_50_prev.sum() / tot_50_prev * 100) if tot_50_prev > 0 else 0
    )

    mm50_croissant = pct_mm50_today > pct_mm50_prev
    etat_mm50 = (
        "✅ Vert" if (pct_mm50_today > 50 and mm50_croissant) else "🚨 Rouge"
    )

    # 3. Avance / Baisse & Ligne Avance-Baisse Cumulée
    daily_diff = close_data.diff()
    daily_advances = (daily_diff > 0).sum(axis=1)
    daily_declines = (daily_diff < 0).sum(axis=1)
    daily_net = daily_advances - daily_declines

    # Ligne Avance-Baisse cumulée sur les 60 derniers jours de trading
    ad_line_60d = daily_net.cumsum().tail(60)

    avances = int(daily_advances.iloc[-1])
    baisses = int(daily_declines.iloc[-1])
    avances_nettes = avances - baisses
    ratio_ad = avances / baisses if baisses > 0 else avances

    # 4. Plus Hauts vs Plus Bas (NH - NL 52 Semaines / 252 Jours)
    high_52w = high_data.rolling(window=252).max()
    low_52w = low_data.rolling(window=252).min()

    nh_today = int((high_data.iloc[-1] >= high_52w.iloc[-1]).sum())
    nl_today = int((low_data.iloc[-1] <= low_52w.iloc[-1]).sum())
    net_nh_nl_today = nh_today - nl_today

    nh_prev = int((high_data.iloc[-2] >= high_52w.iloc[-2]).sum())
    nl_prev = int((low_data.iloc[-2] <= low_52w.iloc[-2]).sum())
    net_nh_nl_prev = nh_prev - nl_prev

    nh_nl_croissant = net_nh_nl_today > net_nh_nl_prev
    nh_nl_positif = net_nh_nl_today > 0
    etat_nh_nl = (
        "✅ Vert" if (nh_nl_positif and nh_nl_croissant) else "🚨 Rouge"
    )

    res_dict = {
        "Indice": index_name,
        "% > MM200": pct_mm200,
        "État MM200": etat_mm200,
        "% > MM50": pct_mm50_today,
        "MM50 Tendance": (
            "🔼 Croissant" if mm50_croissant else "🔽 Décroissant"
        ),
        "État MM50": etat_mm50,
        "NH (Plus Hauts)": nh_today,
        "NL (Plus Bas)": nl_today,
        "Net (NH - NL)": net_nh_nl_today,
        "Net (NH - NL) Veille": net_nh_nl_prev,
        "NH/NL Tendance": (
            "🔼 Croissant" if nh_nl_croissant else "🔽 Décroissant"
        ),
        "État NH/NL": etat_nh_nl,
        "Avances": avances,
        "Baisses": baisses,
        "Avances Nettes": avances_nettes,
        "Ratio A/B": ratio_ad,
    }

    return res_dict, ad_line_60d

  except Exception as e:
    st.error(
        f"Erreur lors du calcul du Market Breadth ({index_name}) : {str(e)}"
    )
    return None, None


# --- CALCUL DES INDICATEURS AVANCÉS (ONGLET 5) ---
def calculer_indicateurs_techniques_avances(ticker_list):
  results = []
  for ticker in ticker_list:
    try:
      df = yf.download(ticker, period="3y", interval="1wk", progress=False)
      if df.empty:
        continue
      df = aplatir_donnees(df)
      if not all(col in df.columns for col in ["High", "Low", "Close"]):
        continue
      if len(df) < 40:
        continue

      cloture_actuelle = float(df["Close"].iloc[-1])

      df["High_Low"] = df["High"] - df["Low"]
      df["High_ClosePrev"] = (df["High"] - df["Close"].shift(1)).abs()
      df["Low_ClosePrev"] = (df["Low"] - df["Close"].shift(1)).abs()
      df["TR"] = df[["High_Low", "High_ClosePrev", "Low_ClosePrev"]].max(axis=1)
      df["ATR"] = df["TR"].ewm(alpha=1 / 14, adjust=False).mean()
      atr_actuel = float(df["ATR"].iloc[-1])
      ratio_th = atr_actuel / cloture_actuelle

      high_pr_val = float(
          df["High"].shift(1).rolling(window=12).max().iloc[-1]
      )
      ratio_high = cloture_actuelle / high_pr_val - 1

      df["Tenkan"] = (
          df["High"].rolling(window=9).max() + df["Low"].rolling(window=9).min()
      ) / 2
      tenkan_actuel = float(df["Tenkan"].iloc[-1])
      tenkan_pct = cloture_actuelle / tenkan_actuel - 1

      période = 14
      df["LL"] = df["Low"].rolling(window=période).min()
      df["HH"] = df["High"].rolling(window=période).max()
      df["HL_Center"] = (df["HH"] + df["LL"]) / 2
      df["D"] = df["Close"] - df["HL_Center"]
      df["HL_Range"] = df["HH"] - df["LL"]

      df["D_Smooth1"] = df["D"].ewm(span=4, adjust=False).mean()
      df["D_Smooth2"] = df["D_Smooth1"].ewm(span=1, adjust=False).mean()
      df["Range_Smooth1"] = df["HL_Range"].ewm(span=4, adjust=False).mean()
      df["Range_Smooth2"] = (
          df["Range_Smooth1"].ewm(span=1, adjust=False).mean()
      )
      df["Range_Smooth2"] = df["Range_Smooth2"].apply(
          lambda x: x if x != 0 else 0.00001
      )

      df["SMI_K"] = 100 * (df["D_Smooth2"] / (0.5 * df["Range_Smooth2"]))
      df["SMI_D"] = df["SMI_K"].ewm(span=14, adjust=False).mean()

      k_actuel = float(df["SMI_K"].iloc[-1])
      d_actuel = float(df["SMI_D"].iloc[-1])
      kd_ratio = k_actuel / d_actuel if d_actuel != 0 else np.nan
      kd_diff = k_actuel - d_actuel

      def calculer_adx_w(data, N, smoothing_N):
        plus_dm = data["High"].diff()
        minus_dm = -data["Low"].diff()
        p_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
        m_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)

        smooth_tr = data["TR"].ewm(alpha=1 / N, adjust=False).mean()
        smooth_p_dm = (
            pd.Series(p_dm, index=data.index)
            .ewm(alpha=1 / N, adjust=False)
            .mean()
        )
        smooth_m_dm = (
            pd.Series(m_dm, index=data.index)
            .ewm(alpha=1 / N, adjust=False)
            .mean()
        )

        p_di = 100 * (smooth_p_dm / smooth_tr)
        m_di = 100 * (smooth_m_dm / smooth_tr)
        dx = 100 * (p_di - m_di).abs() / (p_di + m_di)
        adx = dx.ewm(alpha=1 / smoothing_N, adjust=False).mean()
        return float(adx.iloc[-1])

      adx14_val = calculer_adx_w(df, 14, 14)
      adx7_val = calculer_adx_w(df, 7, 7)

      results.append({
          "ACTIF": ticker,
          "ATR": atr_actuel,
          "Ratio th.": ratio_th,
          "Close": cloture_actuelle,
          "High pr": high_pr_val,
          "Ratio": ratio_high,
          "Tenkan": tenkan_actuel,
          "Tenkan %": tenkan_pct,
          "%K": k_actuel,
          "%D": d_actuel,
          "K/D": kd_ratio,
          "K-D": kd_diff,
          "ADX14": adx14_val,
          "ADX7": adx7_val,
      })
    except Exception as e:
      st.error(f"Erreur sur le ticker {ticker} (Onglet Indicateurs) : {str(e)}")
      continue
  return pd.DataFrame(results)


# --- STYLISATION ET COULEURS ---
def colorier_diff(val):
  try:
    color = "#118d57" if float(val) >= 0 else "#b71d18"
    return f"color: {color}; font-weight: bold"
  except Exception:
    return ""


def colorier_tendance(val):
  color = "#118d57" if "Croissant" in str(val) else "#b71d18"
  return f"color: {color}; font-weight: bold"


def colorier_volume(val):
  color = "#118d57" if "Supérieur" in str(val) else "#b71d18"
  return f"color: {color}; font-weight: bold"


def colorier_actif_conditionnel(row):
  diff_ok = float(row["DIFFÉRENCE"]) >= 0
  tendance_ok = "Croissant" in str(row["TENDANCE"])
  volume_ok = "Supérieur" in str(row["Volume hebdo"])

  color = "#118d57" if (diff_ok and tendance_ok and volume_ok) else "#b71d18"
  style_actif = f"background-color: {color}; color: white; font-weight: bold"

  return [style_actif if col == "ACTIF" else "" for col in row.index]


def colorier_statut_vert_rouge(val):
  color = "#118d57" if "Vert" in str(val) or "Sain" in str(val) else "#b71d18"
  return f"color: {color}; font-weight: bold"


# --- INTERFACE UTILISATEUR STREAMLIT ---
st.title("📊 Scanner SMI & Breakout")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⚡ BREAKOUT MOMENTUM",
    "🎯 ENTRÉE",
    "🌐 MARKET BREADTH",
    "📋 Liste Enregistrée",
    "📈 Indicateurs Avancés",
])

# --- ONGLET 1 : BREAKOUT MOMENTUM ---
with tab1:
  st.subheader("Analyse Breakout Momentum")
  entree_flash = st.text_area(
      "Entrez des tickers à scanner (ex: TSLA NVDA AMD) :",
      value="TSLA NVDA AMD MU AAPL",
      key="txt_breakout",
  )
  liste_flash = [t.strip().upper() for t in entree_flash.split() if t.strip()]

  if st.button(
      "🚀 Lancer le Scan Breakout", key="btn_breakout", use_container_width=True
  ):
    if not liste_flash:
      st.warning("Veuillez saisir au moins un ticker.")
    else:
      with st.spinner("Analyse Breakout Momentum en cours..."):
        df_res_flash = calculer_smi_watchlist(liste_flash)
        if not df_res_flash.empty:
          df_res_flash["IS_VERT"] = (
              (df_res_flash["DIFFÉRENCE"] >= 0)
              & (df_res_flash["TENDANCE"].str.contains("Croissant"))
              & (df_res_flash["Volume hebdo"] == "Supérieur")
          )

          df_res_flash = df_res_flash.sort_values(
              by=["IS_VERT", "DIFFÉRENCE"], ascending=[False, False]
          )

          colonnes_tab1 = [
              "ACTIF",
              "DIFFÉRENCE",
              "TENDANCE",
              "Volume hebdo",
              "Volume sem.",
              "MM20 Vol",
              "SMI %K (k)",
              "SMI %D (d)",
              "HAUT (W)",
              "BAS (W)",
              "CLÔTURE",
          ]

          df_tab1 = df_res_flash[colonnes_tab1].copy()

          df_style_tab1 = (
              df_tab1.style.format({
                  "DIFFÉRENCE": "{:.2f}",
                  "SMI %K (k)": "{:.2f}",
                  "SMI %D (d)": "{:.2f}",
                  "HAUT (W)": "{:.2f}",
                  "BAS (W)": "{:.2f}",
                  "CLÔTURE": "{:.2f}",
                  "Volume sem.": "{:,.0f}",
                  "MM20 Vol": "{:,.0f}",
              })
              .apply(colorier_actif_conditionnel, axis=1)
              .map(colorier_diff, subset=["DIFFÉRENCE"])
              .map(colorier_tendance, subset=["TENDANCE"])
              .map(colorier_volume, subset=["Volume hebdo"])
          )
          st.dataframe(
              df_style_tab1, use_container_width=True, hide_index=True
          )
        else:
          st.warning("Impossible de générer l'analyse.")

# --- ONGLET 2 : ENTRÉE ---
with tab2:
  st.subheader("Niveaux de Prix d'Entrée (Donchian 20 Semaines)")
  entree_ordres = st.text_area(
      "Entrez les tickers pour calculer les ordres d'entrée (ex: TSLA NVDA AMD)"
      " :",
      value="TSLA NVDA AMD MU AAPL",
      key="txt_entree",
  )
  liste_ordres = [t.strip().upper() for t in entree_ordres.split() if t.strip()]

  if st.button(
      "🎯 Calculer les Ordres d'Entrée",
      key="btn_entree",
      use_container_width=True,
  ):
    if not liste_ordres:
      st.warning("Veuillez saisir au moins un ticker.")
    else:
      with st.spinner("Calcul des seuils Donchian 20W..."):
        df_entree = calculer_ordres_entree(liste_ordres)
        if not df_entree.empty:
          df_style_entree = df_entree.style.format({
              "Prix Max Donchian 20W": "{:.2f}",
              "Buy stop": "{:.2f}",
              "Limite": "{:.2f}",
          })
          st.dataframe(
              df_style_entree, use_container_width=True, hide_index=True
          )
        else:
          st.warning("Aucune donnée générée pour ces critères.")

# --- ONGLET 3 : MARKET BREADTH ---
with tab3:
  st.subheader("🌐 Analyse de la Santé Globale du Marché (Market Breadth)")

  if st.button(
      "📊 Calculer le Market Breadth (S&P500 & NASDAQ)",
      key="btn_mb",
      use_container_width=True,
  ):
    with st.spinner(
        "Extraction des listes et calcul de la santé du marché..."
    ):
      sp500_actuel = obtenir_sp500_tickers()
      nasdaq100_actuel = obtenir_nasdaq100_tickers()

      st.caption(
          f"Actifs scannés : S&P 500 ({len(sp500_actuel)} actions) | NASDAQ 100"
          f" ({len(nasdaq100_actuel)} actions)"
      )

      mb_sp500, ad_sp500 = calculer_market_breadth(sp500_actuel, "S&P 500")
      mb_nasdaq, ad_nasdaq = calculer_market_breadth(
          nasdaq100_actuel, "NASDAQ 100"
      )

      res_mb = []
      if mb_sp500:
        res_mb.append(mb_sp500)
      if mb_nasdaq:
        res_mb.append(mb_nasdaq)

      if res_mb:
        df_mb = pd.DataFrame(res_mb)

        # 1. Bannière TRADING OK / TRADING STOP (basée sur le S&P 500 MM200 > 50%)
        sp500_mm200_val = mb_sp500["% > MM200"] if mb_sp500 else 0
        if sp500_mm200_val > 50:
          st.markdown(
              "<h2 style='text-align: center; color: #118d57; background-color:"
              " #e6f4ea; padding: 12px; border-radius: 8px; margin-bottom:"
              " 20px;'>🟢 TRADING OK</h2>",
              unsafe_allow_html=True,
          )
        else:
          st.markdown(
              "<h2 style='text-align: center; color: #b71d18; background-color:"
              " #fce8e6; padding: 12px; border-radius: 8px; margin-bottom:"
              " 20px;'>🔴 TRADING STOP</h2>",
              unsafe_allow_html=True,
          )

        # 2. Tableau Synthétique Complet du Market Breadth
        df_mb_style = df_mb.style.format({
            "% > MM200": "{:.1f}%",
            "% > MM50": "{:.1f}%",
            "Net (NH - NL)": "{:+d}",
            "Net (NH - NL) Veille": "{:+d}",
            "Avances Nettes": "{:+d}",
            "Ratio A/B": "{:.2f}",
        }).map(
            colorier_statut_vert_rouge,
            subset=["État MM200", "État MM50", "État NH/NL"],
        )

        st.dataframe(df_mb_style, use_container_width=True, hide_index=True)

        # 3. Graphique de la Ligne Avance-Baisse Cumulée (60 jours)
        if ad_sp500 is not None and ad_nasdaq is not None:
          st.markdown("---")
          st.subheader(
              "📈 Ligne Avance-Baisse Cumulée (60 derniers jours de trading)"
          )
          st.caption(
              "💡 **Analyse de la hausse** : Si les indices montent et la"
              " ligne avance-baisse monte également, la hausse est solide et"
              " soutenue par une majorité d'actions. Si les indices montent"
              " mais que la ligne baisse, la hausse est tirée par seulement"
              " une poignée d'entreprises."
          )

          df_chart = pd.DataFrame(
              {"S&P 500": ad_sp500, "NASDAQ 100": ad_nasdaq}
          ).dropna()

          st.line_chart(df_chart, use_container_width=True)

      else:
        st.warning("Erreur lors du traitement des données de marché.")

# --- ONGLET 4 : LISTE ENREGISTRÉE ---
with tab4:
  st.subheader("Votre Watchlist")
  tickers_sauvegardes = charger_tickers()
  entree_texte = st.text_area(
      "Modifier les actifs de la liste (séparés par un espace) :",
      value=" ".join(tickers_sauvegardes),
      key="txt_watchlist",
  )
  liste_actifs = sauvegarder_tickers(entree_texte)

  if st.button(
      "🚀 Scanner la Watchlist", key="btn_watchlist", use_container_width=True
  ):
    with st.spinner("Calcul du SMI hebdomadaire..."):
      df_res = calculer_smi_watchlist(liste_actifs)
      if not df_res.empty:
        colonnes_tab4 = [
            "ACTIF",
            "SMI %K (k)",
            "SMI %D (d)",
            "DIFFÉRENCE",
            "HAUT (W)",
            "BAS (W)",
            "CLÔTURE",
        ]
        df_tab4 = df_res[colonnes_tab4].copy()
        df_tab4 = df_tab4.sort_values(by="DIFFÉRENCE", ascending=True)
        df_style4 = df_tab4.style.format(precision=2).map(
            colorier_diff, subset=["DIFFÉRENCE"]
        )
        st.dataframe(df_style4, use_container_width=True, hide_index=True)
      else:
        st.warning("Aucune donnée n'a pu être récupérée.")

# --- ONGLET 5 : TABLEAU AVANCÉ ---
with tab5:
  st.subheader("Tableau de Synthèse Technique Multi-Indicateurs")
  entree_tab5 = st.text_area(
      "Entrez les tickers à analyser pour le tableau complet :",
      value="TSLA NVDA AMD MU AAPL",
      key="txt_tab5",
  )
  liste_tab5 = [t.strip().upper() for t in entree_tab5.split() if t.strip()]

  if st.button(
      "📊 Générer le Tableau Avancé", key="btn_tab5", use_container_width=True
  ):
    if not liste_tab5:
      st.warning("Veuillez saisir au moins un ticker.")
    else:
      with st.spinner("Calcul mathématique des indicateurs complexes..."):
        df_avances = calculer_indicateurs_techniques_avances(liste_tab5)
        if not df_avances.empty:
          ordre_colonnes = [
              "ACTIF",
              "ATR",
              "Ratio th.",
              "Close",
              "High pr",
              "Ratio",
              "Tenkan",
              "Tenkan %",
              "%K",
              "%D",
              "K/D",
              "K-D",
              "ADX14",
              "ADX7",
          ]
          df_final_tab5 = df_avances[ordre_colonnes].copy()

          df_style_tab5 = df_final_tab5.style.format({
              "ATR": "{:.2f}",
              "Ratio th.": "{:.4f}",
              "Close": "{:.2f}",
              "High pr": "{:.2f}",
              "Ratio": "{:.4f}",
              "Tenkan": "{:.2f}",
              "Tenkan %": "{:.4f}",
              "%K": "{:.2f}",
              "%D": "{:.2f}",
              "K/D": "{:.2f}",
              "K-D": "{:.2f}",
              "ADX14": "{:.2f}",
              "ADX7": "{:.2f}",
          })

          st.dataframe(
              df_style_tab5, use_container_width=True, hide_index=True
          )
        else:
          st.warning("Aucune donnée disponible pour ces critères.")
