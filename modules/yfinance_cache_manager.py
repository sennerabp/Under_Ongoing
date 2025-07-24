import streamlit as st
import pandas as pd
import yfinance as yf
import time
import random
from datetime import datetime, timedelta
import hashlib
import json
from functools import wraps
import requests
from typing import Dict, List, Optional, Tuple

class YFinanceCacheManager:
    """
    Gestionnaire de cache intelligent pour optimiser les appels yfinance
    et éviter les rate limits
    """
    
    def __init__(self, cache_duration_minutes: int = 5):
        """
        Args:
            cache_duration_minutes: Durée de vie du cache en minutes
        """
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        self.last_update = {}
        self.price_cache = {}
        self.info_cache = {}
        self.session = requests.Session()
        
        # Initialiser le cache dans session_state si pas présent
        if 'yf_cache' not in st.session_state:
            st.session_state.yf_cache = {
                'prices': {},
                'info': {},
                'last_update': {},
                'eurusd_rate': {'rate': 1.1, 'timestamp': datetime.now() - timedelta(hours=1)}
            }
    
    def _is_cache_valid(self, ticker: str, cache_type: str = 'prices') -> bool:
        """Vérifier si le cache est encore valide pour un ticker"""
        cache_key = f"{ticker}_{cache_type}"
        if cache_key not in st.session_state.yf_cache['last_update']:
            return False
        
        last_update = st.session_state.yf_cache['last_update'][cache_key]
        return datetime.now() - last_update < self.cache_duration
    
    def _rate_limit_handler(self, func, *args, **kwargs):
        """Gestionnaire de rate limit avec retry exponentiel"""
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e).lower()
                if any(phrase in error_msg for phrase in ['rate limit', 'too many requests', '429']):
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0.5, 1.5)
                        st.warning(f"⏳ Rate limit atteint, attente de {delay:.1f}s... (tentative {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        st.error("❌ Rate limit persistant. Utilisation des données en cache.")
                        return None
                else:
                    st.warning(f"⚠️ Erreur pour {args[0] if args else 'ticker'}: {e}")
                    return None
        return None
    
    def get_eurusd_rate(self) -> float:
        """Récupérer le taux EUR/USD avec cache"""
        cache_data = st.session_state.yf_cache['eurusd_rate']
        
        # Vérifier si le cache EUR/USD est valide (1 heure)
        if datetime.now() - cache_data['timestamp'] < timedelta(hours=1):
            return cache_data['rate']
        
        try:
            # Essayer de récupérer le nouveau taux
            eurusd_ticker = yf.Ticker("EURUSD=X")
            rate_data = self._rate_limit_handler(eurusd_ticker.history, period="1d")
            
            if rate_data is not None and not rate_data.empty:
                new_rate = rate_data["Close"].iloc[-1]
                st.session_state.yf_cache['eurusd_rate'] = {
                    'rate': new_rate,
                    'timestamp': datetime.now()
                }
                return new_rate
            else:
                # Garder l'ancien taux si échec
                return cache_data['rate']
                
        except Exception as e:
            st.warning(f"Erreur EUR/USD, utilisation du taux en cache: {cache_data['rate']:.4f}")
            return cache_data['rate']
    
    def get_bulk_prices(self, tickers: List[str], period: str = "5d") -> Dict[str, pd.DataFrame]:
        """
        Récupérer les prix pour plusieurs tickers en une seule requête groupée
        VERSION AMÉLIORÉE pour gérer les tickers US/EU
        """
        # Filtrer les tickers qui ont besoin d'une mise à jour
        tickers_to_update = []
        cached_data = {}
        
        for ticker in tickers:
            if self._is_cache_valid(ticker, 'prices'):
                cached_data[ticker] = st.session_state.yf_cache['prices'][ticker]
            else:
                tickers_to_update.append(ticker)
        
        # Si tous les tickers sont en cache, retourner le cache
        if not tickers_to_update:
            return cached_data
        
        # Afficher le statut de mise à jour
        if tickers_to_update:
            with st.spinner(f"📈 Mise à jour de {len(tickers_to_update)} tickers..."):
                # STRATÉGIE 1: Essayer requête groupée d'abord
                try:
                    if len(tickers_to_update) > 1:
                        bulk_data = self._rate_limit_handler(
                            yf.download,
                            tickers=tickers_to_update,
                            period=period,
                            group_by='ticker',
                            auto_adjust=True,
                            progress=False,
                            threads=True
                        )
                        
                        if bulk_data is not None and not bulk_data.empty:
                            # Traiter les données pour chaque ticker
                            for ticker in tickers_to_update:
                                try:
                                    # Gestion robuste des structures de données
                                    if isinstance(bulk_data.columns, pd.MultiIndex):
                                        # Cas multi-index (plusieurs tickers)
                                        if ticker in bulk_data.columns.get_level_values(0):
                                            ticker_data = bulk_data[ticker]
                                        else:
                                            ticker_data = pd.DataFrame()
                                    else:
                                        # Cas simple (un seul ticker)
                                        ticker_data = bulk_data
                                    
                                    # Vérifier que les colonnes essentielles existent
                                    if not ticker_data.empty and 'Close' in ticker_data.columns:
                                        # Nettoyer les données
                                        ticker_data = ticker_data.dropna()
                                        if not ticker_data.empty:
                                            st.session_state.yf_cache['prices'][ticker] = ticker_data
                                            st.session_state.yf_cache['last_update'][f"{ticker}_prices"] = datetime.now()
                                            cached_data[ticker] = ticker_data
                                            continue
                                    
                                    # Si échec, essayer requête individuelle
                                    st.warning(f"🔄 Requête individuelle pour {ticker}...")
                                    individual_data = self._get_individual_ticker(ticker, period)
                                    if individual_data is not None:
                                        cached_data[ticker] = individual_data
                                        
                                except Exception as e:
                                    st.warning(f"⚠️ Erreur groupée pour {ticker}: {e}")
                                    # Fallback individuel
                                    individual_data = self._get_individual_ticker(ticker, period)
                                    if individual_data is not None:
                                        cached_data[ticker] = individual_data
                        else:
                            # Si bulk_data échoue, passer aux requêtes individuelles
                            for ticker in tickers_to_update:
                                individual_data = self._get_individual_ticker(ticker, period)
                                if individual_data is not None:
                                    cached_data[ticker] = individual_data
                    else:
                        # Un seul ticker, requête directe
                        ticker = tickers_to_update[0]
                        individual_data = self._get_individual_ticker(ticker, period)
                        if individual_data is not None:
                            cached_data[ticker] = individual_data
                            
                except Exception as e:
                    st.error(f"❌ Erreur majeure lors de la récupération: {e}")
                    # Dernier recours: requêtes individuelles pour tous
                    for ticker in tickers_to_update:
                        try:
                            individual_data = self._get_individual_ticker(ticker, period)
                            if individual_data is not None:
                                cached_data[ticker] = individual_data
                        except Exception as e2:
                            st.error(f"❌ Échec final pour {ticker}: {e2}")
        
        return cached_data
    
    def _get_individual_ticker(self, ticker: str, period: str = "5d") -> pd.DataFrame:
        """
        Récupérer les données d'un ticker individuellement
        """
        try:
            ticker_obj = yf.Ticker(ticker)
            hist_data = self._rate_limit_handler(ticker_obj.history, period=period, auto_adjust=True)
            
            if hist_data is not None and not hist_data.empty and 'Close' in hist_data.columns:
                # Nettoyer et valider les données
                hist_data = hist_data.dropna()
                if not hist_data.empty:
                    # Mettre à jour le cache
                    st.session_state.yf_cache['prices'][ticker] = hist_data
                    st.session_state.yf_cache['last_update'][f"{ticker}_prices"] = datetime.now()
                    st.success(f"✅ {ticker} mis à jour individuellement")
                    return hist_data
            
            st.warning(f"⚠️ Pas de données valides pour {ticker}")
            return None
            
        except Exception as e:
            st.warning(f"⚠️ Erreur individuelle pour {ticker}: {e}")
            return None
    
    def get_ticker_info(self, ticker: str, force_refresh: bool = False) -> Dict:
        """
        Récupérer les informations d'un ticker avec cache
        """
        if not force_refresh and self._is_cache_valid(ticker, 'info'):
            return st.session_state.yf_cache['info'].get(ticker, {})
        
        try:
            ticker_obj = yf.Ticker(ticker)
            info_data = self._rate_limit_handler(getattr, ticker_obj, 'info')
            
            if info_data:
                # Mettre à jour le cache
                st.session_state.yf_cache['info'][ticker] = info_data
                st.session_state.yf_cache['last_update'][f"{ticker}_info"] = datetime.now()
                return info_data
            else:
                # Retourner les données en cache si disponibles
                return st.session_state.yf_cache['info'].get(ticker, {})
                
        except Exception as e:
            st.warning(f"⚠️ Erreur info pour {ticker}: {e}")
            return st.session_state.yf_cache['info'].get(ticker, {})
    
    def get_current_prices(self, tickers: List[str]) -> Dict[str, float]:
        """
        Récupérer les prix actuels pour une liste de tickers - VERSION ROBUSTE
        """
        price_data = self.get_bulk_prices(tickers, period="2d")
        current_prices = {}
        
        for ticker in tickers:
            try:
                if ticker in price_data and not price_data[ticker].empty:
                    ticker_df = price_data[ticker]
                    
                    # Vérifications multiples pour les colonnes
                    close_col = None
                    for col_name in ['Close', 'close', 'CLOSE', 'Adj Close']:
                        if col_name in ticker_df.columns:
                            close_col = col_name
                            break
                    
                    if close_col is not None:
                        # Prendre le dernier prix valide (non-NaN)
                        close_prices = ticker_df[close_col].dropna()
                        if not close_prices.empty:
                            current_prices[ticker] = float(close_prices.iloc[-1])
                            continue
                    
                    st.warning(f"⚠️ Pas de colonne 'Close' valide pour {ticker}")
                    current_prices[ticker] = None
                else:
                    st.warning(f"⚠️ Pas de données de prix pour {ticker}")
                    current_prices[ticker] = None
                    
            except Exception as e:
                st.warning(f"⚠️ Erreur extraction prix pour {ticker}: {e}")
                current_prices[ticker] = None
        
        # Debug: afficher le statut
        valid_prices = sum(1 for price in current_prices.values() if price is not None)
        st.info(f"📊 Prix récupérés: {valid_prices}/{len(tickers)} tickers")
        
        return current_prices
    
    def get_cache_status(self) -> Dict:
        """Retourner le statut du cache pour debug"""
        cache = st.session_state.yf_cache
        return {
            'prix_en_cache': len(cache['prices']),
            'infos_en_cache': len(cache['info']),
            'derniere_maj_eurusd': cache['eurusd_rate']['timestamp'],
            'taux_eurusd_actuel': cache['eurusd_rate']['rate']
        }
    
    def clear_cache(self, ticker: str = None):
        """Vider le cache complètement ou pour un ticker spécifique"""
        if ticker:
            # Vider le cache pour un ticker spécifique
            cache = st.session_state.yf_cache
            cache['prices'].pop(ticker, None)
            cache['info'].pop(ticker, None)
            cache['last_update'].pop(f"{ticker}_prices", None)
            cache['last_update'].pop(f"{ticker}_info", None)
        else:
            # Vider tout le cache
            st.session_state.yf_cache = {
                'prices': {},
                'info': {},
                'last_update': {},
                'eurusd_rate': {'rate': 1.1, 'timestamp': datetime.now() - timedelta(hours=1)}
            }

# Instance globale du gestionnaire de cache
@st.cache_resource
def get_cache_manager():
    """Singleton du gestionnaire de cache"""
    return YFinanceCacheManager(cache_duration_minutes=5)


def update_portfolio_prices_optimized(df: pd.DataFrame) -> pd.DataFrame:
    """
    Version optimisée de la mise à jour des prix du portefeuille
    PRÉSERVATION des données originales + conversion à l'affichage
    """
    cache_manager = get_cache_manager()
    
    # Récupérer tous les tickers uniques
    tickers = df["Ticker"].dropna().unique().tolist()
    
    if not tickers:
        st.warning("Aucun ticker trouvé dans le portefeuille")
        return df
    
    # Récupérer les prix actuels de façon groupée
    current_prices = cache_manager.get_current_prices(tickers)
    
    # Appliquer les prix au DataFrame
    df_updated = df.copy()
    
    # === MISE À JOUR DES PRIX SEULEMENT ===
    df_updated["Current price"] = df_updated["Ticker"].map(current_prices)
    df_updated["Current value"] = df_updated["Current price"] * df_updated["Quantity"]
    
    # === IMPORTANT: On ne convertit RIEN ici ===
    # Les devises originales sont préservées
    # La conversion se fera au moment de l'affichage/calculs
    
    return df_updated


def convert_to_eur_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """
    🛡️ VERSION DÉFINITIVE - AUCUNE AMBIGUÏTÉ DE SERIES POSSIBLE
    Conversion USD→EUR ultra-sécurisée pour éviter l'erreur pandas
    """
    cache_manager = get_cache_manager()
    eurusd_rate = cache_manager.get_eurusd_rate()
    
    # Copie pour l'affichage
    df_display = df.copy()
    
    # Vérifications préliminaires - ARRÊT si conditions non remplies
    if df_display.empty:
        return df_display
    if "Units" not in df_display.columns:
        return df_display
    
    try:
        # === ÉTAPE 1: NETTOYER LA COLONNE UNITS ===
        df_display["Units"] = df_display["Units"].fillna("EUR")
        df_display["Units"] = df_display["Units"].astype(str)
        
        # === ÉTAPE 2: IDENTIFIER LES LIGNES USD (SANS COMPARAISON VECTORIELLE) ===
        usd_indices = []
        for idx in df_display.index:
            try:
                unit_value = str(df_display.loc[idx, "Units"]).strip().upper()
                if unit_value == "USD":
                    usd_indices.append(idx)
            except Exception:
                continue  # Ignorer les erreurs sur des lignes spécifiques
        
        # === ÉTAPE 3: SI PAS D'USD, RETOURNER IMMÉDIATEMENT ===
        if not usd_indices:
            return df_display
        
        # === ÉTAPE 4: CONVERSION LIGNE PAR LIGNE (ZÉRO AMBIGUÏTÉ) ===
        conversions_reussies = 0
        
        for idx in usd_indices:
            try:
                # Convertir Purchase value
                if "Purchase value" in df_display.columns:
                    pv = df_display.loc[idx, "Purchase value"]
                    if pd.notna(pv):
                        if pv != 0:  # Éviter les multiplications inutiles
                            df_display.loc[idx, "Purchase value"] = float(pv) * eurusd_rate
                
                # Convertir Current value
                if "Current value" in df_display.columns:
                    cv = df_display.loc[idx, "Current value"]
                    if pd.notna(cv):
                        if cv != 0:  # Éviter les multiplications inutiles
                            df_display.loc[idx, "Current value"] = float(cv) * eurusd_rate
                
                # Marquer comme converti
                df_display.loc[idx, "Units"] = "EUR"
                conversions_reussies += 1
                
            except Exception as e:
                # Log de l'erreur mais continuer
                st.warning(f"⚠️ Erreur conversion ligne {idx}: {e}")
                continue
        
        # === ÉTAPE 5: RAPPORT DE CONVERSION ===
        if conversions_reussies > 0:
            st.info(f"💱 {conversions_reussies} position(s) USD→EUR (taux: {eurusd_rate:.4f})")
        
        return df_display
        
    except Exception as e:
        # En cas d'erreur majeure, retourner les données originales
        st.error(f"❌ Erreur majeure lors de la conversion USD→EUR: {e}")
        st.info("🔄 Utilisation des données originales sans conversion")
        return df


def safe_currency_grouping(df):
    """
    🛡️ REGROUPEMENT SÉCURISÉ avec gestion des devises mixtes
    Cette fonction évite toute ambiguïté de Series lors du groupBy
    """
    try:
        # === ÉTAPE 1: VÉRIFICATIONS PRÉLIMINAIRES ===
        if df is None:
            return pd.DataFrame()
        if df.empty:
            return pd.DataFrame()
        if "Ticker" not in df.columns:
            return pd.DataFrame()
        
        # === ÉTAPE 2: CONVERTIR D'ABORD POUR ÉVITER LES AMBIGUÏTÉS ===
        df_converted = convert_to_eur_for_display(df)
        
        # === ÉTAPE 3: REGROUPEMENT SÉCURISÉ ===
        required_columns = ["Ticker", "Entreprise", "Quantity", "Purchase value", "Current value"]
        available_columns = [col for col in required_columns if col in df_converted.columns]
        
        if len(available_columns) < 2:  # Au minimum Ticker + 1 autre colonne
            st.warning("⚠️ Colonnes insuffisantes pour le regroupement")
            return pd.DataFrame()
        
        # Regroupement avec gestion d'erreur
        grouped = df_converted.groupby("Ticker").agg({
            "Entreprise": "first",
            "Quantity": "sum",
            "Purchase value": "sum",
            "Current value": "sum",
            "Compte": lambda x: ', '.join(sorted(set(x.dropna().astype(str)))),
            "Type": "first",
            "Secteur": "first",
            "Category": "first",
            "Units": "first"
        }).reset_index()
        
        return grouped
        
    except Exception as e:
        st.error(f"❌ Erreur lors du regroupement avec devises: {e}")
        return pd.DataFrame()


def get_real_time_data_optimized(tickers: List[str]) -> Dict[str, Dict]:
    """
    Version optimisée pour récupérer les données temps réel
    """
    cache_manager = get_cache_manager()
    
    # Récupérer les données de prix
    price_data = cache_manager.get_bulk_prices(tickers, period="2d")
    
    real_time_data = {}
    for ticker in tickers:
        try:
            if ticker in price_data and not price_data[ticker].empty:
                hist = price_data[ticker]
                if len(hist) >= 2:
                    current_price = hist["Close"].iloc[-1]
                    prev_close = hist["Close"].iloc[-2]
                    change = current_price - prev_close
                    change_percent = (change / prev_close * 100) if prev_close != 0 else 0
                    
                    # Récupérer les infos supplémentaires si nécessaire (mais en cache)
                    info = cache_manager.get_ticker_info(ticker)
                    
                    real_time_data[ticker] = {
                        'current_price': current_price,
                        'previous_close': prev_close,
                        'change': change,
                        'change_percent': change_percent,
                        'currency': info.get('currency', 'USD'),
                        'market_cap': info.get('marketCap', 'N/A'),
                        'volume': hist["Volume"].iloc[-1] if "Volume" in hist.columns else 'N/A'
                    }
                else:
                    real_time_data[ticker] = {
                        'current_price': None, 'previous_close': None, 
                        'change': None, 'change_percent': None,
                        'currency': 'USD', 'market_cap': 'N/A', 'volume': 'N/A'
                    }
        except Exception as e:
            st.warning(f"⚠️ Erreur données temps réel pour {ticker}: {e}")
            real_time_data[ticker] = {
                'current_price': None, 'previous_close': None,
                'change': None, 'change_percent': None,
                'currency': 'USD', 'market_cap': 'N/A', 'volume': 'N/A'
            }
    
    return real_time_data


def debug_dataframe_for_series_errors(df, context="Unknown"):
    """
    🔧 FONCTION DE DEBUG pour identifier les sources d'erreur "Series is ambiguous"
    """
    try:
        print(f"\n🔍 DEBUG DataFrame - Contexte: {context}")
        print(f"  - Shape: {df.shape}")
        print(f"  - Colonnes: {list(df.columns)}")
        
        if "Units" in df.columns:
            units_counts = df["Units"].value_counts()
            print(f"  - Devises: {dict(units_counts)}")
            
            # Vérifier les valeurs problématiques
            null_units = df["Units"].isnull().sum()
            if null_units > 0:
                print(f"  - ⚠️ {null_units} valeurs nulles dans Units")
        
        return True
        
    except Exception as e:
        print(f"  - ❌ Erreur debug: {e}")
        return False


def display_cache_debug_info():
    """Afficher les informations de debug du cache"""
    cache_manager = get_cache_manager()
    status = cache_manager.get_cache_status()
    
    with st.expander("🔧 Debug Cache yfinance", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Prix en cache", status['prix_en_cache'])
            st.metric("Infos en cache", status['infos_en_cache'])
        
        with col2:
            st.metric("Taux EUR/USD", f"{status['taux_eurusd_actuel']:.4f}")
            st.write(f"**Dernière MAJ EUR/USD:** {status['derniere_maj_eurusd'].strftime('%H:%M:%S')}")
        
        with col3:
            if st.button("🗑️ Vider le cache"):
                cache_manager.clear_cache()
                st.success("Cache vidé!")
                st.rerun()
