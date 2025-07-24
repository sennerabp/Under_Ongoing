import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from datetime import datetime
from streamlit_calendar import calendar as st_calendar
import os
import re
import base64
import uuid
import streamlit_authenticator as stauth
from datetime import timedelta
import yaml
from yaml.loader import SafeLoader

import pandas as pd

def save_to_excel():
    """
    Sauvegarde les DataFrames dans un fichier Excel avec gestion d'erreur améliorée
    """
    # CRÉER LE DOSSIER .temp s'il n'existe pas
    os.makedirs(".temp", exist_ok=True)
    
    # Déterminer le nom du fichier de sortie
    if "save_filename" in st.session_state and st.session_state.save_filename:
        save_name = st.session_state.save_filename
    else:
        # TOUJOURS créer avec la date du jour
        today_str = datetime.today().strftime('%Y%m%d')
        save_name = f"donnees_investissements_{today_str}.xlsx"
        st.session_state.save_filename = save_name
    
    # Chemin complet du fichier de sortie
    output_path = os.path.join(".temp", save_name)
    
    try:
        # Vérifier qu'on a au moins des données principales
        if "df_data" not in st.session_state or st.session_state.df_data.empty:
            st.error("❌ Aucune donnée à sauvegarder")
            return False
        
        # INITIALISER les DataFrames vides s'ils n'existent pas
        if "df_limits" not in st.session_state:
            st.session_state.df_limits = pd.DataFrame()
        if "df_comments" not in st.session_state:
            st.session_state.df_comments = pd.DataFrame()
        if "df_dividendes" not in st.session_state:
            st.session_state.df_dividendes = pd.DataFrame()
        if "df_events" not in st.session_state:
            st.session_state.df_events = pd.DataFrame()
        
        # Sauvegarder avec ExcelWriter
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            # Feuille 1 : Données principales (obligatoire)
            st.session_state.df_data.to_excel(writer, sheet_name="Feuil1", index=False)
            
            # Feuille 2 : Limites (optionnel)
            if not st.session_state.df_limits.empty:
                st.session_state.df_limits.to_excel(writer, sheet_name="Feuil2", index=False)
            
            # Feuille 3 : Commentaires (optionnel)
            if not st.session_state.df_comments.empty:
                st.session_state.df_comments.to_excel(writer, sheet_name="Feuil3", index=False)
            
            # Feuille 4 : Dividendes (optionnel)
            if not st.session_state.df_dividendes.empty:
                st.session_state.df_dividendes.to_excel(writer, sheet_name="Feuil4", index=False)
            
            # Feuille 5 : Événements (optionnel)
            if not st.session_state.df_events.empty:
                st.session_state.df_events.to_excel(writer, sheet_name="Feuil5", index=False)
        
        # Stocker le chemin du fichier sauvegardé
        st.session_state["last_saved_path"] = output_path
        
        # Vérifier que le fichier a bien été créé
        if os.path.exists(output_path):
            return True
        else:
            st.error(f"❌ Le fichier n'a pas pu être créé : {output_path}")
            return False
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la sauvegarde : {e}")
        st.error(f"Chemin tenté : {output_path}")
        return False

# --- Constantes ---
CATEGORY_LIST = {
    "Cyclique": ["Consommation cyclique", "Matériaux de base", "Services financiers"],
    "Sensible": ["Services de communication", "Industrie", "Technologie", "Energie"],
    "Défensif": ["Consommation de base", "Santé", "Service aux collectivités"],
    "ETF": ["S&P500", "Euro STOXX50", "NASDAQ 100"]
}

SECTEUR_PAR_TYPE = {
    "ETF": ["ETF"],
    "Actions": ["Cyclique", "Sensible", "Défensif"]
}

SECTOR_COLORS = {
    "Cyclique": "#fdae61", "Sensible": "#abd9e9", "Défensif": "#2c7bb6", "ETF": "#66c2a5",
    "Santé": "#2ECC71", "Consommation de base": "#1ABC9C", "Service aux collectivités": "#117A65",
    "Energie": "#E74C3C", "S&P500": "#7F8C8D", "Euro STOXX50": "#7F8C8D", "NASDAQ 100": "#5D6D7E",
    "Consommation cyclique": "#F1C40F", "Matériaux de base": "#A569BD", "Services financiers": "#5DADE2",
    "Services de communication": "#AF7AC5", "Industrie": "#5499C7", "Technologie": "#48C9B0"
}
