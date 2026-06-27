import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import os

# Configuration de la page optimisée pour mobile
st.set_page_config(page_title="Scanner SMI Custom", layout="wide")

FILENAME = "mes_tickers.txt"

def charger_tickers():
    if os.path.exists(FILENAME):
        with open(FILENAME, "r") as f:
            return [line.strip().upper() for line in f if line.strip()]
    return ["GOOG", "MU", "MSFT"]

def sauvegarder_tickers(liste_str):
    tickers = [t.strip().upper() for t in liste_str.split() if t.strip()]
    with open(FILENAME, "w") as f:
        for ticker in sorted(list(set(tickers))):
            f.write(f"{ticker}\n")
    return tickers

# --- MOTEUR DE CALCUL UNIFIÉ ---
def get_smi_custom(ticker_list):
    results = []
    today = datetime.date.today()
    monday_this_week = today - datetime.timedelta(days=today.weekday())
    
    for ticker in ticker_list:
        try:
            df_wk = yf.download(ticker, period="5y", interval="1wk", progress=False, auto_adjust=False)
            if df_wk.empty: continue
            if isinstance(df_wk.columns, pd.MultiIndex): df_wk.columns = df_wk.columns.get_level_values(0)
            
            df_d = yf.download(ticker, period="10d", interval="1d", progress=False, auto_adjust=False)
            if df_d.empty: continue
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            
            this_week_daily = df_d[df_d.index.date >= monday_this_week]
            
            if not this_week_daily.empty:
                w_open = this_week_daily['Open'].iloc[0]
                w_high = this_week_daily['High'].max()
                w_low = this_week_daily['Low'].min()
                w_close = this_week_daily['Close'].iloc[-1]
                
                df_wk = df_wk[df_wk.index.date < monday_this_week].copy()
                current_week_row = pd.DataFrame({'Open': [w_open], 'High': [w_high], 'Low': [w_low], 'Close': [w_close]}, index=[pd.Timestamp(monday_this_week)])
                df_final = pd.concat([df_wk, current_week_row])
            else:
                df_final = df_wk.copy()
            
            if len(df_final) < 15: continue # Sécurité pour avoir au moins 2 périodes calculées
            
            # Formule SMI (14, 4, 1, 14, EMA)
            rolling_high = df_final['High'].rolling(14).max()
            rolling_low = df_final['Low'].rolling(14).min()
            mid = (rolling_high + rolling_low) / 2
            diff = df_final['Close'] - mid
            hl_range = rolling_high - rolling_low
            
            ema1_diff = diff.ewm(span=4, adjust=False).mean()
            ema1_range = hl_range.ewm(span=4, adjust=False).mean()
            
            ema2_diff = ema1_diff.ewm(span=1, adjust=False).mean()
            ema2_range = ema1_range.ewm(span=1, adjust=False).mean()
            ema2_range = ema2_range.apply(lambda x: x if x != 0 else 0.00001)
            
            df_final['SMI_K'] = 100 * (ema2_diff / (0.5 * ema2_range))
            df_final['SMI_D'] = df_final['SMI_K'].ewm(span=14, adjust=False).mean()
            df_final['Diff'] = df_final['SMI_K'] - df_final['SMI_D']
            
            # Extraction de la période actuelle (-1) et précédente (-2)
            last_calculated = df_final.iloc[-1]
            prev_calculated = df_final.iloc[-2]
            
            last_k = float(last_calculated['SMI_K'])
            prev_k = float(prev_calculated['SMI_K'])
            
            # Calcul de la tendance du Stochastic Momentum
            tendance = "🔼 Croissant" if last_k >= prev_k else "🔽 Décroissant"
            
            results.append({
                "ACTIF": ticker, 
                "SMI %K (k)": last_k,
                "SMI %D (d)": float(last_calculated['SMI_D']), 
                "DIFFÉRENCE": float(last_calculated['Diff']),
                "TENDANCE": tendance,
                "HAUT (W)": float(last_calculated['High']),
                "BAS (W)": float(last_calculated['Low']),
                "CLÔTURE": float(last_calculated['Close'])
            })
        except Exception:
            continue
    return pd.DataFrame(results)

# --- FONCTIONS DE STYLISATION DE COULEUR ---
def colorier_diff(val):
    color = '#118d57' if val >= 0 else '#b71d18'
    return f'color: {color}; font-weight: bold'

def colorier_tendance(val):
    color = '#118d57' if "Croissant" in str(val) else '#b71d18'
    return f'color: {color}; font-weight: bold'


# --- ARCHITECTURE DE L'INTERFACE WEB ---
st.title("📊 Application SMI Globale (14, 4, 1, 14, EMA)")

# Création des deux onglets
tab1, tab2 = st.tabs(["📋 Liste Enregistrée", "⚡ Analyse Flash + Tendance"])

# --- ONGLET 1 : LISTE ENREGISTRÉE ---
with tab1:
    st.subheader("Gestion de votre Watchlist Permanente")
    tickers_actuels = charger_tickers()
    
    tickers_texte = st.text_area(
        "Modifier votre liste permanente (séparés par un espace) :",
        value=" ".join(tickers_actuels),
        key="txt_tab1"
    )
    liste_tab1 = sauvegarder_tickers(tickers_texte)
    st.caption(f"Actifs sauvegardés : {len(liste_tab1)}")
    
    if st.button("🚀 Lancer le Scan de la Liste", key="btn_tab1", use_container_width=True):
        with st.spinner("Analyse de votre liste en cours..."):
            df_res = get_smi_custom(liste_tab1)
            if not df_res.empty:
                df_res = df_res.sort_values(by="DIFFÉRENCE", ascending=True)
                # On retire la colonne tendance pour cet onglet afin de garder l'affichage épuré demandé initialement
                df_res_clean = df_res.drop(columns=["TENDANCE"])
                
                df_style = df_res_clean.style.format(precision=2).map(colorier_diff, subset=['DIFFÉRENCE'])
                st.dataframe(df_style, use_container_width=True, hide_index=True)
            else:
                st.error("Aucune donnée disponible.")

# --- ONGLET 2 : ANALYSE FLASH + TENDANCE ---
with tab2:
    st.subheader("Analyse Instantanée avec Tendance de Période")
    st.markdown("_Saisissez des tickers temporaires pour une analyse immédiate sans modifier votre liste principale._")
    
    tickers_flash_texte = st.text_area(
        "Entrez les tickers à analyser (ex: AAPL NVDA TSLA) :",
        value="AAPL NVDA TSLA",
        key="txt_tab2"
    )
    
    liste_tab2 = [t.strip().upper() for t in tickers_flash_texte.split() if t.strip()]
    
    if st.button("🔍 Lancer l'Analyse Flash + Tendance", key="btn_tab2", use_container_width=True):
        if not liste_tab2:
            st.warning("⚠️ Veuillez entrer au moins un ticker.")
        else:
            with st.spinner("Calcul des indicateurs et de la dynamique de tendance..."):
                df_res = get_smi_custom(liste_tab2)
                if not df_res.empty:
                    # Tri par différence Croissante
                    df_res = df_res.sort_values(by="DIFFÉRENCE", ascending=True)
                    
                    # Application du double formatage de couleur (Différence et Tendance)
                    df_style = (df_res.style.format(precision=2)
                                .map(colorier_diff, subset=['DIFFÉRENCE'])
                                .map(colorier_tendance, subset=['TENDANCE']))
                    
                    st.success("Analyse dynamique terminée !")
                    st.dataframe(df_style, use_container_width=True, hide_index=True)
                else:
                    st.error("Impossible de récupérer les données pour ces actifs.")
