import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
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

# --- MOTEUR DE CALCUL CENTRALISÉ ---
def calculer_indicateurs_globaux(ticker_list):
    results = []
    today = datetime.date.today()
    monday_this_week = today - datetime.timedelta(days=today.weekday())
    
    for ticker in ticker_list:
        try:
            # 1. Récupération des données historiques
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
            
            if len(df_final) < 60: continue
            
            # --- FORMULE STRICTE SMI (14, 4, 1, 14, EMA) ---
            rolling_high_14 = df_final['High'].rolling(14).max()
            rolling_low_14 = df_final['Low'].rolling(14).min()
            mid_14 = (rolling_high_14 + rolling_low_14) / 2
            diff_14 = df_final['Close'] - mid_14
            hl_range_14 = rolling_high_14 - rolling_low_14
            
            ema1_diff = diff_14.ewm(span=4, adjust=False).mean()
            ema1_range = hl_range_14.ewm(span=4, adjust=False).mean()
            
            ema2_diff = ema1_diff.ewm(span=1, adjust=False).mean()
            ema2_range = ema1_range.ewm(span=1, adjust=False).mean()
            ema2_range = ema2_range.apply(lambda x: x if x != 0 else 0.00001)
            
            df_final['SMI_K'] = 100 * (ema2_diff / (0.5 * ema2_range))
            df_final['SMI_D'] = df_final['SMI_K'].ewm(span=14, adjust=False).mean()
            df_final['Diff'] = df_final['SMI_K'] - df_final['SMI_D']
            
            # --- EXTRACTION DES COMPOSANTES ---
            last_row = df_final.iloc[-1]
            prev_row = df_final.iloc[-2]
            
            close_val = float(last_row['Close'])
            high_val = float(last_row['High'])
            low_val = float(last_row['Low'])
            
            last_k = float(last_row['SMI_K'])
            last_d = float(last_row['SMI_D'])
            last_diff = float(last_row['Diff']) # <-- Correction : Définition de la variable manquante
            prev_k = float(prev_row['SMI_K'])
            
            tendance = "🔼 Croissant" if last_k >= prev_k else "🔽 Décroissant"
            
            # ATR (14) Weekly
            prev_close = df_final['Close'].shift(1)
            tr = pd.concat([
                df_final['High'] - df_final['Low'],
                (df_final['High'] - prev_close).abs(),
                (df_final['Low'] - prev_close).abs()
            ], axis=1).max(axis=1)
            atr14_series = tr.ewm(alpha=1/14, adjust=False).mean()
            atr_val = float(atr14_series.iloc[-1])
            
            ratio_th_val = (atr_val / close_val * 100) if close_val != 0 else 0
            
            # High pr : 2ème plus haut réel sur 12 semaines
            last_12_highs = df_final['High'].iloc[-12:]
            high_pr_val = float(last_12_highs.nlargest(2).iloc[-1]) if len(last_12_highs) >= 2 else high_val
            
            ratio_val = ((close_val / high_pr_val) - 1) * 100 if high_pr_val != 0 else 0
            
            # Tenkan Ichimoku (9)
            tenkan_series = (df_final['High'].rolling(9).max() + df_final['Low'].rolling(9).min()) / 2
            tenkan_val = float(tenkan_series.iloc[-1])
            tenkan_pct_val = ((close_val / tenkan_val) - 1) * 100 if tenkan_val != 0 else 0
            
            kd_ratio_val = (last_k / last_d) if last_d != 0 else 0
            kd_diff_val = last_k - last_d
            
            # Fonction interne ADX (Wilder)
            def calculer_adx(df, p):
                p_high = df['High'].shift(1)
                p_low = df['Low'].shift(1)
                p_close = df['Close'].shift(1)
                v_tr = pd.concat([df['High'] - df['Low'], (df['High'] - p_close).abs(), (df['Low'] - p_close).abs()], axis=1).max(axis=1)
                dp = df['High'] - p_high
                dm = p_low - df['Low']
                dp = pd.Series(np.where((dp > dm) & (dp > 0), dp, 0), index=df.index)
                dm = pd.Series(np.where((dm > dp) & (dm > 0), dm, 0), index=df.index)
                tr_s = v_tr.ewm(alpha=1/p, adjust=False).mean().apply(lambda x: x if x != 0 else 0.00001)
                dp_s = dp.ewm(alpha=1/p, adjust=False).mean()
                dm_s = dm.ewm(alpha=1/p, adjust=False).mean()
                di_p = 100 * (dp_s / tr_s)
                di_m = 100 * (dm_s / tr_s)
                di_sum = (di_p + di_m).apply(lambda x: x if x != 0 else 0.00001)
                v_dx = 100 * ((di_p - di_m).abs() / di_sum)
                v_adx = v_dx.ewm(alpha=1/p, adjust=False).mean()
                return float(v_adx.iloc[-1])
            
            adx14_val = calculer_adx(df_final, 14)
            adx7_val = calculer_adx(df_final, 7)
            
            results.append({
                "ACTIF": ticker, 
                "SMI %K (k)": last_k,
                "SMI %D (d)": last_d, 
                "DIFFÉRENCE": last_diff,
                "TENDANCE": tendance,
                "HAUT (W)": high_val,
                "BAS (W)": low_val,
                "CLÔTURE": close_val,
                "ATR": atr_val,
                "Ratio th.": ratio_th_val,
                "Close": close_val,
                "High pr": high_pr_val,
                "Ratio": ratio_val,
                "Tenkan": tenkan_val,
                "Tenkan %": tenkan_pct_val,
                "%K": last_k,
                "%D": last_d,
                "K/D": kd_ratio_val,
                "K-D": kd_diff_val,
                "ADX14": adx14_val,
                "ADX7": adx7_val
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


# --- STRUCTURE INTERFACE ---
st.title("📊 Terminal SMI & Indicateurs Avancés")

tab1, tab2, tab3 = st.tabs(["📋 Liste Enregistrée", "⚡ Analyse Flash + Tendance", "🧬 Dashboard Multi-Indicateurs"])

# --- ONGLET 1 : LISTE ENREGISTRÉE ---
with tab1:
    st.subheader("Watchlist Permanente")
    tickers_actuels = charger_tickers()
    
    tickers_texte = st.text_area(
        "Modifier votre liste permanente (séparés par un espace) :",
        value=" ".join(tickers_actuels),
        key="txt_tab1"
    )
    liste_tab1 = sauvegarder_tickers(tickers_texte)
    st.caption(f"Actifs enregistrés : {len(liste_tab1)}")
    
    if st.button("🚀 Lancer le Scan de la Liste", key="btn_tab1", use_container_width=True):
        with st.spinner("Analyse de votre liste en cours..."):
            df_all = calculer_indicateurs_globaux(liste_tab1)
            if not df_all.empty:
                df_tab1 = df_all[["ACTIF", "SMI %K (k)", "SMI %D (d)", "DIFFÉRENCE", "HAUT (W)", "BAS (W)", "CLÔTURE"]].copy()
                df_tab1 = df_tab1.sort_values(by="DIFFÉRENCE", ascending=True)
                
                df_style = df_tab1.style.format(precision=2).map(colorier_diff, subset=['DIFFÉRENCE'])
                st.dataframe(df_style, use_container_width=True, hide_index=True)
            else:
                st.error("Aucune donnée disponible.")

# --- ONGLET 2 : ANALYSE FLASH + TENDANCE ---
with tab2:
    st.subheader("Analyse Flash Éphémère")
    tickers_flash_texte = st.text_area(
        "Entrez les tickers à analyser (ex: AAPL NVDA TSLA) :",
        value="AAPL NVDA TSLA GOOG",
        key="txt_tab2"
    )
    liste_tab2 = [t.strip().upper() for t in tickers_flash_texte.split() if t.strip()]
    
    if st.button("🔍 Analyser la Liste Flash", key="btn_tab2", use_container_width=True):
        if not liste_tab2:
            st.warning("⚠️ Veuillez entrer au moins un ticker.")
        else:
            with st.spinner("Calcul avec dynamique de tendance en cours..."):
                df_all = calculer_indicateurs_globaux(liste_tab2)
                if not df_all.empty:
                    df_tab2 = df_all[["ACTIF", "SMI %K (k)", "SMI %D (d)", "DIFFÉRENCE", "TENDANCE", "HAUT (W)", "BAS (W)", "CLÔTURE"]].copy()
                    df_tab2 = df_tab2.sort_values(by="DIFFÉRENCE", ascending=True)
                    
                    df_style = (df_tab2.style.format(precision=2)
                                .map(colorier_diff, subset=['DIFFÉRENCE'])
                                .map(colorier_tendance, subset=['TENDANCE']))
                    st.dataframe(df_style, use_container_width=True, hide_index=True)
                else:
                    st.error("Impossible de récupérer les données.")

# --- ONGLET 3 : DASHBOARD MULTI-INDICATEURS ---
with tab3:
    st.subheader("Analyse Technique Avancée Globale")
    st.markdown("_Toutes les données sont calculées en base Hebdomadaire (Weekly) synchronisée._")
    
    tickers_tab3_texte = st.text_area(
        "Entrez les tickers à étudier pour le grand tableau :",
        value="GOOG MU MSFT AAPL NVDA",
        key="txt_tab3"
    )
    liste_tab3 = [t.strip().upper() for t in tickers_tab3_texte.split() if t.strip()]
    
    if st.button("🧬 Générer le Tableau Multi-Indicateurs", key="btn_tab3", use_container_width=True):
        if not liste_tab3:
            st.warning("⚠️ Veuillez entrer au moins un ticker.")
        else:
            with st.spinner("Extraction et génération du tableau de synthèse..."):
                df_all = calculer_indicateurs_globaux(liste_tab3)
                if not df_all.empty:
                    colonnes_ordre = [
                        "ACTIF", "ATR", "Ratio th.", "Close", "High pr", "Ratio", 
                        "Tenkan", "Tenkan %", "%K", "%D", "K/D", "K-D", "ADX14", "ADX7"
                    ]
                    df_tab3 = df_all[colonnes_ordre].copy()
                    
                    df_style = (df_tab3.style.format(precision=2)
                                .map(colorier_diff, subset=['K-D']))
                    
                    st.success("Tableau de synthèse généré !")
                    st.dataframe(df_style, use_container_width=True, hide_index=True)
                else:
                    st.error("Aucune donnée n'a pu être extraite pour cette liste.")
