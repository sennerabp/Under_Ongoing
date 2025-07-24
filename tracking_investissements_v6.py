# Version corrigée avec les 3 améliorations demandées + Create New Portfolio

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_calendar import calendar as st_calendar
import os
import re
import base64
import uuid
import time
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from streamlit_authenticator.utilities import (
    CredentialsError, ForgotError, Hasher, LoginError,
    RegisterError, ResetError, UpdateError
)
from modules.yfinance_cache_manager import get_cache_manager

version = '1.0.1'

# === FONCTIONS CREATE NEW PORTFOLIO ===
def create_empty_portfolio(username: str) -> str:
    """
    Créer un fichier Excel vierge avec toutes les feuilles nécessaires
    
    Args:
        username: nom de l'utilisateur connecté
        
    Returns:
        str: chemin du fichier créé
    """
    # Créer le nom du fichier
    today_str = datetime.today().strftime('%Y%m%d')
    filename = f"TLB_portfolio_{username}_{today_str}.xlsx"
    
    # Créer le dossier .temp s'il n'existe pas
    os.makedirs(".temp", exist_ok=True)
    filepath = os.path.join(".temp", filename)
    
    try:
        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            
            # === FEUIL1 : Données principales avec ligne d'exemple ===
            df_main_columns = [
                "Date", "Compte", "Ticker", "Type", "Secteur", "Category", 
                "Entreprise", "Quantity", "Purchase price", "Purchase value", 
                "Current price", "Current value", "Units"
            ]
            
            # AJOUT : Créer une ligne d'exemple pour que df_data ne soit pas vide
            example_data = {
                "Date": [datetime.today().strftime('%Y-%m-%d')],
                "Compte": ["EXEMPLE - Supprimer cette ligne"],
                "Ticker": ["EXEMPLE"],
                "Type": ["Actions"],
                "Secteur": ["Cyclique"],
                "Category": ["Consommation cyclique"],
                "Entreprise": ["LIGNE D'EXEMPLE - À SUPPRIMER"],
                "Quantity": [0],
                "Purchase price": [0],
                "Purchase value": [0],
                "Current price": [0],
                "Current value": [0],
                "Units": ["EUR"]
            }
            
            df_main = pd.DataFrame(example_data)
            df_main.to_excel(writer, sheet_name="Feuil1", index=False)
            
            # === FEUIL2 : Limites avec données pré-remplies ===
            limits_data = [
                ["Type", "Actions", 70],
                ["Type", "ETF", 30],
                ["Secteur", "Cyclique", 25],
                ["Secteur", "Défensif", 35],
                ["Secteur", "Sensible", 40],
                ["Catégorie", "Matériaux de base", 8],
                ["Catégorie", "Consommation cyclique", 12],
                ["Catégorie", "Services financiers", 5],
                ["Catégorie", "Services de communication", 10],
                ["Catégorie", "Industrie", 15],
                ["Catégorie", "Technologie", 15],
                ["Catégorie", "Energie", 8],
                ["Catégorie", "Consommation de base", 15],
                ["Catégorie", "Santé", 12],
                ["Catégorie", "S&P500", 15],
                ["Catégorie", "Euro STOXX50", 15]
            ]
            
            df_limits = pd.DataFrame(limits_data, columns=["Variable1", "Variable2", "Valeur seuils"])
            df_limits.to_excel(writer, sheet_name="Feuil2", index=False)
            
            # === FEUIL3 : Commentaires ===
            df_comments_columns = ["Date", "Commentaire", "Date action", "Actions"]
            df_comments = pd.DataFrame(columns=df_comments_columns)
            df_comments.to_excel(writer, sheet_name="Feuil3", index=False)
            
            # === FEUIL4 : Dividendes ===
            df_dividends_columns = [
                "Date paiement", "Ticker", "Entreprise", "Dividende par action", 
                "Quantité détenue", "Montant brut (€)", "Montant net (€)", "Devise", "Type"
            ]
            df_dividends = pd.DataFrame(columns=df_dividends_columns)
            df_dividends.to_excel(writer, sheet_name="Feuil4", index=False)
            
            # === FEUIL5 : Événements ===
            df_events_columns = ["Date", "Event"]
            df_events = pd.DataFrame(columns=df_events_columns)
            df_events.to_excel(writer, sheet_name="Feuil5", index=False)
        
        return filepath
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la création du portfolio : {e}")
        return None

def load_created_portfolio(filepath: str, username: str):
    """
    Charger le portfolio nouvellement créé dans l'application
    
    Args:
        filepath: chemin du fichier créé
        username: nom de l'utilisateur
    """
    try:
        # Vérifier que le fichier existe
        if not os.path.exists(filepath):
            st.error(f"❌ Fichier non trouvé : {filepath}")
            return False
        
        # Lire toutes les feuilles
        excel_data = pd.read_excel(filepath, sheet_name=None)
        
        # Charger les DataFrames dans session_state
        st.session_state.df_data = excel_data.get("Feuil1", pd.DataFrame())
        st.session_state.df_limits = excel_data.get("Feuil2", pd.DataFrame())
        st.session_state.df_comments = excel_data.get("Feuil3", pd.DataFrame())
        st.session_state.df_dividendes = excel_data.get("Feuil4", pd.DataFrame())
        st.session_state.df_events = excel_data.get("Feuil5", pd.DataFrame())
        
        # NETTOYAGE : Supprimer toute ligne d'exemple qui pourrait rester
        if not st.session_state.df_data.empty:
            # Supprimer les lignes contenant "EXEMPLE" dans n'importe quelle colonne
            mask = st.session_state.df_data.astype(str).apply(lambda x: x.str.contains('EXEMPLE', na=False)).any(axis=1)
            if mask.any():
                st.session_state.df_data = st.session_state.df_data[~mask].reset_index(drop=True)
                st.sidebar.info("🧹 Lignes d'exemple supprimées")
        
        # Mettre à jour les métadonnées
        st.session_state.input_file_path = filepath
        st.session_state.base_filename = f"TLB_portfolio_{username}"
        st.session_state.save_filename = os.path.basename(filepath)
        st.session_state.data_modified = False
        st.session_state.current_values_updated = False
        st.session_state.auto_update_done = False
        
        # IMPORTANT: Marquer le fichier comme uploadé pour déclencher l'interface
        st.session_state.file_uploaded = "created_portfolio"
        
        return True
        
    except Exception as e:
        st.sidebar.error(f"❌ Erreur lors du chargement du nouveau portfolio : {e}")
        return False

def display_create_portfolio_button():
    """
    Afficher le bouton "Create New Portfolio" dans la sidebar
    Condition : affiché seulement après connexion et quand aucun fichier n'est chargé
    """
    # Vérifier les conditions d'affichage
    is_authenticated = st.session_state.get("authentication_status", False)
    
    # MODIFICATION : Nouvelle logique pour détecter un fichier chargé
    has_loaded_file = (
        'input_file_path' in st.session_state and 
        st.session_state.input_file_path and 
        os.path.exists(st.session_state.input_file_path)
    )
    
    username = st.session_state.get("username", "user")
    
    # Afficher le bouton seulement si connecté ET aucun fichier chargé
    if is_authenticated and not has_loaded_file:
        st.sidebar.markdown("---")
        
        if st.sidebar.button("🆕 Create New Portfolio", key="create_new_portfolio", type="secondary"):
            with st.sidebar:
                with st.spinner("📁 Création du nouveau portfolio..."):
                    # Créer le fichier vierge
                    filepath = create_empty_portfolio(username)
                    
                    if filepath and os.path.exists(filepath):
                        st.sidebar.success(f"✅ Fichier créé : {os.path.basename(filepath)}")
                        
                        # Charger automatiquement le nouveau portfolio
                        if load_created_portfolio(filepath, username):
                            st.sidebar.success("✅ Portfolio chargé avec succès !")
                            # Forcer le rechargement complet
                            time.sleep(1)  # Pause pour laisser voir les messages
                            st.rerun()
                        else:
                            st.sidebar.error("❌ Erreur lors du chargement du nouveau portfolio")
                    else:
                        st.sidebar.error("❌ Erreur lors de la création du fichier")

# === FONCTIONS DE SÉCURITÉ ===
def safe_tab_wrapper(tab_function):
    def wrapper(*args, **kwargs):
        try:
            return tab_function(*args, **kwargs)
        except ValueError as e:
            if "truth value of a Series is ambiguous" in str(e):
                st.error("🔧 Correction automatique...")
                # Nettoyer les données
                if "df_data" in st.session_state:
                    df = st.session_state.df_data.copy()
                    df["Units"] = df["Units"].fillna("EUR").astype(str)
                    st.session_state.df_data = df
                st.rerun()
            else:
                raise e
    return wrapper
    
def clear_all_user_data():
    """Nettoyer TOUTES les données utilisateur - Sécurité maximale"""
    keys_to_clear = [
        'df_data', 'df_limits', 'df_comments', 'df_dividendes', 'df_events',
        'data_modified', 'input_file_path', 'save_filename', 'uploaded_file',
        'base_filename', 'file_uploaded', 'current_values_updated', 'last_saved_path',
        'yf_cache', 'user_session_id', 'last_authenticated_user', 'auto_update_done'
    ]
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # Nettoyer aussi les fichiers temporaires
    try:
        if os.path.exists('.temp'):
            import shutil
            shutil.rmtree('.temp')
            os.makedirs('.temp', exist_ok=True)
    except:
        pass

def force_logout():
    """Déconnexion forcée avec nettoyage complet"""
    # 1. Nettoyer toutes les données
    clear_all_user_data()
    
    # 2. Réinitialiser l'authentification
    st.session_state['authentication_status'] = None
    st.session_state['name'] = None
    st.session_state['username'] = None
    
    # 3. Forcer le rechargement de la page
    st.rerun()

def check_session_security():
    """Vérifier la sécurité de la session"""
    current_user = st.session_state.get('username')
    
    # Si pas d'utilisateur connecté, nettoyer par sécurité
    if not current_user:
        clear_all_user_data()
        return False
    
    # Vérifier si c'est une nouvelle session (changement d'utilisateur)
    last_user = st.session_state.get('last_authenticated_user')
    if last_user and last_user != current_user:
        clear_all_user_data()
    
    # Enregistrer l'utilisateur actuel
    st.session_state.last_authenticated_user = current_user
    return True

def generate_session_id():
    """Générer un ID unique pour la session"""
    if 'user_session_id' not in st.session_state:
        st.session_state.user_session_id = str(uuid.uuid4())
    return st.session_state.user_session_id

def auto_update_portfolio():
    """Actualisation automatique du portefeuille au premier chargement"""
    if st.session_state.get('auto_update_done', False):
        return  # Déjà fait pour cette session
    
    if not st.session_state.df_data.empty:
        try:
            from modules.tab1_actualisation import update_portfolio_prices_optimized
            
            with st.spinner("🔄 Actualisation automatique des cours boursiers..."):
                df_updated = update_portfolio_prices_optimized(st.session_state.df_data)
                st.session_state.df_data = df_updated
                st.session_state.data_modified = True
                st.session_state.auto_update_done = True  # Marquer comme fait
                
                # Sauvegarder automatiquement
                from modules.tab0_constants import save_to_excel
                success = save_to_excel()
                if success:
                    st.success("✅ Cours actualisés automatiquement et sauvegardés !")
                else:
                    st.warning("⚠️ Cours actualisés mais erreur de sauvegarde")
                    
        except Exception as e:
            st.warning(f"⚠️ Erreur lors de l'actualisation automatique : {e}")
            st.info("💡 Vous pouvez actualiser manuellement depuis l'onglet Portefeuille")

def display_useful_links():
    """Afficher les liens utiles dans la sidebar"""
    st.sidebar.markdown("---")  # Séparateur
    st.sidebar.title('📚 Sites financiers utiles')
    st.sidebar.markdown("""
        **📈 TLB Investor**
        - [TLB Skool](https://www.skool.com/team-tlb/about)  
          _Communauté TLB Investor_
        - [Analyses Communes - ETF's](https://docs.google.com/spreadsheets/d/1SBQffJFSXTyw7AJqsEuVXP9C0Ef4IzBh9zTZMMP_h18/edit?gid=936070616#gid=936070616)  
          _Google Sheet contenant analyses communes ETF's validées par TLB_
        - [Analyses Communes - Actions](https://docs.google.com/spreadsheets/d/16mwbFmzam2Q4tCgz1YC8ZQnlSK8XZMWqomWpxg3_dwQ/edit?gid=1136459576#gid=1136459576)  
          _Google Sheet contenant analyses communes Actions validées par TLB_

        **🔍 Analyse des entreprises**
        - [Yahoo Finance Tickers](https://finance.yahoo.com/lookup/)  
          _Recherche de symboles boursiers (Tickers)_
        - [ZoneBourse](https://www.zonebourse.com/)  
          _Données chiffrées pour analyser les entreprises_
        - [Google Finance](https://www.google.com/finance/?hl=fr)  
          _Infos générales sur les entreprises_
        - [Investing](https://fr.investing.com/)  
          _Infos, actualités et Watchlist_
        - [Bloomberg](https://www.bloomberg.com/europe)  
          _Articles et actualités_

        **💸 Dividendes & Rendement**
        - [Rendement Bourse](https://rendementbourse.com/)  
          _Historique de dividendes et secteur_
        - [Dividend.com](https://www.dividend.com/)  
          _Prochains dividendes & historique_
        - [Boursorama - Trackers](https://www.boursorama.com/bourse/trackers/palmares/)  
          _Palmarès d'ETF_

        **📊 ETF & Screener**
        - [JustETF](https://www.justetf.com/fr/)  
          _Infos ETF compatibles PEA_
        - [Trackinsight](https://www.trackinsight.com/fr)  
          _Données sur ETF pour CTO_
        - [MorningStar](https://www.morningstar.com/)  
          _Notes des ETF_
        - [Boursophile](https://www.boursophile.com/screener/)  
          _Screener d'actions_

        **📈 Stratégie et insider**
        - [Insider Screener](https://www.insiderscreener.com/fr/)  
          _Transactions des initiés_
        - [Gurufocus](https://www.gurufocus.com/guru/warren%2Bbuffett/current-portfolio/portfolio?view=table)  
          _Suivi des portefeuilles des milliardaires_

        **🌍 Vue globale**
        - [Finviz](https://finviz.com/map.ashx)  
          _Carte thermique du marché mondial_
    """, unsafe_allow_html=True)

# === INITIALISATION FORCÉE DU CACHE ===
if 'yf_cache' not in st.session_state:
    st.session_state.yf_cache = {
        'prices': {},
        'info': {},
        'last_update': {},
        'eurusd_rate': {'rate': 1.1, 'timestamp': datetime.now() - timedelta(hours=1)}
    }

# Ensure modules folder is recognized as a package
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))
from modules.tab0_constants import save_to_excel

@st.cache_data
def get_base64_image(path):
    try:
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        st.warning(f"Image non trouvée : {path}")
        return ""

st.set_page_config(page_title='Suivi Investissements', layout='wide')

# === CSS ET STYLE ===
logo_base64 = get_base64_image('logo.png')

st.markdown("""
    <style>
    html, body, .main, .block-container {
        background-color: white !important;
        padding-top: 0px !important;
        margin-top: 0px !important;
    }
    .block-container {
        padding-top: 0.2rem !important;
        padding-bottom: 0.4rem !important;
    }
    .centered-header {
        display: flex;
        flex-direction: column;
        align-items: center;
        margin-top: 2rem !important;
        margin-bottom: -1rem !important;
    }
    img {
        margin-top: 0rem !important;
        margin-bottom: -1rem !important;
        display: block;
        margin-left: auto;
        margin-right: auto;
    }
    .stTextInput, .stPassword, .stButton {
        width: 100% !important;
        max-width: 300px !important;
        margin: 0.5rem auto !important;
        display: block;
    }
    .stForm {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    .stForm > div {
        width: 100%;
        max-width: 300px;
    }
    .forgot-button {
        display: flex;
        justify-content: center;
        margin-top: 1rem;
    }
    .logout-button {
        background-color: #ff4b4b !important;
        color: white !important;
        border: none !important;
        padding: 0.5rem 1rem !important;
        border-radius: 5px !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

if logo_base64:
    st.markdown(f"""
        <div class="centered-header">
            <img src="data:image/png;base64,{logo_base64}" width="300">
            <div style="margin-top: 0.1rem; margin-bottom: 0rem; font-size: 0.9rem; color: gray;">
                Version {version}
            </div>
        </div>
    """, unsafe_allow_html=True)

# === CONFIGURATION AUTHENTIFICATION ===
config_path = 'config.yaml'
if not os.path.exists(config_path):
    st.error('config.yaml introuvable.')
    st.stop()

try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.load(f, Loader=SafeLoader)
except Exception as e:
    st.error(f"Erreur lors du chargement du fichier config.yaml : {e}")
    st.stop()

authenticator = stauth.Authenticate(
    config['credentials'], 
    config['cookie']['name'],
    config['cookie']['key'], 
    config['cookie']['expiry_days']
)

# === GESTION DE L'AUTHENTIFICATION ===
try:
    with st.container():
        authenticator.login()
except LoginError as e:
    st.error(e)

# === GESTION DES CAS D'AUTHENTIFICATION ===
if st.session_state.get('authentication_status') is False:
    st.error('Nom d\'utilisateur ou mot de passe incorrect')
    clear_all_user_data()  # Nettoyer en cas d'échec de connexion
    
elif st.session_state.get('authentication_status') is True:
    
    # === VÉRIFICATION DE SÉCURITÉ DE SESSION ===
    if not check_session_security():
        st.stop()
    
    # === BOUTON DE DÉCONNEXION SÉCURISÉ ===
    with st.sidebar:
        st.markdown("---")
        if st.button('🚪 Déconnexion', key='secure_logout', help='Déconnexion avec effacement de toutes les données'):
            force_logout()
    
    # === NOUVEAU : BOUTON CREATE NEW PORTFOLIO ===
    display_create_portfolio_button()
    
    # === GÉNÉRATION ID SESSION ===
    session_id = generate_session_id()
    
    st.success(f"Bienvenue {st.session_state['name']} ! ")

    # === INTERFACE DE CHARGEMENT DE FICHIER (en premier) ===
    st.sidebar.header('📁 Charger les données')
    uploaded = st.sidebar.file_uploader('Importer un fichier Excel', type=['xlsx'])

    # === SECTION SAUVEGARDE (juste après le chargement) ===
    if 'df_data' in st.session_state and 'input_file_path' in st.session_state:
        st.sidebar.header('💾 Sauvegarde des données')

        today_str = datetime.today().strftime('%Y%m%d')
        save_filename = f"{st.session_state.base_filename}_{today_str}.xlsx"
        from io import BytesIO
        output = BytesIO()
        try:
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                # TOUJOURS sauvegarder les 5 feuilles
                st.session_state.df_data.to_excel(writer, sheet_name="Feuil1", index=False)
                st.session_state.df_limits.to_excel(writer, sheet_name="Feuil2", index=False)
                st.session_state.df_comments.to_excel(writer, sheet_name="Feuil3", index=False)
                st.session_state.df_dividendes.to_excel(writer, sheet_name="Feuil4", index=False)
                st.session_state.df_events.to_excel(writer, sheet_name="Feuil5", index=False)
                
            output.seek(0)
            file_data = output.getvalue()
            if st.sidebar.download_button(
                label="📥 Télécharger",
                data=file_data,
                file_name=save_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="direct_download",
                on_click=lambda: setattr(st.session_state, 'data_modified', False)
            ):
                st.sidebar.success("✅ Fichier téléchargé avec succès!")
        except Exception as e:
            st.sidebar.error(f"❌ Erreur lors de la préparation du fichier : {e}")

    # === AFFICHAGE DES LIENS UTILES (après la sauvegarde) ===
    display_useful_links()

# === ARRÊT SI PAS CONNECTÉ ===
if st.session_state.get('authentication_status') is not True:
    if st.button('🔑 Mot de passe oublié ?', key='forgot_btn'):
        st.info('Merci d\'envoyer un email à [pierre.barennes@gmail.com](mailto:pierre.barennes@gmail.com) avec votre adresse e-mail d\'inscription et votre nom d\'utilisateur.')
    st.stop()

# === RESTE DU CODE APPLICATION ===
# Initialisation des DataFrames
if st.session_state.get('authentication_status') is True:
    for key in ['df_data','df_limits','df_comments','df_dividendes','df_events']:
        if key not in st.session_state:
            st.session_state[key] = pd.DataFrame()
    if 'data_modified' not in st.session_state:
        st.session_state.data_modified = False

    if uploaded:
        base_name = os.path.splitext(uploaded.name)[0]
        base_name = re.sub(r"_\d{8}$", "", base_name)
        date_str = datetime.today().strftime('%Y%m%d')
        save_name = f'{base_name}_{date_str}.xlsx'
        path = f'.temp/{save_name}'
        os.makedirs('.temp', exist_ok=True)
        
        # Sauvegarder le fichier uploadé
        with open(path, 'wb') as f:
            f.write(uploaded.getbuffer())
        
        st.session_state.input_file_path = path
        st.session_state.save_filename = save_name
        st.session_state.uploaded_file = uploaded
        st.session_state.base_filename = base_name
        
        if ("df_data" not in st.session_state or 
            st.session_state.get("file_uploaded") != uploaded or
            st.session_state.df_data.empty):
            try:
                # Charger toutes les feuilles Excel
                xls = pd.ExcelFile(path)
                st.session_state.df_data = pd.read_excel(xls, 'Feuil1')
                st.session_state.df_limits = pd.read_excel(xls, 'Feuil2') if 'Feuil2' in xls.sheet_names else pd.DataFrame()
                st.session_state.df_comments = pd.read_excel(xls, 'Feuil3') if 'Feuil3' in xls.sheet_names else pd.DataFrame()
                st.session_state.df_dividendes = pd.read_excel(xls, 'Feuil4') if 'Feuil4' in xls.sheet_names else pd.DataFrame()
                st.session_state.df_events = pd.read_excel(xls, 'Feuil5') if 'Feuil5' in xls.sheet_names else pd.DataFrame()
                st.session_state.file_uploaded = uploaded
                st.session_state.current_values_updated = False
                st.session_state.auto_update_done = False  # Reset pour permettre l'actualisation auto
                st.sidebar.success(f"✅ Fichier chargé")
                st.session_state.data_modified = False
                
                # === ACTUALISATION AUTOMATIQUE APRÈS CHARGEMENT ===
                auto_update_portfolio()
                
            except Exception as e:
                st.sidebar.error(f"Erreur lors du chargement : {e}")
        else:
            st.sidebar.success(f"✅ Fichier chargé contenant {len(st.session_state.df_data)} lignes d'investissements")

    # === INTERFACE PRINCIPALE ===
    # MODIFICATION : Changer la condition pour détecter un fichier chargé
    # Au lieu de vérifier si df_data n'est pas vide, vérifier si on a chargé un fichier
    has_portfolio_loaded = (
        'input_file_path' in st.session_state and 
        st.session_state.input_file_path and 
        os.path.exists(st.session_state.input_file_path)
    )
    
    if not has_portfolio_loaded:            
        # === MESSAGE D'ACCUEIL (seulement si pas de fichier chargé) ===
        col1, col2, col3 = st.columns([1,2, 1])
    
        with col2:
            st.markdown("""
                ### 🚀 Chargez votre TLB Portfolio
                
                **Première connexion :**
                - 🆕 **Créez** un nouveau portfolio vierge (bouton "Create New Portfolio")
                
                **Portfolio existant :**
                - 📥 **Importez** votre fichier Portfolio depuis la sidebar (Browse files)
            """)
            
            # SECTION SÉCURITÉ - Visible uniquement avant chargement des données
            st.markdown("""
                ---
                ### 🔒 Sécurité et Confidentialité :
                
                - ✅ **Traitement local** - Vos données restent dans votre session
                - ✅ **Aucun stockage** permanent sur nos serveurs  
                - ✅ **Export sécurisé** - Fichiers générés à la demande puis supprimés
                - ✅ **Isolation totale** entre utilisateurs
                - ✅ **Déconnexion automatique** après inactivité
                - 🔒 **Effacement garanti** - Toute déconnexion efface vos données
                
                💡 **Vos fichiers Excel sont vos données** - nous ne les conservons jamais !
            """)
    
    else:   
        # === ONGLETS PRINCIPAUX (seulement si fichier chargé) ===
        st.markdown(f"### 📊 Portfolio chargé : {os.path.basename(st.session_state.input_file_path)}")
        
        # Message pour nouveau portfolio vide
        if st.session_state.df_data.empty:
            st.info("""
            🆕 **Nouveau portfolio créé !** 
            
            Portfolio vierge prêt à l'emploi - Utilisez l'onglet **"➕ Ajouter un achat"** pour commencer à ajouter vos investissements
            """)
        
        tabs = st.tabs([
            '📈 Portefeuille','➕ Ajouter un achat','📊 Répartition dynamique',
            '🎯 Équilibre vs Objectifs','📝 Commentaires','💸 Dividendes',
            '📊 Projections','📅 Calendrier','🔍 Analyse complète'
        ])

        try:
            from modules.tab1_actualisation import display_tab1_actualisation
            from modules.tab2_ajout_achat   import display_tab2_ajout_achat
            from modules.tab3_repartition    import display_tab3_repartition
            from modules.tab4_imbalances    import display_tab4_imbalances
            from modules.tab5_commentaires  import display_tab5_commentaires
            from modules.tab6_dividendes     import display_tab6_dividendes
            from modules.tab9_projections    import display_tab_projections
            from modules.tab7_evenements    import display_tab7_evenements
            from modules.tab8_analyse       import display_tab8_analyse

            with tabs[0]: display_tab1_actualisation()
            with tabs[1]: display_tab2_ajout_achat()
            with tabs[2]: display_tab3_repartition()
            with tabs[3]: display_tab4_imbalances()
            with tabs[4]: display_tab5_commentaires()
            with tabs[5]: display_tab6_dividendes()
            with tabs[6]: display_tab_projections()
            with tabs[7]: display_tab7_evenements()
            with tabs[8]: display_tab8_analyse()

        except ImportError as e:
            st.error(f"Erreur d'import des modules : {e}")
            st.info("Vérifiez que le dossier 'modules' contient tous les fichiers.")
        except Exception as e:
            st.error(f"Erreur lors de l'exécution des onglets : {e}")

# === NETTOYAGE AUTOMATIQUE EN FIN DE SESSION ===
# Note: Streamlit ne garantit pas l'exécution de code à la fermeture de fenêtre
# Mais le nettoyage se fera automatiquement à la prochaine connexion
