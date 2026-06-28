import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os

# Configuration de la page
st.set_page_config(page_title="Scanner SMI", layout="wide")

FILENAME = "mes_tickers.txt"

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

# --- NETTOYAGE DES COLONNES MULTI-INDEX ---
def aplatir_donnees(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# --- CALCUL DU SMI POUR LES ONGLETS 1 & 2 (INTOUCHÉ) ---
def calculer_smi_watchlist(ticker_list):
    results = []
    for ticker in ticker_list:
        try:
            df = yf.download(ticker, period="3y", interval="1wk", progress=False)
            if df.empty:
                continue
            df = aplatir_donnees(df)
            if not all(col in df.columns for col in ['High', 'Low', 'Close']):
                continue
            if len(df) < 30: 
                continue

            période = 14
            df['LL'] = df['Low'].rolling(window=période).min()
            df['HH'] = df['High'].rolling(window=période).max()
            df['HL_Center'] = (df['HH'] + df['LL']) / 2
            
            df['D'] = df['Close'] - df['HL_Center']
            df['HL_Range'] = df['HH'] - df['LL']
            
            df['D_Smooth1'] = df['D'].ewm(span=4, adjust=False).mean()
            df['D_Smooth2'] = df['D_Smooth1'].ewm(span=1, adjust=False).mean()
            
            df['Range_Smooth1'] = df['HL_Range'].ewm(span=4, adjust=False).mean()
            df['Range_Smooth2'] = df['Range_Smooth1'].ewm(span=1, adjust=False).mean()
            
            df['Range_Smooth2'] = df['Range_Smooth2'].apply(lambda x: x if x != 0 else 0.00001)
            
            df['SMI_K'] = 100 * (df['D_Smooth2'] / (0.5 * df['Range_Smooth2']))
            df['SMI_D'] = df['SMI_K'].ewm(span=14, adjust=False).mean()
            df['Diff'] = df['SMI_K'] - df['SMI_D']
            
            derniere_ligne = df.iloc[-1]
            ligne_precedente = df.iloc[-2]
            
            cloture_actuelle = float(derniere_ligne['Close'])
            haut_actuel = float(derniere_ligne['High'])
            bas_actuel = float(derniere_ligne['Low'])
            
            k_actuel = float(derniere_ligne['SMI_K'])
            d_actuel = float(derniere_ligne['SMI_D'])
            diff_actuelle = float(derniere_ligne['Diff'])
            k_precedent = float(ligne_precedente['SMI_K'])
            
            tendance = "🔼 Croissant" if k_actuel >= k_precedent else "🔽 Décroissant"
            
            results.append({
                "ACTIF": ticker,
                "SMI %K (k)": k_actuel,
                "SMI %D (d)": d_actuel,
                "DIFFÉRENCE": diff_actuelle,
                "TENDANCE": tendance,
                "HAUT (W)": haut_actuel,
                "BAS (W)": bas_actuel,
                "CLÔTURE": cloture_actuelle
            })
        except Exception as e:
            st.error(f"Erreur sur le ticker {ticker} : {str(e)}")
            continue
    return pd.DataFrame(results)

# --- CALCUL DES INDICATEURS AVANCÉS POUR L'ONGLET 3 ---
def calculer_indicateurs_techniques_avances(ticker_list):
    results = []
    for ticker in ticker_list:
        try:
            df = yf.download(ticker, period="3y", interval="1wk", progress=False)
            if df.empty:
                continue
            df = aplatir_donnees(df)
            if not all(col in df.columns for col in ['High', 'Low', 'Close']):
                continue
            if len(df) < 40: 
                continue

            # 1. Base des prix actuels
            cloture_actuelle = float(df['Close'].iloc[-1])
            
            # 2. ATR (14) - Lissage de Wilder
            df['High_Low'] = df['High'] - df['Low']
            df['High_ClosePrev'] = (df['High'] - df['Close'].shift(1)).abs()
            df['Low_ClosePrev'] = (df['Low'] - df['Close'].shift(1)).abs()
            df['TR'] = df[['High_Low', 'High_ClosePrev', 'Low_ClosePrev']].max(axis=1)
            df['ATR'] = df['TR'].ewm(alpha=1/14, adjust=False).mean()
            atr_actuel = float(df['ATR'].iloc[-1])
            
            # Calcul : Ratio th. (Format numérique sous forme de décimale brute)
            ratio_th = (atr_actuel / cloture_actuelle)
            
            # 3. High pr : Plus haut des 12 semaines précédentes (excluant la semaine en cours)
            high_pr_val = float(df['High'].shift(1).rolling(window=12).max().iloc[-1])
            
            # Calcul : Ratio (Format numérique sous forme de décimale brute)
            ratio_high = (cloture_actuelle / high_pr_val - 1)
            
            # 4. Tenkan (Période 9 d'Ichimoku)
            df['Tenkan'] = (df['High'].rolling(window=9).max() + df['Low'].rolling(window=9).min()) / 2
            tenkan_actuel = float(df['Tenkan'].iloc[-1])
            
            # Calcul : Tenkan % (Format numérique sous forme de décimale brute)
            tenkan_pct = (cloture_actuelle / tenkan_actuel - 1)
            
            # 5. SMI Identique (14, 4, 1, 14)
            période = 14
            df['LL'] = df['Low'].rolling(window=période).min()
            df['HH'] = df['High'].rolling(window=période).max()
            df['HL_Center'] = (df['HH'] + df['LL']) / 2
            df['D'] = df['Close'] - df['HL_Center']
            df['HL_Range'] = df['HH'] - df['LL']
            
            df['D_Smooth1'] = df['D'].ewm(span=4, adjust=False).mean()
            df['D_Smooth2'] = df['D_Smooth1'].ewm(span=1, adjust=False).mean()
            df['Range_Smooth1'] = df['HL_Range'].ewm(span=4, adjust=False).mean()
            df['Range_Smooth2'] = df['Range_Smooth1'].ewm(span=1, adjust=False).mean()
            df['Range_Smooth2'] = df['Range_Smooth2'].apply(lambda x: x if x != 0 else 0.00001)
            
            df['SMI_K'] = 100 * (df['D_Smooth2'] / (0.5 * df['Range_Smooth2']))
            df['SMI_D'] = df['SMI_K'].ewm(span=14, adjust=False).mean()
            
            k_actuel = float(df['SMI_K'].iloc[-1])
            d_actuel = float(df['SMI_D'].iloc[-1])
            
            # Calculs SMI dérivés
            kd_ratio = k_actuel / d_actuel if d_actuel != 0 else np.nan
            kd_diff = k_actuel - d_actuel

            # 6. Fonction ADX avec lissage Wilder standard (alpha=1/N)
            def calculer_adx_w(data, N, smoothing_N):
                plus_dm = data['High'].diff()
                minus_dm = -data['Low'].diff()
                
                p_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
                m_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)
                
                smooth_tr = data['TR'].ewm(alpha=1/N, adjust=False).mean()
                smooth_p_dm = pd.Series(p_dm, index=data.index).ewm(alpha=1/N, adjust=False).mean()
                smooth_m_dm = pd.Series(m_dm, index=data.index).ewm(alpha=1/N, adjust=False).mean()
                
                p_di = 100 * (smooth_p_dm / smooth_tr)
                m_di = 100 * (smooth_m_dm / smooth_tr)
                
                dx = 100 * (p_di - m_di).abs() / (p_di + m_di)
                adx = dx.ewm(alpha=1/smoothing_N, adjust=False).mean()
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
                "ADX7": adx7_val
            })
        except Exception as e:
            st.error(f"Erreur sur le ticker {ticker} (Onglet 3) : {str(e)}")
            continue
    return pd.DataFrame(results)

# --- STYLISATION DES TABLEAUX ---
def colorier_diff(val):
    try:
        color = '#118d57' if float(val) >= 0 else '#b71d18'
        return f'color: {color}; font-weight: bold'
    except:
        return ''

def colorier_tendance(val):
    color = '#118d57' if "Croissant" in str(val) else '#b71d18'
    return f'color: {color}; font-weight: bold'


# --- INTERFACE UTILISATEUR STREAMLIT ---
st.title("📊 Scanner SMI Épuré & Avancé")

tab1, tab2, tab3 = st.tabs(["📋 Liste Enregistrée", "⚡ Analyse Flash", "📈 Indicateurs Avancés"])

# --- ONGLET 1 : LISTE ENREGISTRÉE (WATCHLIST) ---
with tab1:
    st.subheader("Votre Watchlist")
    tickers_sauvegardes = charger_tickers()
    entree_texte = st.text_area(
        "Modifier les actifs de la liste (séparés par un espace) :",
        value=" ".join(tickers_sauvegardes),
        key="txt_watchlist"
    )
    liste_actifs = sauvegarder_tickers(entree_texte)
    
    if st.button("🚀 Scanner la Watchlist", key="btn_watchlist", use_container_width=True):
        with st.spinner("Calcul du SMI hebdomadaire..."):
            df_res = calculer_smi_watchlist(liste_actifs)
            if not df_res.empty:
                colonnes_tab1 = ["ACTIF", "SMI %K (k)", "SMI %D (d)", "DIFFÉRENCE", "HAUT (W)", "BAS (W)", "CLÔTURE"]
                df_
