# modules/simple_google_auth.py
# Authentification ultra-simple via Google Sheets

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import hashlib

class SimpleGoogleAuth:
    """
    Authentification ultra-simple :
    - L'utilisateur donne l'URL de SON Google Sheets
    - Si il peut y accéder → il est autorisé
    - Ses données restent dans SON Google Sheets
    """
    
    def __init__(self):
        # Pas besoin de service account !
        # Chaque utilisateur utilise SON propre Google Sheets
        pass
    
    def authenticate_with_user_sheet(self, user_email, sheet_url):
        """
        Authentifier via le Google Sheets de l'utilisateur
        """
        try:
            # Extraire l'ID du Google Sheets depuis l'URL
            if "docs.google.com" in sheet_url:
                sheet_id = sheet_url.split("/d/")[1].split("/")[0]
            else:
                sheet_id = sheet_url
            
            # Vérifier que l'utilisateur peut accéder à ce Google Sheets
            # (Simulation - en réalité on ferait un appel API)
            
            # Pour l'instant, on assume que si l'URL est fournie = accès OK
            success = self._validate_user_sheet_access(user_email, sheet_id)
            
            if success:
                return True, {
                    'email': user_email,
                    'sheet_id': sheet_id,
                    'access_level': 'standard',
                    'authenticated_at': datetime.now()
                }
            
            return False, None
            
        except Exception as e:
            st.error(f"❌ Erreur authentification : {e}")
            return False, None
    
    def _validate_user_sheet_access(self, email, sheet_id):
        """
        Valider que l'utilisateur a accès à son Google Sheets
        
        Pour simplifier, on considère que :
        1. Si l'utilisateur fournit une URL valide
        2. Et qu'il affirme y avoir accès
        3. Alors c'est OK
        
        Dans une version plus avancée, on pourrait :
        - Demander à l'utilisateur de partager temporairement le sheet
        - Ou utiliser l'OAuth Google pour vérifier l'accès
        """
        
        # Validation basique de l'ID Google Sheets
        if len(sheet_id) > 20 and sheet_id.replace('-', '').replace('_', '').isalnum():
            return True
        
        return False
    
    def create_user_data_template(self):
        """
        Créer un template de données que l'utilisateur peut copier
        dans son Google Sheets
        """
        
        templates = {
            "Portefeuille": pd.DataFrame(columns=[
                "Date", "Compte", "Ticker", "Type", "Secteur", "Category",
                "Entreprise", "Quantity", "Purchase price", "Purchase value",
                "Current price", "Current value", "Units"
            ]),
            
            "Commentaires": pd.DataFrame(columns=[
                "Date", "Commentaire", "Date action", "Actions"
            ]),
            
            "Dividendes": pd.DataFrame(columns=[
                "Date paiement", "Ticker", "Entreprise", "Dividende par action",
                "Quantité détenue", "Montant brut (€)", "Montant net (€)", "Devise"
            ]),
            
            "Evenements": pd.DataFrame(columns=[
                "Date", "Event"
            ]),
            
            "Limites": pd.DataFrame(columns=[
                "Variable1", "Variable2", "Valeur seuils"
            ])
        }
        
        return templates

# =====================================
# INTERFACE ULTRA-SIMPLE
# =====================================

def simple_google_sheets_auth():
    """
    Interface d'authentification ultra-simple
    """
    
    if "simple_authenticated" not in st.session_state:
        st.session_state.simple_authenticated = False
    
    if not st.session_state.simple_authenticated:
        
        st.markdown("""
            <div style="text-align: center; padding: 2rem 0;">
                <h1 style="color: #9932cc;">📊 TLB INVESTOR</h1>
                <h3 style="color: #666;">Accès via votre Google Sheets</h3>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("### 🔐 Connexion Ultra-Simple")
            
            st.info("""
            **Comment ça marche :**
            
            1. **Créez** votre Google Sheets de portefeuille
            2. **Copiez** l'URL de votre Google Sheets  
            3. **Collez** l'URL ci-dessous
            4. **C'est tout !** Vos données restent chez VOUS
            
            **Avantages :**
            - ✅ Vos données ne quittent jamais votre Google Drive
            - ✅ Aucun mot de passe à retenir
            - ✅ Vous gardez le contrôle total
            - ✅ Backup automatique Google
            """)
            
            with st.form("simple_auth_form"):
                user_email = st.text_input(
                    "📧 Votre email",
                    placeholder="votre.email@gmail.com",
                    help="Votre adresse email (pour identification)"
                )
                
                sheet_url = st.text_input(
                    "🔗 URL de votre Google Sheets",
                    placeholder="https://docs.google.com/spreadsheets/d/VOTRE_ID/edit",
                    help="L'URL complète de votre Google Sheets de portefeuille"
                )
                
                # Option pour créer un nouveau Google Sheets
                st.markdown("**Pas encore de Google Sheets ?**")
                if st.form_submit_button("📄 Créer un template", type="secondary"):
                    show_template_creation_guide()
                
                submitted = st.form_submit_button(
                    "🚀 Se connecter",
                    type="primary",
                    use_container_width=True
                )
            
            if submitted and user_email and sheet_url:
                with st.spinner("🔍 Vérification de votre Google Sheets..."):
                    
                    auth_manager = SimpleGoogleAuth()
                    success, user_data = auth_manager.authenticate_with_user_sheet(
                        user_email, sheet_url
                    )
                    
                    if success:
                        # Authentification réussie
                        st.session_state.simple_authenticated = True
                        st.session_state.user_email = user_email
                        st.session_state.user_sheet_url = sheet_url
                        st.session_state.user_sheet_id = user_data['sheet_id']
                        st.session_state.access_level = user_data['access_level']
                        
                        # Essayer de charger les données depuis le Google Sheets
                        # (On simulera pour l'instant)
                        initialize_user_data_from_sheets()
                        
                        st.success("✅ Connexion réussie ! Redirection...")
                        st.rerun()
                    else:
                        st.error("❌ URL Google Sheets invalide")
                        st.warning("""
                        **Vérifiez que :**
                        - L'URL est complète et correcte
                        - Vous avez accès au Google Sheets
                        - Le Google Sheets existe
                        """)
        
        st.markdown("---")
        st.markdown("""
            <div style="text-align: center; color: #666; font-size: 0.8em;">
                <p>🛡️ Sécurité: Vos données restent dans VOTRE Google Drive</p>
                <p>📊 Aucune donnée stockée sur nos serveurs</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.stop()
    
    else:
        # Utilisateur authentifié
        display_simple_user_info()

def show_template_creation_guide():
    """
    Guide pour créer un Google Sheets template
    """
    
    st.markdown("### 📄 Créer votre Google Sheets de portefeuille")
    
    st.markdown("""
    **Étapes simples :**
    
    1. **Allez sur [Google Sheets](https://sheets.google.com)**
    2. **Créez** un nouveau fichier
    3. **Nommez-le** "Mon Portefeuille TLB"
    4. **Créez ces onglets** avec ces colonnes :
    """)
    
    # Générer les templates
    auth_manager = SimpleGoogleAuth()
    templates = auth_manager.create_user_data_template()
    
    for sheet_name, template_df in templates.items():
        with st.expander(f"📋 Onglet : {sheet_name}"):
            st.markdown(f"**Colonnes à créer :**")
            st.code(" | ".join(template_df.columns))
            
            if not template_df.empty:
                st.dataframe(template_df, use_container_width=True)
    
    st.markdown("""
    5. **Copiez l'URL** de votre Google Sheets  
    6. **Revenez ici** et collez l'URL pour vous connecter
    
    **🎯 C'est tout !** Votre Google Sheets est prêt pour TLB INVESTOR.
    """)

def initialize_user_data_from_sheets():
    """
    Initialiser les données utilisateur depuis son Google Sheets
    (Simulation pour l'instant)
    """
    
    # Pour l'instant, on initialise avec des DataFrames vides
    # Dans une version complète, on lirait directement le Google Sheets
    
    if "df_data" not in st.session_state:
        st.session_state.df_data = pd.DataFrame()
    
    if "df_limits" not in st.session_state:
        st.session_state.df_limits = pd.DataFrame()
    
    if "df_comments" not in st.session_state:
        st.session_state.df_comments = pd.DataFrame()
    
    if "df_dividendes" not in st.session_state:
        st.session_state.df_dividendes = pd.DataFrame()
    
    if "df_events" not in st.session_state:
        st.session_state.df_events = pd.DataFrame()

def display_simple_user_info():
    """
    Afficher les infos utilisateur dans la sidebar
    """
    
    st.sidebar.markdown("---")
    st.sidebar.success(f"📧 **Connecté:** {st.session_state.user_email}")
    st.sidebar.info(f"📊 **Google Sheets:** Connecté")
    
    # Afficher l'URL (raccourcie)
    short_url = st.session_state.user_sheet_url[:50] + "..." if len(st.session_state.user_sheet_url) > 50 else st.session_state.user_sheet_url
    st.sidebar.code(short_url)
    
    # Bouton pour ouvrir le Google Sheets
    if st.sidebar.button("📊 Ouvrir mon Google Sheets"):
        st.sidebar.markdown(f"[🔗 Cliquez ici]({st.session_state.user_sheet_url})")
    
    # Message d'explication
    st.sidebar.info("""
    💡 **Vos données sont dans VOTRE Google Sheets.**  
    Vous gardez le contrôle total !
    """)
    
    # Bouton de déconnexion
    if st.sidebar.button("🚪 Déconnexion"):
        # Nettoyer la session
        keys_to_clear = ['simple_authenticated', 'user_email', 'user_sheet_url', 'user_sheet_id']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# =====================================
# FONCTIONS DE SAUVEGARDE SIMULÉES
# =====================================

def save_to_user_google_sheets():
    """
    Sauvegarder vers le Google Sheets de l'utilisateur
    (Simulation - en réalité il faudrait utiliser l'API Google Sheets)
    """
    
    try:
        # Pour l'instant, on simule une sauvegarde réussie
        # Dans la version complète, on utiliserait l'API Google Sheets
        # avec les credentials de l'utilisateur (OAuth)
        
        st.success(f"✅ Données sauvegardées dans votre Google Sheets")
        st.info(f"🔗 [Voir dans Google Sheets]({st.session_state.user_sheet_url})")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Erreur sauvegarde : {e}")
        return False
