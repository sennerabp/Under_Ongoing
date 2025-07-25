# modules/google_sheets_oauth_manager.py
"""
Gestionnaire Google Sheets optimisé avec OAuth2
Chaque utilisateur accède à SON propre Google Sheet privé
"""

import streamlit as st
import pandas as pd
import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, List
import hashlib
import time

class TLBGoogleSheetsOAuthManager:
    """
    Gestionnaire Google Sheets avec OAuth2 pour TLB INVESTOR
    - Authentification OAuth2 sécurisée
    - Cache intelligent avec TTL
    - Accès aux Google Sheets privés de l'utilisateur
    - Synchronisation bidirectionnelle optimisée
    """
    
    def __init__(self, cache_duration_minutes: int = 10):
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        self.credentials = None
        self.gc = None
        self.drive_service = None
        
        # Configuration OAuth2 - À adapter selon votre projet Google Cloud
        self.SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
        
        self._init_session_cache()
    
    def _init_session_cache(self):
        """Initialiser le cache de session"""
        if 'tlb_gs_cache' not in st.session_state:
            st.session_state.tlb_gs_cache = {
                'credentials': None,
                'authenticated': False,
                'user_sheets': {},
                'data_cache': {},
                'last_update': {},
                'selected_sheet_id': None,
                'user_profile': None
            }
    
    def setup_oauth_credentials(self, client_config: Dict) -> bool:
        """
        Configuration des credentials OAuth2
        
        Args:
            client_config: Configuration OAuth2 (client_id, client_secret, etc.)
            
        Returns:
            bool: True si configuration réussie
        """
        try:
            self.client_config = client_config
            return True
        except Exception as e:
            st.error(f"❌ Erreur configuration OAuth2: {e}")
            return False
    
    def authenticate_user(self) -> Tuple[bool, str]:
        """
        Authentifier l'utilisateur via OAuth2 Google
        
        Returns:
            tuple: (success, message)
        """
        try:
            # Vérifier si déjà authentifié
            if st.session_state.tlb_gs_cache['authenticated']:
                return True, "Déjà authentifié"
            
            # Configuration du flow OAuth2
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.SCOPES,
                redirect_uri=self.client_config.get('redirect_uri', 'urn:ietf:wg:oauth:2.0:oob')
            )
            
            # Vérifier si on a un code d'autorisation
            auth_code = st.session_state.get('google_auth_code')
            
            if not auth_code:
                # Générer l'URL d'autorisation
                auth_url, _ = flow.authorization_url(prompt='consent')
                return False, f"Veuillez vous authentifier: {auth_url}"
            
            # Échanger le code contre des tokens
            flow.fetch_token(code=auth_code)
            
            # Sauvegarder les credentials
            self.credentials = flow.credentials
            st.session_state.tlb_gs_cache['credentials'] = {
                'token': self.credentials.token,
                'refresh_token': self.credentials.refresh_token,
                'token_uri': self.credentials.token_uri,
                'client_id': self.credentials.client_id,
                'client_secret': self.credentials.client_secret,
                'scopes': self.credentials.scopes
            }
            
            # Initialiser les services
            self._init_services()
            
            # Récupérer le profil utilisateur
            user_profile = self._get_user_profile()
            st.session_state.tlb_gs_cache['user_profile'] = user_profile
            st.session_state.tlb_gs_cache['authenticated'] = True
            
            return True, f"Authentification réussie pour {user_profile.get('email', 'utilisateur')}"
            
        except Exception as e:
            return False, f"Erreur authentification: {str(e)}"
    
    def _init_services(self):
        """Initialiser les services Google"""
        try:
            # Service gspread
            self.gc = gspread.authorize(self.credentials)
            
            # Service Google Drive pour lister les sheets
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            
        except Exception as e:
            st.error(f"❌ Erreur initialisation services: {e}")
    
    def _get_user_profile(self) -> Dict:
        """Récupérer le profil utilisateur Google"""
        try:
            service = build('oauth2', 'v2', credentials=self.credentials)
            profile = service.userinfo().get().execute()
            return profile
        except Exception as e:
            st.warning(f"⚠️ Impossible de récupérer le profil: {e}")
            return {}
    
    def list_user_spreadsheets(self, force_refresh: bool = False) -> List[Dict]:
        """
        Lister les Google Sheets de l'utilisateur
        
        Args:
            force_refresh: Forcer le rechargement depuis Google Drive
            
        Returns:
            List[Dict]: Liste des spreadsheets avec id, nom, date de modification
        """
        cache_key = 'user_spreadsheets'
        
        # Vérifier le cache
        if not force_refresh and self._is_cache_valid(cache_key):
            return st.session_state.tlb_gs_cache['data_cache'][cache_key]
        
        try:
            # Rechercher les Google Sheets
            query = "mimeType='application/vnd.google-apps.spreadsheet'"
            results = self.drive_service.files().list(
                q=query,
                pageSize=50,
                fields="files(id, name, modifiedTime, webViewLink)"
            ).execute()
            
            spreadsheets = []
            for file in results.get('files', []):
                spreadsheets.append({
                    'id': file['id'],
                    'name': file['name'],
                    'modified': file.get('modifiedTime', ''),
                    'url': file.get('webViewLink', ''),
                    'display_name': f"{file['name']} (Modifié: {file.get('modifiedTime', 'Inconnu')[:10]})"
                })
            
            # Trier par date de modification (plus récent en premier)
            spreadsheets.sort(key=lambda x: x['modified'], reverse=True)
            
            # Mettre en cache
            self._update_cache(cache_key, spreadsheets)
            
            return spreadsheets
            
        except Exception as e:
            st.error(f"❌ Erreur listage spreadsheets: {e}")
            return []
    
    def load_portfolio_data(self, sheet_id: str, force_refresh: bool = False) -> Tuple[bool, Dict[str, pd.DataFrame]]:
        """
        Charger les données du portfolio depuis un Google Sheet
        
        Args:
            sheet_id: ID du Google Sheet
            force_refresh: Forcer le rechargement
            
        Returns:
            tuple: (success, dict_of_dataframes)
        """
        cache_key = f"portfolio_data_{sheet_id}"
        
        # Vérifier le cache
        if not force_refresh and self._is_cache_valid(cache_key):
            cached_data = st.session_state.tlb_gs_cache['data_cache'][cache_key]
            return True, cached_data
        
        try:
            # Ouvrir le spreadsheet
            spreadsheet = self.gc.open_by_key(sheet_id)
            
            portfolio_data = {}
            
            # Mapping des feuilles TLB
            sheet_mapping = {
                'Feuil1': 'df_data',       # Données principales
                'Feuil2': 'df_limits',     # Limites
                'Feuil3': 'df_comments',   # Commentaires
                'Feuil4': 'df_dividendes', # Dividendes
                'Feuil5': 'df_events'      # Événements
            }
            
            for sheet_name, df_name in sheet_mapping.items():
                try:
                    # Essayer de récupérer la feuille
                    worksheet = spreadsheet.worksheet(sheet_name)
                    
                    # Récupérer les données avec gspread_dataframe (plus rapide)
                    df = self._get_worksheet_dataframe(worksheet)
                    
                    # Nettoyer les données selon le type de feuille
                    df_cleaned = self._clean_dataframe_by_type(df, df_name)
                    
                    portfolio_data[df_name] = df_cleaned
                    st.success(f"✅ {sheet_name}: {len(df_cleaned)} lignes chargées")
                    
                except gspread.WorksheetNotFound:
                    # Créer DataFrame vide si feuille n'existe pas
                    portfolio_data[df_name] = self._create_empty_dataframe(df_name)
                    st.info(f"⚪ {sheet_name}: Feuille non trouvée, structure vide créée")
                    
                except Exception as e:
                    st.warning(f"⚠️ Erreur {sheet_name}: {e}")
                    portfolio_data[df_name] = self._create_empty_dataframe(df_name)
            
            # Vérifier qu'on a au moins les données principales
            if portfolio_data.get('df_data') is None or portfolio_data['df_data'].empty:
                return False, "Aucune donnée trouvée dans Feuil1"
            
            # Mettre en cache
            self._update_cache(cache_key, portfolio_data)
            
            # Stocker l'ID du sheet sélectionné
            st.session_state.tlb_gs_cache['selected_sheet_id'] = sheet_id
            
            return True, portfolio_data
            
        except Exception as e:
            return False, f"Erreur chargement portfolio: {str(e)}"
    
    def _get_worksheet_dataframe(self, worksheet) -> pd.DataFrame:
        """
        Récupérer un DataFrame depuis une worksheet de façon optimisée
        """
        try:
            # Méthode 1: gspread_dataframe (plus rapide pour gros datasets)
            from gspread_dataframe import get_as_dataframe
            df = get_as_dataframe(worksheet, parse_dates=True, usecols=None, 
                                dtype=str, converters=None, skiprows=0, 
                                nrows=None, header=0)
            
            # Supprimer les lignes complètement vides
            df = df.dropna(how='all').reset_index(drop=True)
            
            return df
            
        except ImportError:
            # Fallback: méthode gspread standard
            st.warning("⚠️ gspread_dataframe non disponible, utilisation méthode standard")
            records = worksheet.get_all_records()
            return pd.DataFrame(records)
        
        except Exception as e:
            st.warning(f"⚠️ Erreur lecture worksheet, fallback: {e}")
            # Dernière tentative
            values = worksheet.get_all_values()
            if values:
                df = pd.DataFrame(values[1:], columns=values[0])
                return df
            return pd.DataFrame()
    
    def _clean_dataframe_by_type(self, df: pd.DataFrame, df_type: str) -> pd.DataFrame:
        """
        Nettoyer un DataFrame selon son type (repris de votre code existant)
        """
        if df.empty:
            return df
            
        df_cleaned = df.copy()
        
        try:
            if df_type == 'df_data':  # Données principales
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
                        
            elif df_type == 'df_limits':  # Limites
                if 'Valeur seuils' in df_cleaned.columns:
                    df_cleaned['Valeur seuils'] = pd.to_numeric(df_cleaned['Valeur seuils'], errors='coerce').fillna(0)
                    
            elif df_type == 'df_comments':  # Commentaires
                if 'Date' in df_cleaned.columns:
                    df_cleaned['Date'] = pd.to_datetime(df_cleaned['Date'], errors='coerce')
                if 'Date action' in df_cleaned.columns:
                    df_cleaned['Date action'] = pd.to_datetime(df_cleaned['Date action'], errors='coerce')
                    
            elif df_type == 'df_dividendes':  # Dividendes
                if 'Date paiement' in df_cleaned.columns:
                    df_cleaned['Date paiement'] = pd.to_datetime(df_cleaned['Date paiement'], errors='coerce')
                numeric_div_columns = ['Dividende par action', 'Quantité détenue', 'Montant brut (€)', 'Montant net (€)']
                for col in numeric_div_columns:
                    if col in df_cleaned.columns:
                        df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce').fillna(0)
                        
            elif df_type == 'df_events':  # Événements
                if 'Date' in df_cleaned.columns:
                    df_cleaned['Date'] = pd.to_datetime(df_cleaned['Date'], errors='coerce')
            
            return df_cleaned
            
        except Exception as e:
            st.warning(f"⚠️ Erreur nettoyage {df_type}: {e}")
            return df
    
    def _create_empty_dataframe(self, df_type: str) -> pd.DataFrame:
        """Créer DataFrame vide selon le type (repris de votre code)"""
        if df_type == 'df_data':
            return pd.DataFrame(columns=[
                "Date", "Compte", "Ticker", "Type", "Secteur", "Category", 
                "Entreprise", "Quantity", "Purchase price", "Purchase value", 
                "Current price", "Current value", "Units"
            ])
        elif df_type == 'df_limits':
            return pd.DataFrame(columns=["Variable1", "Variable2", "Valeur seuils"])
        elif df_type == 'df_comments':
            return pd.DataFrame(columns=["Date", "Commentaire", "Date action", "Actions"])
        elif df_type == 'df_dividendes':
            return pd.DataFrame(columns=[
                "Date paiement", "Ticker", "Entreprise", "Dividende par action", 
                "Quantité détenue", "Montant brut (€)", "Montant net (€)", "Devise", "Type"
            ])
        elif df_type == 'df_events':
            return pd.DataFrame(columns=["Date", "Event"])
        else:
            return pd.DataFrame()
    
    def save_portfolio_data(self, portfolio_data: Dict[str, pd.DataFrame], sheet_id: str = None) -> Tuple[bool, str]:
        """
        Sauvegarder les données du portfolio vers Google Sheets
        
        Args:
            portfolio_data: Dictionnaire des DataFrames à sauvegarder
            sheet_id: ID du sheet (utilise le sheet sélectionné si None)
            
        Returns:
            tuple: (success, message)
        """
        if not sheet_id:
            sheet_id = st.session_state.tlb_gs_cache.get('selected_sheet_id')
            if not sheet_id:
                return False, "Aucun Google Sheet sélectionné"
        
        try:
            # Ouvrir le spreadsheet
            spreadsheet = self.gc.open_by_key(sheet_id)
            
            # Mapping des DataFrames vers les feuilles
            sheet_mapping = {
                'df_data': 'Feuil1',
                'df_limits': 'Feuil2', 
                'df_comments': 'Feuil3',
                'df_dividendes': 'Feuil4',
                'df_events': 'Feuil5'
            }
            
            saved_sheets = []
            
            for df_name, sheet_name in sheet_mapping.items():
                if df_name in portfolio_data:
                    df = portfolio_data[df_name]
                    
                    try:
                        # Essayer d'obtenir la feuille existante
                        try:
                            worksheet = spreadsheet.worksheet(sheet_name)
                        except gspread.WorksheetNotFound:
                            # Créer la feuille si elle n'existe pas
                            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
                        
                        # Vider la feuille
                        worksheet.clear()
                        
                        # Écrire les données
                        if not df.empty:
                            # Méthode optimisée avec gspread_dataframe
                            try:
                                from gspread_dataframe import set_with_dataframe
                                set_with_dataframe(worksheet, df, include_index=False)
                            except ImportError:
                                # Fallback: méthode standard
                                worksheet.update([df.columns.values.tolist()] + df.values.tolist())
                        
                        saved_sheets.append(sheet_name)
                        
                    except Exception as e:
                        st.warning(f"⚠️ Erreur sauvegarde {sheet_name}: {e}")
            
            # Invalider le cache pour ce sheet
            cache_key = f"portfolio_data_{sheet_id}"
            if cache_key in st.session_state.tlb_gs_cache['data_cache']:
                del st.session_state.tlb_gs_cache['data_cache'][cache_key]
            
            if saved_sheets:
                return True, f"Sauvegarde réussie: {', '.join(saved_sheets)}"
            else:
                return False, "Aucune feuille sauvegardée"
                
        except Exception as e:
            return False, f"Erreur sauvegarde: {str(e)}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Vérifier si le cache est valide"""
        cache = st.session_state.tlb_gs_cache
        
        if cache_key not in cache['data_cache']:
            return False
        
        if cache_key not in cache['last_update']:
            return False
        
        last_update = cache['last_update'][cache_key]
        return datetime.now() - last_update < self.cache_duration
    
    def _update_cache(self, cache_key: str, data):
        """Mettre à jour le cache"""
        cache = st.session_state.tlb_gs_cache
        cache['data_cache'][cache_key] = data
        cache['last_update'][cache_key] = datetime.now()
    
    def clear_cache(self, cache_key: str = None):
        """Vider le cache"""
        cache = st.session_state.tlb_gs_cache
        
        if cache_key:
            cache['data_cache'].pop(cache_key, None)
            cache['last_update'].pop(cache_key, None)
        else:
            cache['data_cache'].clear()
            cache['last_update'].clear()
    
    def disconnect(self):
        """Déconnecter et nettoyer la session"""
        # Nettoyer le cache
        st.session_state.tlb_gs_cache = {
            'credentials': None,
            'authenticated': False,
            'user_sheets': {},
            'data_cache': {},
            'last_update': {},
            'selected_sheet_id': None,
            'user_profile': None
        }
        
        # Réinitialiser les services
        self.credentials = None
        self.gc = None
        self.drive_service = None
    
    def get_cache_stats(self) -> Dict:
        """Obtenir les statistiques du cache"""
        cache = st.session_state.tlb_gs_cache
        return {
            'authenticated': cache['authenticated'],
            'cached_items': len(cache['data_cache']),
            'user_email': cache.get('user_profile', {}).get('email', 'Inconnu'),
            'selected_sheet': cache.get('selected_sheet_id', 'Aucun')
        }
