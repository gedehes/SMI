import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import os

# Configuration de la page pour le mobile
st.set_page_config(page_title="Scanner SMI Custom", layout="wide")

FILENAME = "mes_tickers.txt"

def charger_tickers():
    if os.path.exists(FILENAME):
        with open(FILENAME, "r") as f:
            return [line.strip().upper() for line in f if line.strip()]
    return ["GOOG", "MU", "MSFT"] # Tickers par défaut si le fichier n'existe pas

def sauvegarder_tickers(liste_str):
    tickers = [t.strip().upper() for t in liste_str.split() if t.strip()]
    with open(FILENAME, "w") as f:
        for ticker in sorted(list(set(tickers))):
            f.write(f"{ticker}\n")
    return tickers

# --- INTERFACE STREAMLIT ---
st.title("📊 Scanner SMI Personnel (14, 4, 1, 14, EMA)")

# Gestion de la liste dans la barre latérale (Sidebar)
st.sidebar.header("⚙️ Configuration")
tickers_actuels = charger_tickers()
tickers_texte = st.sidebar.text_area(
    "Modifier la liste (séparés par un espace ou retour à la ligne) :",
    value=" ".join(tickers_actuels),
    height=200
)

# Sauvegarde automatique dès que la liste change
ma_liste = sauvegarder_tickers(tickers_texte)
st.sidebar.write(f"📋 **{len(ma_liste)} actifs configurés.**")

# Bouton principal de scan
bouton_scan = st.button("🚀 Lancer le Scan Hebdomadaire", use_container_width=True)

# --- MOTEUR DE CALCUL ---
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
            
            if len(df_final) < 14: continue
            
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
            
            last_calculated = df_final.iloc[-1]
            
            results.append({
                "ACTIF": ticker, 
                "SMI %K (k)": float(last_calculated['SMI_K']),
                "SMI %D (d)": float(last_calculated['SMI_D']), 
                "DIFFÉRENCE": float(last_calculated['Diff']),
                "HAUT (W)": float(last_calculated['High']),
                "BAS (W)": float(last_calculated['Low']),
                "CLÔTURE": float(last_calculated['Close'])
            })
        except Exception:
            continue
    return pd.DataFrame(results)

# --- ACTION ET AFFICHAGE ---
if bouton_scan:
    if not ma_liste:
        st.warning("⚠️ Veuillez ajouter au moins un ticker dans la liste.")
    else:
        with st.spinner("Analyse et synchronisation des données en cours..."):
            df_result = get_smi_custom(ma_liste)
            
            if not df_result.empty:
                # 1. Tri automatique par différence CROISSANTE (ascending=True)
                df_result = df_result.sort_values(by="DIFFÉRENCE", ascending=True)
                
                # Stylisation des couleurs pour la colonne DIFFÉRENCE
                def colorier_diff(val):
                    color = '#118d57' if val >= 0 else '#b71d18'
                    return f'color: {color}; font-weight: bold'
                
                # 2. Strictement 2 décimales maximum pour TOUTES les colonnes numériques
                df_style = df_result.style.format(precision=2).map(colorier_diff, subset=['DIFFÉRENCE'])
                
                # Affichage du tableau interactif
                st.success("Analyses terminées !")
                st.dataframe(
                    df_style, 
                    use_container_width=True, 
                    hide_index=True,
                    height=min(40 * len(df_result) + 40, 600)
                )
            else:
                st.error("Aucune donnée n'a pu être récupérée pour les tickers configurés.")
