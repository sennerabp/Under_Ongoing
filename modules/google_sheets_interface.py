# modules/google_sheets_interface.py
"""
Interface Streamlit pour l'intégration Google Sheets OAuth2
"""

import streamlit as st
import os
from datetime import datetime
from typing import Dict, Optional
from .google_sheets_oauth_manager import TLBGoogleSheetsOAuthManager

class TLBGoogleSheetsInterface:
    """
    Interface utilisateur pour Google Sheets OAuth2
    """
    
    def __init__(self):
        self.manager = TLBGoogleSheetsOAuthManager()
        self._load_oauth_config()
    
    def _load_oauth_config(self) -> bool:
        """
        Charger la configuration OAuth2 depuis les secrets Streamlit
        """
        try:
            # Configuration OAuth2 - À ajouter dans secrets.toml
            client_config = {
                "web": {
                    "client_id": st.secrets.get("GOOGLE_CLIENT_ID"),
                    "client_secret": st.secrets.get("GOOGLE_CLIENT_SECRET"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uri": st.secrets.get("GOOGLE_REDIRECT_URI", "urn:ietf:wg:oauth:2.0:oob")
                }
            }
            
            # Vérifier que les secrets sont configurés
            if not client_config["web"]["client_id"] or not client_config["web"]["client_secret"]:
                st.error("❌ Configuration Google OAuth2 manquante dans secrets.toml")
                st.info("""
                **Configuration requise dans .streamlit/secrets.toml :**
                ```toml
                GOOGLE_CLIENT_ID = "327885215877-8f30ie53tnh9fncrrr4uf9k8orf9vl5v.apps.googleusercontent.com"
                GOOGLE_CLIENT_SECRET = "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"
                GOOGLE_REDIRECT_URI = "https://trackinginvestissementsv6py-7vgkqtycr4geqctogpryqc.streamlit.app/"
                ```
                """)
                return False
            
            return self.manager.setup_oauth_credentials(client_config["web"])
            
        except Exception as e:
            st.error(f"❌ Erreur configuration OAuth2: {e}")
            return False
    
    def display_authentication_interface(self) -> bool:
        """
        Afficher l'interface d'authentification Google
        
        Returns:
            bool: True si authentifié
        """
        cache = st.session_state.tlb_gs_cache
        
        # Si déjà authentifié, afficher le status
        if cache['authenticated']:
            self._display_authenticated_status()
            return True
        
        # Interface d'authentification
        st.markdown("### 🔐 Authentification Google Sheets")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info("""
            **Accès à vos Google Sheets privés :**
            
            1. **Cliquez** sur "S'authentifier avec Google"
            2. **Autorisez** l'accès à vos Google Sheets
            3. **Copiez** le code d'autorisation
            4. **Collez** le code ci-dessous
            
            🔒 **Sécurité garantie :** Vos données restent dans VOS Google Sheets privés
            """)
        
        with col2:
            # Bouton d'authentification
            if st.button("🔐 S'authentifier avec Google", key="main_google_auth_btn", type="primary"):
                success, message = self.manager.authenticate_user()
                
                if success:
                    st.success("✅ " + message)
                    st.rerun()
                else:
                    # Afficher l'URL d'authentification
                    if "Veuillez vous authentifier:" in message:
                        auth_url = message.split(": ", 1)[1]
                        st.markdown(f"**🔗 [Cliquez ici pour vous authentifier]({auth_url})**")
                        
                        # Zone de saisie du code
                        auth_code = st.text_input(
                            "Code d'autorisation",
                            placeholder="Collez le code d'autorisation Google ici",
                            help="Après autorisation, Google affichera un code à copier-coller ici"
                        )
                        
                        if auth_code:
                            st.session_state['google_auth_code'] = auth_code
                            st.rerun()
                    else:
                        st.error("❌ " + message)
        
        return False
    
    def _display_authenticated_status(self):
        """Afficher le statut authentifié"""
        cache = st.session_state.tlb_gs_cache
        user_profile = cache.get('user_profile', {})
        
        st.success(f"✅ Connecté à Google Sheets en tant que {user_profile.get('email', 'Utilisateur')}")
    
    def display_sheets_selector(self) -> Optional[str]:
        """
        Afficher le sélecteur de Google Sheets
        
        Returns:
            str: ID du sheet sélectionné ou None
        """
        if not st.session_state.tlb_gs_cache['authenticated']:
            return None
        
        st.markdown("### 📊 Sélection du Google Sheet")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Bouton pour rafraîchir la liste
            if st.button("🔄 Actualiser la liste", key="refresh_sheets"):
                self.manager.clear_cache('user_spreadsheets')
                st.rerun()
            
            # Récupérer la liste des spreadsheets
            with st.spinner("📋 Chargement de vos Google Sheets..."):
                spreadsheets = self.manager.list_user_spreadsheets()
            
            if not spreadsheets:
                st.warning("⚠️ Aucun Google Sheet trouvé dans votre Google Drive")
                st.info("💡 Créez un nouveau Google Sheet ou vérifiez vos permissions")
                return None
            
            # Sélecteur de spreadsheet
            sheet_options = {sheet['id']: sheet['display_name'] for sheet in spreadsheets}
            
            selected_sheet_id = st.selectbox(
                "Choisir votre Google Sheet TLB:",
                options=list(sheet_options.keys()),
                format_func=lambda x: sheet_options[x],
                index=0,
                key="selected_sheet_selector"
            )
            
            # Afficher les détails du sheet sélectionné
            selected_sheet = next((s for s in spreadsheets if s['id'] == selected_sheet_id), None)
            if selected_sheet:
                st.info(f"""
                **Sheet sélectionné :** {selected_sheet['name']}
                **Dernière modification :** {selected_sheet['modified'][:16] if selected_sheet['modified'] else 'Inconnue'}
                **ID :** {selected_sheet['id'][:20]}...
                """)
        
        with col2:
            # Bouton pour ouvrir le sheet dans un nouvel onglet
            if selected_sheet:
                st.markdown(f"[📊 Ouvrir dans Google Sheets]({selected_sheet['url']})")
        
        return selected_sheet_id
    
    def display_data_loader(self, sheet_id: str) -> bool:
        """
        Afficher l'interface de chargement des données
        
        Args:
            sheet_id: ID du Google Sheet
            
        Returns:
            bool: True si chargement réussi
        """
        if not sheet_id:
            return False
        
        st.markdown("### 📥 Chargement des données")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if st.button("📊 Charger le Portfolio", key="load_portfolio", type="primary"):
                with st.spinner("📊 Chargement du portfolio depuis Google Sheets..."):
                    success, result = self.manager.load_portfolio_data(sheet_id)
                    
                    if success:
                        # Charger les données dans session_state
                        st.session_state.df_data = result['df_data']
                        st.session_state.df_limits = result['df_limits'] 
                        st.session_state.df_comments = result['df_comments']
                        st.session_state.df_dividendes = result['df_dividendes']
                        st.session_state.df_events = result['df_events']
                        
                        # Métadonnées pour le système TLB
                        st.session_state.input_file_path = f"google_sheets_{sheet_id}"
                        st.session_state.base_filename = f"TLB_GoogleSheets_{datetime.now().strftime('%Y%m%d')}"
                        st.session_state.save_filename = f"{st.session_state.base_filename}.xlsx"
                        st.session_state.data_modified = False
                        st.session_state.current_values_updated = False
                        st.session_state.auto_update_done = False
                        st.session_state.file_uploaded = "google_sheets_oauth"
                        
                        st.success(f"✅ Portfolio chargé ! {len(st.session_state.df_data)} investissements trouvés")
                        
                        # Auto-actualisation des cours
                        self._auto_update_prices()
                        
                        return True
                    else:
                        st.error(f"❌ {result}")
                        return False
        
        with col2:
            # Force refresh
            if st.button("🔄 Forcer le rechargement", key="force_reload"):
                with st.spinner("🔄 Rechargement forcé..."):
                    success, result = self.manager.load_portfolio_data(sheet_id, force_refresh=True)
                    if success:
                        st.success("✅ Données rechargées")
                        st.rerun()
                    else:
                        st.error(f"❌ {result}")
        
        with col3:
            # Statistiques du cache
            cache_stats = self.manager.get_cache_stats()
            st.metric("Cache", f"{cache_stats['cached_items']} items")
        
        return False
    
    def _auto_update_prices(self):
        """Auto-actualisation des cours après chargement Google Sheets"""
        try:
            from .tab1_actualisation import update_portfolio_prices_optimized
            from .tab0_constants import save_to_excel
            
            with st.spinner("🔄 Actualisation automatique des cours..."):
                df_updated = update_portfolio_prices_optimized(st.session_state.df_data)
                st.session_state.df_data = df_updated
                st.session_state.data_modified = True
                st.session_state.auto_update_done = True
                
                # Sauvegarder en local
                success = save_to_excel()
                if success:
                    st.success("✅ Cours actualisés et sauvegardés localement !")
                else:
                    st.warning("⚠️ Cours actualisés mais erreur sauvegarde locale")
                    
        except Exception as e:
            st.warning(f"⚠️ Erreur actualisation automatique : {e}")
    
    def display_save_interface(self) -> bool:
        """
        Afficher l'interface de sauvegarde vers Google Sheets
        
        Returns:
            bool: True si sauvegarde réussie
        """
        cache = st.session_state.tlb_gs_cache
        
        if not cache['authenticated'] or not cache.get('selected_sheet_id'):
            return False
        
        # Vérifier qu'on a des données à sauvegarder
        if not hasattr(st.session_state, 'df_data') or st.session_state.df_data.empty:
            return False
        
        st.markdown("### 💾 Sauvegarde vers Google Sheets")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Indicateur de modifications
            has_modifications = st.session_state.get('data_modified', False)
            
            if has_modifications:
                st.warning("⚠️ Données modifiées non sauvegardées vers Google Sheets")
            else:
                st.success("✅ Données synchronisées avec Google Sheets")
            
            # Bouton de sauvegarde
            if st.button("💾 Sauvegarder vers Google Sheets", 
                        key="save_to_gs", 
                        type="primary" if has_modifications else "secondary"):
                
                with st.spinner("💾 Sauvegarde vers Google Sheets..."):
                    # Préparer les données
                    portfolio_data = {
                        'df_data': st.session_state.df_data,
                        'df_limits': st.session_state.df_limits,
                        'df_comments': st.session_state.df_comments, 
                        'df_dividendes': st.session_state.df_dividendes,
                        'df_events': st.session_state.df_events
                    }
                    
                    # Sauvegarder
                    success, message = self.manager.save_portfolio_data(
                        portfolio_data, 
                        cache['selected_sheet_id']
                    )
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.session_state.data_modified = False
                        return True
                    else:
                        st.error(f"❌ {message}")
                        return False
        
        with col2:
            # Lien vers le Google Sheet
            sheet_id = cache.get('selected_sheet_id')
            if sheet_id:
                sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
                st.markdown(f"[📊 Ouvrir Google Sheet]({sheet_url})")
        
        return False
    
    def display_sidebar_integration(self):
        """
        Afficher l'intégration Google Sheets dans la sidebar
        (Remplace ou complète l'interface de chargement Excel)
        """
        # Vérifier les prérequis d'authentification TLB
        is_authenticated = st.session_state.get("authentication_status", False)
        is_2fa_verified = st.session_state.get("tlb_2fa_verified", False)
        
        if not (is_authenticated and is_2fa_verified):
            return
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📊 Google Sheets")
        
        # Étape 1: Authentification Google
        if not st.session_state.tlb_gs_cache['authenticated']:
            st.sidebar.markdown("**🔐 Étape 1: Authentification**")
            
            if st.sidebar.button("🔐 Se connecter à Google", key="sidebar_google_auth_btn"):
                # Rediriger vers l'interface principale
                st.session_state['show_google_auth'] = True
                st.info("👆 Utilisez l'interface principale pour vous authentifier à Google")
                return
        
        else:
            # Étape 2: Sélection et chargement
            st.sidebar.markdown("**📋 Étape 2: Sélection du Sheet**")
            
            user_email = st.session_state.tlb_gs_cache.get('user_profile', {}).get('email', 'Utilisateur')
            st.sidebar.success(f"✅ Connecté: {user_email}")
            
            # Mini sélecteur de sheets
            try:
                spreadsheets = self.manager.list_user_spreadsheets()
                
                if spreadsheets:
                    # Sélecteur compact
                    sheet_options = {sheet['id']: sheet['name'] for sheet in spreadsheets}
                    
                    selected_sheet_id = st.sidebar.selectbox(
                        "Google Sheet:",
                        options=list(sheet_options.keys()),
                        format_func=lambda x: sheet_options[x][:30] + "..." if len(sheet_options[x]) > 30 else sheet_options[x],
                        key="sidebar_sheet_selector"
                    )
                    
                    # Bouton de chargement compact
                    if st.sidebar.button("📥 Charger Portfolio", key="sidebar_load_gs", type="primary"):
                        with st.spinner("📊 Chargement..."):
                            success, result = self.manager.load_portfolio_data(selected_sheet_id)
                            
                            if success:
                                # Charger dans session_state
                                st.session_state.df_data = result['df_data']
                                st.session_state.df_limits = result['df_limits']
                                st.session_state.df_comments = result['df_comments']
                                st.session_state.df_dividendes = result['df_dividendes']
                                st.session_state.df_events = result['df_events']
                                
                                # Métadonnées
                                st.session_state.input_file_path = f"google_sheets_{selected_sheet_id}"
                                st.session_state.base_filename = f"TLB_GoogleSheets_{datetime.now().strftime('%Y%m%d')}"
                                st.session_state.file_uploaded = "google_sheets_oauth"
                                st.session_state.data_modified = False
                                
                                st.sidebar.success(f"✅ {len(st.session_state.df_data)} investissements chargés")
                                
                                # Auto-actualisation
                                self._auto_update_prices()
                                st.rerun()
                            else:
                                st.sidebar.error(f"❌ {result}")
                
                else:
                    st.sidebar.warning("⚠️ Aucun Google Sheet trouvé")
                    
            except Exception as e:
                st.sidebar.error(f"❌ Erreur: {e}")
            
            # Étape 3: Sauvegarde (si données chargées)
            if (hasattr(st.session_state, 'df_data') and 
                not st.session_state.df_data.empty and
                st.session_state.get('file_uploaded') == "google_sheets_oauth"):
                
                st.sidebar.markdown("**💾 Étape 3: Sauvegarde**")
                
                # Indicateur de modifications
                has_modifications = st.session_state.get('data_modified', False)
                
                if has_modifications:
                    st.sidebar.warning("⚠️ Modifié")
                else:
                    st.sidebar.success("✅ Synchronisé")
                
                # Bouton sauvegarde
                if st.sidebar.button("💾 Sync → Google Sheets", 
                                   key="sidebar_save_gs",
                                   type="primary" if has_modifications else "secondary"):
                    
                    portfolio_data = {
                        'df_data': st.session_state.df_data,
                        'df_limits': st.session_state.df_limits,
                        'df_comments': st.session_state.df_comments,
                        'df_dividendes': st.session_state.df_dividendes,
                        'df_events': st.session_state.df_events
                    }
                    
                    success, message = self.manager.save_portfolio_data(
                        portfolio_data,
                        st.session_state.tlb_gs_cache.get('selected_sheet_id')
                    )
                    
                    if success:
                        st.sidebar.success("✅ Sauvegardé")
                        st.session_state.data_modified = False
                        st.rerun()
                    else:
                        st.sidebar.error("❌ Erreur")
            
            # Bouton déconnexion
            st.sidebar.markdown("---")
            if st.sidebar.button("🚪 Déconnecter Google", key="disconnect_google"):
                self.manager.disconnect()
                st.sidebar.success("✅ Déconnecté de Google")
                st.rerun()
    
    def display_main_interface(self):
        """
        Afficher l'interface principale Google Sheets
        (À utiliser dans le contenu principal si pas de fichier chargé)
        """
        # Vérifier si on doit afficher l'interface Google Sheets
        show_google_auth = st.session_state.get('show_google_auth', False)
        
        if show_google_auth:
            st.markdown("## 🔐 Authentification Google Sheets")
            
            # Interface d'authentification
            authenticated = self.display_authentication_interface()
            
            if authenticated:
                # Interface de sélection et chargement
                st.markdown("---")
                selected_sheet_id = self.display_sheets_selector()
                
                if selected_sheet_id:
                    st.markdown("---")
                    success = self.display_data_loader(selected_sheet_id)
                    
                    if success:
                        # Rediriger vers l'application principale
                        st.session_state['show_google_auth'] = False
                        st.success("🎉 Portfolio chargé avec succès ! Redirection...")
                        st.rerun()
            
            # Bouton retour
            if st.button("🔙 Retour", key="back_from_google_auth"):
                st.session_state['show_google_auth'] = False
                st.rerun()
    
    def display_debug_info(self):
        """Afficher les informations de debug (développement)"""
        if st.sidebar.checkbox("🔧 Debug Google Sheets", key="debug_gs"):
            cache_stats = self.manager.get_cache_stats()
            
            st.sidebar.markdown("**📊 Statistiques:**")
            st.sidebar.json(cache_stats)
            
            if st.sidebar.button("🗑️ Vider cache", key="clear_gs_cache"):
                self.manager.clear_cache()
                st.sidebar.success("Cache vidé")


# Fonction d'intégration principale pour votre application
def integrate_google_sheets_oauth():
    """
    Fonction principale d'intégration Google Sheets OAuth
    À appeler dans votre streamlit_app.py
    """
    # Initialiser l'interface
    gs_interface = TLBGoogleSheetsInterface()
    
    # Affichage conditionnel
    has_portfolio_loaded = (
        'input_file_path' in st.session_state and 
        st.session_state.input_file_path and
        'df_data' in st.session_state and
        not st.session_state.df_data.empty
    )
    
    # Sidebar: toujours afficher l'intégration Google Sheets
    gs_interface.display_sidebar_integration()
    
    # Interface principale: seulement si demandé et pas de portfolio chargé
    if not has_portfolio_loaded and st.session_state.get('show_google_auth', False):
        gs_interface.display_main_interface()
    
    # Debug (développement)
    if st.secrets.get("DEBUG_MODE", False):
        gs_interface.display_debug_info()
    
    return gs_interface
