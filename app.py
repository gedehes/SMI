from io import StringIO
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Analyseur de Breadth de Marché",
    layout="wide",
    initial_sidebar_state="expanded",
)

# En-têtes HTTP imitant un navigateur moderne pour éviter les blocages 403
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


# --- 1. FONCTIONS DE SCRAPING ---


@st.cache_data(ttl=86400)
def obtenir_sp500_tickers():
  """Récupère les tickers du S&P 500 : Slickcharts -> StockAnalysis -> Liste fixe."""
  # 1. Slickcharts
  try:
    url = "https://www.slickcharts.com/sp500"
    res = requests.get(url, headers=HEADERS, timeout=10)
    if res.status_code == 200:
      df = pd.read_html(StringIO(res.text))[0]
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

  # 2. StockAnalysis
  try:
    url = "https://stockanalysis.com/list/sp-500-stocks/"
    res = requests.get(url, headers=HEADERS, timeout=10)
    if res.status_code == 200:
      df = pd.read_html(StringIO(res.text))[0]
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

  # 3. Secours
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
  ]


@st.cache_data(ttl=86400)
def obtenir_nasdaq100_tickers():
  """Récupère les tickers du NASDAQ 100 : Slickcharts -> StockAnalysis -> Liste fixe."""
  # 1. Slickcharts
  try:
    url = "https://www.slickcharts.com/nasdaq100"
    res = requests.get(url, headers=HEADERS, timeout=10)
    if res.status_code == 200:
      df = pd.read_html(StringIO(res.text))[0]
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

  # 2. StockAnalysis
  try:
    url = "https://stockanalysis.com/list/nasdaq-100-stocks/"
    res = requests.get(url, headers=HEADERS, timeout=10)
    if res.status_code == 200:
      df = pd.read_html(StringIO(res.text))[0]
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

  # 3. Secours
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
  ]


# --- 2. TÉLÉCHARGEMENT DE DONNÉES BOURSIÈRES ---


@st.cache_data(ttl=3600)
def telecharger_historique_prix(tickers, Periode="1y"):
  """Télécharge les prix de clôture ajustés via yfinance."""
  donnees = yf.download(tickers, period=Periode, progress=False)

  # Gestion des structures de colonnes retournées par yfinance
  if isinstance(donnees.columns, pd.MultiIndex):
    if "Close" in donnees.columns.levels[0]:
      df_close = donnees["Close"]
    elif "Adj Close" in donnees.columns.levels[0]:
      df_close = donnees["Adj Close"]
    else:
      df_close = donnees.iloc[:, 0]
  else:
    df_close = donnees["Close"] if "Close" in donnees else donnees

  return df_close.ffill().dropna(how="all", axis=1)


# --- 3. CALCULS DE LARGEUR DE MARCHÉ (BREADTH) ---


def calculer_pct_au_dessus_mm(df_close, fenetre):
  """Calcule le % d'actions cotant au-dessus de leur moyenne mobile."""
  mm = df_close.rolling(window=fenetre).mean()
  au_dessus = df_close > mm
  # Pourcentage calculé sur les tickers actifs à chaque date
  pct = (au_dessus.sum(axis=1) / df_close.notna().sum(axis=1)) * 100
  return pct


# --- 4. INTERFACE STREAMLIT ---

st.title("📊 Tableau de Bord - Health & Market Breadth")
st.markdown(
    "Analyse de la participation globale des actions d'un indice par rapport"
    " à leurs moyennes mobiles."
)

# Barre latérale (Paramètres)
st.sidebar.header("Paramètres d'analyse")

indice_choisi = st.sidebar.selectbox(
    "Sélectionner l'Indice", ["S&P 500", "NASDAQ 100"]
)

periode_historique = st.sidebar.selectbox(
    "Période Historique",
    ["6m", "1y", "2y", "5y"],
    index=1,
)

mm_court_terme = st.sidebar.slider("Moyenne Mobile Courte (Jours)", 10, 50, 20)
mm_moyen_terme = st.sidebar.slider("Moyenne Mobile Moyenne (Jours)", 20, 100, 50)
mm_long_terme = st.sidebar.slider("Moyenne Mobile Longue (Jours)", 50, 200, 200)

# Chargement de la liste des symboles
with st.spinner("Récupération des tickers..."):
  if indice_choisi == "S&P 500":
    list_tickers = obtenir_sp500_tickers()
  else:
    list_tickers = obtenir_nasdaq100_tickers()

st.sidebar.success(f"Tickers chargés : {len(list_tickers)}")

# Chargement des prix
with st.spinner("Téléchargement des cours boursiers..."):
  df_close = telecharger_historique_prix(list_tickers, periode_historique)

if df_close.empty:
  st.error(
      "Impossible de récupérer les cours boursiers. Réessayez plus tard."
  )
  st.stop()

# Calculs de la Breadth
breadth_court = calculer_pct_au_dessus_mm(df_close, mm_court_terme)
breadth_moyen = calculer_pct_au_dessus_mm(df_close, mm_moyen_terme)
breadth_long = calculer_pct_au_dessus_mm(df_close, mm_long_terme)

# KPI Cards (Dernières valeurs connues)
derniere_date = df_close.index[-1].strftime("%d/%m/%Y")
st.subheader(f"Statut au {derniere_date}")

col1, col2, col3, col4 = st.columns(4)

val_court = breadth_court.iloc[-1]
val_moyen = breadth_moyen.iloc[-1]
val_long = breadth_long.iloc[-1]

# Calcul de l'Advance / Decline du jour
var_jour = df_close.pct_change().iloc[-1]
hausses = (var_jour > 0).sum()
baisses = (var_jour < 0).sum()

col1.metric(f"% > MM{mm_court_terme}", f"{val_court:.1f}%")
col2.metric(f"% > MM{mm_moyen_terme}", f"{val_moyen:.1f}%")
col3.metric(f"% > MM{mm_long_terme}", f"{val_long:.1f}%")
col4.metric(
    "Avancées / Déclins (1J)",
    f"{hausses} / {baisses}",
    delta=f"{hausses - baisses} Net",
)

# Graphique temporel Plotly
st.subheader("Évolution de la participation du marché")

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=breadth_court.index,
        y=breadth_court,
        mode="lines",
        name=f"% > MM{mm_court_terme}",
        line=dict(color="#FFA500", width=1.5),
    )
)

fig.add_trace(
    go.Scatter(
        x=breadth_moyen.index,
        y=breadth_moyen,
        mode="lines",
        name=f"% > MM{mm_moyen_terme}",
        line=dict(color="#1E90FF", width=2),
    )
)

fig.add_trace(
    go.Scatter(
        x=breadth_long.index,
        y=breadth_long,
        mode="lines",
        name=f"% > MM{mm_long_terme}",
        line=dict(color="#2E8B57", width=2),
    )
)

# Lignes de surachat / survente classiques (70% et 30%)
fig.add_hline(
    y=70,
    line_dash="dash",
    line_color="red",
    annotation_text="Zone Surachat (70%)",
)
fig.add_hline(
    y=30,
    line_dash="dash",
    line_color="green",
    annotation_text="Zone Survente (30%)",
)

fig.update_layout(
    yaxis=dict(title="Pourcentage (%)", range=[0, 100]),
    xaxis=dict(title="Date"),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=20, r=20, t=40, b=20),
    height=500,
)

st.plotly_chart(fig, use_container_width=True)

# Tableau de détail par action
with st.expander("🔍 Voir le détail par titre (Dernière séance)"):
  derniers_prix = df_close.iloc[-1]
  mm_c = df_close.rolling(mm_court_terme).mean().iloc[-1]
  mm_m = df_close.rolling(mm_moyen_terme).mean().iloc[-1]
  mm_l = df_close.rolling(mm_long_terme).mean().iloc[-1]

  df_status = pd.DataFrame({
      "Prix": derniers_prix,
      f"MM{mm_court_terme}": mm_c,
      f"> MM{mm_court_terme}": derniers_prix > mm_c,
      f"MM{mm_moyen_terme}": mm_m,
      f"> MM{mm_moyen_terme}": derniers_prix > mm_m,
      f"MM{mm_long_terme}": mm_l,
      f"> MM{mm_long_terme}": derniers_prix > mm_l,
  })

  st.dataframe(df_status, use_container_width=True)
