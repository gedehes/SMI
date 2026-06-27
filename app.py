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
    # Si yfinance retourne un MultiIndex (cas fréquent selon les versions), on extrait le premier niveau
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# --- CALCUL DU SMI & PRIX ---
def calculer_smi_watchlist(ticker_list):
    results = []
    
    for ticker in ticker_list:
        try:
            # Téléchargement en Hebdomadaire (Weekly)
            df = yf.download(ticker, period="3y", interval="1wk", progress=False)
            if df.empty:
                continue
                
            df = aplatir_donnees(df)
            
            # Sécurité pour s'assurer que les colonnes nécessaires existent
            if not all(col in df.columns for col in ['High', 'Low', 'Close']):
                continue
                
            if len(df) < 20: 
                continue

            # --- FORMULE STANDARD DU STOCHASTIC MOMENTUM INDEX (SMI) ---
            # Paramètres classiques : Période 14, Premier lissage 3, Second lissage 3
            période = 14
            df['LL'] = df['Low'].rolling(window=période).min()
            df['HH'] = df['High'].rolling(window=période).max()
            df['HL_Center'] = (df['HH'] + df['LL']) / 2
            
            # Distance du cours par rapport au centre du Range
            df['D'] = df['Close'] - df['HL_Center']
            df['HL_Range'] = df['HH'] - df['LL']
            
            # Double lissage de la distance (D)
            df['D_Smooth1'] = df['D'].ewm(span=3, adjust=False).mean()
            df['D_Smooth2'] = df['D_Smooth1'].ewm(span=3, adjust=False).mean()
            
            # Double lissage du Range (HL_Range)
            df['Range_Smooth1'] = df['HL_Range'].ewm(span=3, adjust=False).mean()
            df['Range_Smooth2'] = df['Range_Smooth1'].ewm(span=3, adjust=False).mean()
            
            # Éviter les divisions par zéro
            df['Range_Smooth2'] = df['Range_Smooth2'].apply(lambda x: x if x != 0 else 0.00001)
            
            # Calcul des lignes %K et %D du SMI
            df['SMI_K'] = 100 * (df['D_Smooth2'] / (0.5 * df['Range_Smooth2']))
            df['SMI_D'] = df['SMI_K'].ewm(span=10, adjust=False).mean()
            df['Diff'] = df['SMI_K'] - df['SMI_D']
            
            # --- EXTRACTION DES DERNIÈRES VALEURS RÉSULTATS ---
            derniere_ligne = df.iloc[-1]
            ligne_precedente = df.iloc[-2]
            
            # Extraction explicite des prix sous forme de float simple
            cloture_actuelle = float(derniere_ligne['Close'])
            haut_actuel = float(derniere_ligne['High'])
            bas_actuel = float(derniere_ligne['Low'])
            
            k_actuel = float(derniere_ligne['SMI_K'])
            d_actuel = float(derniere_ligne['SMI_D'])
            diff_actuelle = float(derniere_ligne['Diff'])
            k_precedent = float(ligne_precedente['SMI_K'])
            
            # Dynamique de tendance de la ligne %K
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
st.title("📊 Scanner SMI Épuré")

tab1, tab2 = st.tabs(["📋 Liste Enregistrée", "⚡ Analyse Flash"])

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
                # On filtre les colonnes demandées pour l'onglet 1
                colonnes_tab1 = ["ACTIF", "SMI %K (k)", "SMI %D (d)", "DIFFÉRENCE", "HAUT (W)", "BAS (W)", "CLÔTURE"]
                df_tab1 = df_res[colonnes_tab1].copy()
                
                # Tri par DIFFÉRENCE croissante
                df_tab1 = df_tab1.sort_values(by="DIFFÉRENCE", ascending=True)
                
                # Application des styles et affichage
                df_style = df_tab1.style.format(precision=2).map(colorier_diff, subset=['DIFFÉRENCE'])
                st.dataframe(df_style, use_container_width=True, hide_index=True)
            else:
                st.warning("Aucune donnée n'a pu être récupérée.")

# --- ONGLET 2 : ANALYSE FLASH ---
with tab2:
    st.subheader("Analyse de Tendance Rapide")
    entree_flash = st.text_area(
        "Entrez des tickers temporaires (ex: TSLA NVDA AMD) :",
        value="TSLA NVDA AMD",
        key="txt_flash"
    )
    liste_flash = [t.strip().upper() for t in entree_flash.split() if t.strip()]
    
    if st.button("🔍 Lancer le Scan Flash", key="btn_flash", use_container_width=True):
        if not liste_flash:
            st.warning("Veuillez saisir au moins un ticker.")
        else:
            with st.spinner("Analyse de la tendance SMI..."):
                df_res_flash = calculer_smi_watchlist(liste_flash)
                if not df_res_flash.empty:
                    # Ajout de la colonne TENDANCE pour l'onglet 2
                    colonnes_tab2 = ["ACTIF", "SMI %K (k)", "SMI %D (d)", "DIFFÉRENCE", "TENDANCE", "HAUT (W)", "BAS (W)", "CLÔTURE"]
                    df_tab2 = df_res_flash[colonnes_tab2].copy()
                    
                    df_tab2 = df_tab2.sort_values(by="DIFFÉRENCE", ascending=True)
                    
                    df_style_flash = (df_tab2.style.format(precision=2)
                
