# modules/google_sheets_integration.py
# Module d'intégration Google Sheets pour TLB INVESTOR

import streamlit as st
import pandas as pd
import requests
import io
import os
import re
from datetime import datetime
from typing import Dict, Tuple, Optional
from urllib.parse import urlparse, parse_qs

class TLBGoogleSheetsManager:
    """
    Gestionnaire Google Sheets pour TLB INVESTOR
    Permet de charger un portfolio depuis Google Sheets avec authentification
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.temp_folder = ".temp"
        os.makedirs(self.temp_folder, exist_ok=True)
    
    def extract_sheet_id(self, url: str) -> Optional[str]:
        """
        Extraire l'ID du Google Sheet depuis l'URL
        
        Args:
            url: URL du Google Sheet
            
        Returns:
            str: ID du sheet ou None si invalide
        """
        try:
            # Patterns possibles pour les URLs Google Sheets
            patterns = [
                r'/spreadsheets/d/([a-zA-Z0-9-_]+)',
                r'key=([a-zA-Z0-9-_]+)',
                r'id=([a-zA-Z0-9-_]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            st.error(f"Erreur extraction ID sheet: {e}")
            return None
    
    def get_sheet_names(self, sheet_id: str) -> Dict[str, str]:
        """
        Récupérer les noms des feuilles du Google Sheet
        
        Args:
            sheet_id: ID du Google Sheet
            
        Returns:
            dict: {nom_feuille: gid} ou None si erreur
        """
        try:
            # URL pour récupérer les métadonnées du sheet
            meta_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit#gid=0"
            
            # Pour simplifier, on utilise les noms standards TLB
            # En production, on pourrait parser la page pour les vrais noms
            return {
                "Feuil1": "0",           # Données principales
                "Feuil2": "1",           # Limites  
                "Feuil3": "2",           # Commentaires
                "Feuil4": "3",           # Dividendes
                "Feuil5": "4"            # Événements
            }
            
        except Exception as e:
            st.warning(f"Erreur récupération feuilles: {e}")
            return {}
    
    def read_sheet_as_csv(self, sheet_id: str, gid: str = "0") -> Optional[pd.DataFrame]:
        """
        Lire une feuille Google Sheets en tant que CSV
        
        Args:
            sheet_id: ID du Google Sheet
            gid: ID de la feuille (par défaut 0)
            
        Returns:
            DataFrame ou None si erreur
        """
        try:
            # URL pour export CSV d'une feuille spécifique
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            
            # Télécharger le CSV
            response = self.session.get(csv_url)
            response.raise_for_status()
            
            # Convertir en DataFrame
            csv_data = io.StringIO(response.text)
            df = pd.read_csv(csv_data)
            
            return df
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                st.error("❌ Accès refusé au Google Sheet. Vérifiez les permissions de partage.")
                return None
            elif e.response.status_code == 404:
                st.error("❌ Google Sheet non trouvé. Vérifiez l'URL.")
                return None
            else:
                st.error(f"❌ Erreur HTTP {e.response.status_code}")
                return None
                
        except Exception as e:
            st.error(f"❌ Erreur lecture Google Sheet: {e}")
            return None
    
    def load_portfolio_from_sheets(self, sheet_url: str, username: str) -> Tuple[bool, str]:
        """
        Charger un portfolio complet depuis Google Sheets
        
        Args:
            sheet_url: URL du Google Sheet
            username: nom d'utilisateur pour le versioning
            
        Returns:
            tuple: (success, message)
        """
        try:
            # Extraire l'ID du sheet
            sheet_id = self.extract_sheet_id(sheet_url)
            if not sheet_id:
                return False, "URL Google Sheets invalide"
            
            # Récupérer les noms des feuilles
            sheet_names = self.get_sheet_names(sheet_id)
            if not sheet_names:
                return False, "Impossible de récupérer les feuilles du document"
            
            # Charger chaque feuille
            sheets_data = {}
            
            with st.spinner("📊 Chargement des données depuis Google Sheets..."):
                for sheet_name, gid in sheet_names.items():
                    with st.spinner(f"📄 Chargement {sheet_name}..."):
                        df = self.read_sheet_as_csv(sheet_id, gid)
                        
                        if df is not None and not df.empty:
                            # CORRECTION : Nettoyer les données après chargement
                            df = self.clean_dataframe(df, sheet_name)
                            sheets_data[sheet_name] = df
                            st.success(f"✅ {sheet_name}: {len(df)} lignes chargées")
                        else:
                            # Créer DataFrame vide si la feuille n'existe pas
                            sheets_data[sheet_name] = self.create_empty_dataframe(sheet_name)
                            st.info(f"⚪ {sheet_name}: Feuille vide, structure par défaut créée")
            
            # Vérifier qu'on a au moins les données principales
            if sheets_data.get("Feuil1") is None or sheets_data["Feuil1"].empty:
                return False, "Aucune donnée trouvée dans la feuille principale (Feuil1)"
            
            # Charger dans session_state
            st.session_state.df_data = sheets_data.get("Feuil1", pd.DataFrame())
            st.session_state.df_limits = sheets_data.get("Feuil2", pd.DataFrame())
            st.session_state.df_comments = sheets_data.get("Feuil3", pd.DataFrame())
            st.session_state.df_dividendes = sheets_data.get("Feuil4", pd.DataFrame())
            st.session_state.df_events = sheets_data.get("Feuil5", pd.DataFrame())
            
            # Sauvegarder localement avec versioning
            success, filepath = self.save_to_local_excel(username)
            if success:
                # Mettre à jour les métadonnées de session
                st.session_state.input_file_path = filepath
                st.session_state.base_filename = f"TLB_portfolio_{username}_GoogleSheets"
                st.session_state.save_filename = os.path.basename(filepath)
                st.session_state.data_modified = False
                st.session_state.current_values_updated = False
                st.session_state.auto_update_done = False
                st.session_state.file_uploaded = "google_sheets"
                
                total_rows = len(st.session_state.df_data)
                return True, f"Portfolio chargé avec succès depuis Google Sheets ! {total_rows} investissements trouvés"
            else:
                return False, "Données chargées mais erreur de sauvegarde locale"
                
        except Exception as e:
            return False, f"Erreur lors du chargement: {str(e)}"
    
    def clean_dataframe(self, df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
        """
        Nettoyer et formater les données selon le type de feuille
        
        Args:
            df: DataFrame à nettoyer
            sheet_name: nom de la feuille
            
        Returns:
            DataFrame nettoyé
        """
        try:
            df_cleaned = df.copy()
            
            if sheet_name == "Feuil1":  # Données principales
                # Conversion des colonnes numériques
                numeric_columns = ['Quantity', 'Purchase price', 'Purchase value', 'Current price', 'Current value']
                for col in numeric_columns:
                    if col in df_cleaned.columns:
                        df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce').fillna(0)
                
                # Conversion des dates
                if 'Date' in df_cleaned.columns:
                    df_cleaned['Date'] = pd.to_datetime(df_cleaned['Date'], errors='coerce')
                
                # Nettoyer les colonnes texte
                text_columns = ['Ticker', 'Type', 'Secteur', 'Category', 'Entreprise', 'Compte', 'Units']
                for col in text_columns:
                    if col in df_cleaned.columns:
                        df_cleaned[col] = df_cleaned[col].astype(str).fillna('')
                        
            elif sheet_name == "Feuil2":  # Limites
                if 'Valeur seuils' in df_cleaned.columns:
                    df_cleaned['Valeur seuils'] = pd.to_numeric(df_cleaned['Valeur seuils'], errors='coerce').fillna(0)
                    
            elif sheet_name == "Feuil3":  # Commentaires
                if 'Date' in df_cleaned.columns:
                    df_cleaned['Date'] = pd.to_datetime(df_cleaned['Date'], errors='coerce')
                if 'Date action' in df_cleaned.columns:
                    df_cleaned['Date action'] = pd.to_datetime(df_cleaned['Date action'], errors='coerce')
                    
            elif sheet_name == "Feuil4":  # Dividendes
                if 'Date paiement' in df_cleaned.columns:
                    df_cleaned['Date paiement'] = pd.to_datetime(df_cleaned['Date paiement'], errors='coerce')
                numeric_div_columns = ['Dividende par action', 'Quantité détenue', 'Montant brut (€)', 'Montant net (€)']
                for col in numeric_div_columns:
                    if col in df_cleaned.columns:
                        df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce').fillna(0)
                        
            elif sheet_name == "Feuil5":  # Événements
                if 'Date' in df_cleaned.columns:
                    df_cleaned['Date'] = pd.to_datetime(df_cleaned['Date'], errors='coerce')
            
            return df_cleaned
            
        except Exception as e:
            st.warning(f"Erreur nettoyage {sheet_name}: {e}")
            return df
    
    def create_empty_dataframe(self, sheet_name: str) -> pd.DataFrame:
        """
        Créer un DataFrame vide avec la structure correcte selon le type de feuille
        
        Args:
            sheet_name: nom de la feuille
            
        Returns:
            DataFrame vide avec les bonnes colonnes
        """
        if sheet_name == "Feuil1":
            return pd.DataFrame(columns=[
                "Date", "Compte", "Ticker", "Type", "Secteur", "Category", 
                "Entreprise", "Quantity", "Purchase price", "Purchase value", 
                "Current price", "Current value", "Units"
            ])
        elif sheet_name == "Feuil2":
            return pd.DataFrame(columns=["Variable1", "Variable2", "Valeur seuils"])
        elif sheet_name == "Feuil3":
            return pd.DataFrame(columns=["Date", "Commentaire", "Date action", "Actions"])
        elif sheet_name == "Feuil4":
            return pd.DataFrame(columns=[
                "Date paiement", "Ticker", "Entreprise", "Dividende par action", 
                "Quantité détenue", "Montant brut (€)", "Montant net (€)", "Devise", "Type"
            ])
        elif sheet_name == "Feuil5":
            return pd.DataFrame(columns=["Date", "Event"])
        else:
            return pd.DataFrame()
    
    def save_to_local_excel(self, username: str) -> Tuple[bool, str]:
        """
        Sauvegarder les données en local avec versioning
        
        Args:
            username: nom d'utilisateur
            
        Returns:
            tuple: (success, filepath)
        """
        try:
            # Nom de fichier avec versioning
            today_str = datetime.today().strftime('%Y%m%d')
            filename = f"TLB_portfolio_{username}_GoogleSheets_{today_str}.xlsx"
            filepath = os.path.join(self.temp_folder, filename)
            
            # Sauvegarder avec toutes les feuilles
            with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
                st.session_state.df_data.to_excel(writer, sheet_name="Feuil1", index=False)
                st.session_state.df_limits.to_excel(writer, sheet_name="Feuil2", index=False)
                st.session_state.df_comments.to_excel(writer, sheet_name="Feuil3", index=False)
                st.session_state.df_dividendes.to_excel(writer, sheet_name="Feuil4", index=False)
                st.session_state.df_events.to_excel(writer, sheet_name="Feuil5", index=False)
            
            return True, filepath
            
        except Exception as e:
            st.error(f"Erreur sauvegarde locale: {e}")
            return False, ""

def display_google_sheets_loader():
    """
    Interface de chargement Google Sheets dans la sidebar
    """
    # Vérifier que l'utilisateur est connecté et 2FA validé
    is_authenticated = st.session_state.get("authentication_status", False)
    is_2fa_verified = st.session_state.get("tlb_2fa_verified", False)
    
    if not (is_authenticated and is_2fa_verified):
        return
    
    username = st.session_state.get("username", "user")
    
    # Vérifier si l'utilisateur a une URL Google Sheets configurée
    try:
        import yaml
        from yaml.loader import SafeLoader
        
        config_path = 'config.yaml'
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.load(f, Loader=SafeLoader)
            
            user_config = config['credentials']['usernames'].get(username, {})
            google_sheets_url = user_config.get('google_sheets_url', '')
            
            if google_sheets_url:
                st.sidebar.markdown("---")
                st.sidebar.markdown("### 📊 Google Sheets")
                
                # Afficher l'URL configurée (tronquée)
                url_display = google_sheets_url[:50] + "..." if len(google_sheets_url) > 50 else google_sheets_url
                st.sidebar.info(f"📋 **Sheet configuré:**\n{url_display}")
                
                # Bouton de chargement
                if st.sidebar.button("📥 Load Data (Google Sheets)", 
                                   key="load_google_sheets", 
                                   type="primary",
                                   help="Charger le portfolio depuis Google Sheets"):
                    
                    # Initialiser le gestionnaire
                    sheets_manager = TLBGoogleSheetsManager()
                    
                    # Charger depuis Google Sheets
                    success, message = sheets_manager.load_portfolio_from_sheets(google_sheets_url, username)
                    
                    if success:
                        st.sidebar.success("✅ " + message)
                        
                        # Actualisation automatique après chargement
                        try:
                            from modules.tab1_actualisation import update_portfolio_prices_optimized
                            
                            with st.spinner("🔄 Actualisation automatique des cours..."):
                                df_updated = update_portfolio_prices_optimized(st.session_state.df_data)
                                st.session_state.df_data = df_updated
                                st.session_state.data_modified = True
                                st.session_state.auto_update_done = True
                                
                                # Sauvegarder les cours actualisés
                                from modules.tab0_constants import save_to_excel
                                save_success = save_to_excel()
                                if save_success:
                                    st.sidebar.success("✅ Cours actualisés et sauvegardés")
                        
                        except Exception as e:
                            st.sidebar.warning(f"⚠️ Données chargées mais erreur actualisation: {e}")
                        
                        # Recharger la page pour afficher le portfolio
                        st.rerun()
                        
                    else:
                        st.sidebar.error("❌ " + message)
                        
                        # Aide au dépannage
                        with st.sidebar.expander("💡 Aide au dépannage", expanded=True):
                            st.markdown("""
                            **🔍 Problèmes courants :**
                            
                            **❌ Erreur HTTP 400/403 - Accès refusé :**
                            1. **Partagez votre Google Sheet** :
                               - Ouvrez le Google Sheet
                               - Clic sur "Partager" (coin supérieur droit)
                               - Clic sur "Modifier l'accès"
                               - Sélectionner **"Toute personne disposant du lien"**
                               - Niveau d'accès : **"Lecteur"** (lecture seule)
                               - Cliquer "Terminé"
                            
                            2. **Vérifiez l'URL** dans config.yaml :
                            ```
                            google_sheets_url: "https://docs.google.com/spreadsheets/d/VOTRE_ID/edit#gid=0"
                            ```
                            
                            **❌ Sheet non trouvé (404) :**
                            - L'URL doit être complète et correcte
                            - Vérifiez que le Google Sheet existe
                            
                            **✅ Format URL correct :**
                            ```
                            https://docs.google.com/spreadsheets/d/1abc123def456/edit#gid=0
                            ```
                            
                            **📊 Structure attendue :**
                            - **Feuil1** : Données portefeuille (obligatoire)
                            - **Feuil2** : Limites (optionnel)
                            - **Feuil3** : Commentaires (optionnel)
                            - **Feuil4** : Dividendes (optionnel)
                            - **Feuil5** : Événements (optionnel)
                            
                            **💬 Support :** pierre.barennes@gmail.com
                            """)
                            
                            # Test de connectivité
                            if st.button("🧪 Tester l'accès au Google Sheet", key="test_sheets_access"):
                                test_result = test_google_sheets_access(google_sheets_url)
                                if test_result["success"]:
                                    st.success(f"✅ Accès OK ! {test_result['rows']} lignes, {test_result['columns']} colonnes")
                                    st.info(f"Sheet ID détecté : {test_result['sheet_id']}")
                                else:
                                    st.error(f"❌ Test échoué : {test_result['error']}")
                                    
                                    # Instructions spécifiques selon le type d'erreur
                                    if "403" in test_result['error'] or "Accès refusé" in test_result['error']:
                                        st.warning("🔧 **Action requise :** Partagez le Google Sheet en lecture publique")
                                    elif "404" in test_result['error']:
                                        st.warning("🔧 **Action requise :** Vérifiez l'URL du Google Sheet")
                                    elif "URL invalide" in test_result['error']:
                                        st.warning("🔧 **Action requise :** Corrigez l'URL dans config.yaml")
            else:
                # Afficher comment configurer Google Sheets
                st.sidebar.markdown("---")
                st.sidebar.markdown("### 📊 Google Sheets")
                st.sidebar.info("""
                **Configuration Google Sheets**
                
                Pour activer le chargement depuis Google Sheets, ajoutez dans votre config.yaml :
                
                ```yaml
                pbarennes:
                  google_sheets_url: "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
                ```
                
                Le Google Sheet doit être partagé en lecture.
                """)
                
    except Exception as e:
        st.sidebar.error(f"Erreur configuration Google Sheets: {e}")

def test_google_sheets_access(sheet_url: str) -> Dict[str, any]:
    """
    Tester l'accès à un Google Sheet (fonction utilitaire)
    
    Args:
        sheet_url: URL du Google Sheet
        
    Returns:
        dict: résultats du test
    """
    manager = TLBGoogleSheetsManager()
    
    try:
        # Extraire l'ID
        sheet_id = manager.extract_sheet_id(sheet_url)
        if not sheet_id:
            return {"success": False, "error": "URL invalide"}
        
        # Tester l'accès à la première feuille
        df = manager.read_sheet_as_csv(sheet_id, "0")
        
        if df is not None:
            return {
                "success": True, 
                "rows": len(df), 
                "columns": len(df.columns),
                "sheet_id": sheet_id
            }
        else:
            return {"success": False, "error": "Accès refusé ou feuille vide"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}
