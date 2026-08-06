import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os

# Configuration de la page
st.set_page_config(page_title="Scanner SMI & Breakout", layout="wide")

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

# --- CALCUL DU SMI & VOLUME POUR LES ONGLETS 1 & 3 ---
def calculer_smi_watchlist(ticker_list):
    results = []
    for ticker in ticker_list:
        try:
            df = yf.download(ticker, period="3y", interval="1wk", progress=False)
            if df.empty:
                continue
            df = aplatir_donnees(df)
            if not all(col in df.columns for col in ['High', 'Low', 'Close', 'Volume']):
                continue
            if len(df) < 30: 
                continue

            # Calcul du SMI (14, 4, 1, 14)
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
            
            # Calcul MM20 du Volume Hebdo
            df['Vol_MM20'] = df['Volume'].rolling(window=20).mean()

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
            
            # Comparaison Volume Hebdo vs MM20 Volume
            vol_actuel = float(derniere_ligne['Volume'])
            vol_mm20 = float(derniere_ligne['Vol_MM20'])
            vol_status = "Supérieur" if vol_actuel > vol_mm20 else "Inférieur"

            results.append({
                "ACTIF": ticker,
                "SMI %K (k)": k_actuel,
                "SMI %D (d)": d_actuel,
                "DIFFÉRENCE": diff_actuelle,
                "TENDANCE": tendance,
                "Volume hebdo": vol_status,
                "HAUT (W)": haut_actuel,
                "BAS (W)": bas_actuel,
                "CLÔTURE": cloture_actuelle
            })
        except Exception as e:
            st.error(f"Erreur sur le ticker {ticker} : {str(e)}")
            continue
    return pd.DataFrame(results)

# --- CALCUL DES NIVEAUX D'ENTRÉE (ONGLET 2) ---
def calculer_ordres_entree(ticker_list):
    results = []
    for ticker in ticker_list:
        try:
            df = yf.download(ticker, period="1y", interval="1wk", progress=False)
            if df.empty:
                continue
            df = aplatir_donnees(df)
            if 'High' not in df.columns:
                continue
            
            derniere_ligne = df.iloc[-1]
            prix_max_w = float(derniere_ligne['High'])
            
            buy_stop = prix_max_w * 1.005
            limite = buy_stop * 1.01
            
            results.append({
                "ACTIF": ticker,
                "Prix Max (W)": prix_max_w,
                "Buy stop": buy_stop,
                "Limite": limite
            })
        except Exception as e:
            st.error(f"Erreur sur le ticker {ticker} (Onglet Entrée) : {str(e)}")
            continue
    return pd.DataFrame(results)

# --- CALCUL DES INDICATEURS AVANCÉS POUR L'ONGLET 4 ---
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

            cloture_actuelle = float(df['Close'].iloc[-1])
            
            # ATR (14)
            df['High_Low'] = df['High'] - df['Low']
            df['High_ClosePrev'] = (df['High'] - df['Close'].shift(1)).abs()
            df['Low_ClosePrev'] = (df['Low'] - df['Close'].shift(1)).abs()
            df['TR'] = df[['High_Low', 'High_ClosePrev', 'Low_ClosePrev']].max(axis=1)
            df['ATR'] = df['TR'].ewm(alpha=1/14, adjust=False).mean()
            atr_actuel = float(df['ATR'].iloc[-1])
            ratio_th = (atr_actuel / cloture_actuelle)
            
            # High pr (12 semaines)
            high_pr_val = float(df['High'].shift(1).rolling(window=12).max().iloc[-1])
            ratio_high = (cloture_actuelle / high_pr_val - 1)
            
            # Tenkan (9)
            df['Tenkan'] = (df['High'].rolling(window=9).max() + df['Low'].rolling(window=9).min()) / 2
            tenkan_actuel = float(df['Tenkan'].iloc[-1])
            tenkan_pct = (cloture_actuelle / tenkan_actuel - 1)
            
            # SMI
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
            kd_ratio = k_actuel / d_actuel if d_actuel != 0 else np.nan
            kd_diff = k_actuel - d_actuel

            # ADX
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
            st.error(f"Erreur sur le ticker {ticker} (Onglet 4) : {str(e)}")
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

def colorier_volume(val):
    color = '#118d57' if "Supérieur" in str(val) else '#b71d18'
    return f'color: {color}; font-weight: bold'

# --- INTERFACE UTILISATEUR STREAMLIT ---
st.title("📊 Scanner SMI & Breakout")

tab1, tab2, tab3, tab4 = st.tabs([
    "⚡ BREAKOUT MOMENTUM", 
    "🎯 ENTRÉE", 
    "📋 Liste Enregistrée", 
    "📈 Indicateurs Avancés"
])

# --- ONGLET 1 : BREAKOUT MOMENTUM ---
with tab1:
    st.subheader("Analyse Breakout Momentum")
    entree_flash = st.text_area(
        "Entrez des tickers à scanner (ex: TSLA NVDA AMD) :",
        value="TSLA NVDA AMD",
        key="txt_breakout"
    )
    liste_flash = [t.strip().upper() for t in entree_flash.split() if t.strip()]
    
    if st.button("🚀 Lancer le Scan Breakout", key="btn_breakout", use_container_width=True):
        if not liste_flash:
            st.warning("Veuillez saisir au moins un ticker.")
        else:
            with st.spinner("Analyse Breakout Momentum en cours..."):
                df_res_flash = calculer_smi_watchlist(liste_flash)
                if not df_res_flash.empty:
                    colonnes_tab1 = [
                        "ACTIF", "DIFFÉRENCE", "TENDANCE", "Volume hebdo", 
                        "SMI %K (k)", "SMI %D (d)", "HAUT (W)", "BAS (W)", "CLÔTURE"
                    ]
                    df_tab1 = df_res_flash[colonnes_tab1].copy()
                    df_tab1 = df_tab1.sort_values(by="DIFFÉRENCE", ascending=True)
                    df_style_tab1 = (df_tab1.style.format(precision=2)
                                     .map(colorier_diff, subset=['DIFFÉRENCE'])
                                     .map(colorier_tendance, subset=['TENDANCE'])
                                     .map(colorier_volume, subset=['Volume hebdo']))
                    st.dataframe(df_style_tab1, use_container_width=True, hide_index=True)
                else:
                    st.warning("Impossible de générer l'analyse.")

# --- ONGLET 2 : ENTRÉE ---
with tab2:
    st.subheader("Niveaux de Prix d'Entrée")
    entree_ordres = st.text_area(
        "Entrez les tickers pour calculer les ordres d'entrée (ex: TSLA NVDA AMD) :",
        value="TSLA NVDA AMD",
        key="txt_entree"
    )
    liste_ordres = [t.strip().upper() for t in entree_ordres.split() if t.strip()]
    
    if st.button("🎯 Calculer les Ordres d'Entrée", key="btn_entree", use_container_width=True):
        if not liste_ordres:
            st.warning("Veuillez saisir au moins un ticker.")
        else:
            with st.spinner("Calcul des seuils d'entrée (Buy stop + Limite)..."):
                df_entree = calculer_ordres_entree(liste_ordres)
                if not df_entree.empty:
                    df_style_entree = df_entree.style.format({
                        "Prix Max (W)": "{:.2f}",
                        "Buy stop": "{:.2f}",
                        "Limite": "{:.2f}"
                    })
                    st.dataframe(df_style_entree, use_container_width=True, hide_index=True)
                else:
                    st.warning("Aucune donnée générée pour ces critères.")

# --- ONGLET 3 : LISTE ENREGISTRÉE (WATCHLIST) ---
with tab3:
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
                colonnes_tab3 = ["ACTIF", "SMI %K (k)", "SMI %D (d)", "DIFFÉRENCE", "HAUT (W)", "BAS (W)", "CLÔTURE"]
                df_tab3 = df_res[colonnes_tab3].copy()
                df_tab3 = df_tab3.sort_values(by="DIFFÉRENCE", ascending=True)
                df_style3 = df_tab3.style.format(precision=2).map(colorier_diff, subset=['DIFFÉRENCE'])
                st.dataframe(df_style3, use_container_width=True, hide_index=True)
            else:
                st.warning("Aucune donnée n'a pu être récupérée.")

# --- ONGLET 4 : TABLEAU AVANCÉ ---
with tab4:
    st.subheader("Tableau de Synthèse Technique Multi-Indicateurs")
    entree_tab4 = st.text_area(
        "Entrez les tickers à analyser pour le tableau complet :",
        value="TSLA NVDA AMD MU AAPL",
        key="txt_tab4"
    )
    liste_tab4 = [t.strip().upper() for t in entree_tab4.split() if t.strip()]
    
    if st.button("📊 Générer le Tableau Avancé", key="btn_tab4", use_container_width=True):
        if not liste_tab4:
            st.warning("Veuillez saisir au moins un ticker.")
        else:
            with st.spinner("Calcul mathématique des indicateurs complexes..."):
                df_avances = calculer_indicateurs_techniques_avances(liste_tab4)
                if not df_avances.empty:
                    ordre_colonnes = [
                        "ACTIF", "ATR", "Ratio th.", "Close", "High pr", "Ratio", 
                        "Tenkan", "Tenkan %", "%K", "%D", "K/D", "K-D", "ADX14", "ADX7"
                    ]
                    df_final_tab4 = df_avances[ordre_colonnes].copy()
                    
                    df_style_tab4 = df_final_tab4.style.format({
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
                        "ADX7": "{:.2f}"
                    })
                    
                    st.dataframe(df_style_tab4, use_container_width=True, hide_index=True)
                else:
                    st.warning("Aucune donnée disponible pour ces critères.")
