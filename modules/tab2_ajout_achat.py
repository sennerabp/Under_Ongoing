import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
import yfinance as yf
from modules.tab0_constants import SECTEUR_PAR_TYPE, CATEGORY_LIST, SECTOR_COLORS, save_to_excel

# 🔥 IMPORT POUR L'ACTUALISATION AUTOMATIQUE
from modules.yfinance_cache_manager import update_portfolio_prices_optimized

def search_ticker_info(ticker):
    """
    🔍 Rechercher les informations d'un ticker avec yfinance + GESTION RATE LIMIT
    """
    try:
        # 🔥 UTILISER LE CACHE MANAGER EXISTANT
        from modules.yfinance_cache_manager import get_cache_manager
        cache_manager = get_cache_manager()
        
        # Récupérer les infos avec gestion de cache et rate limit
        info = cache_manager.get_ticker_info(ticker)
        
        if info and 'longName' in info:
            return {
                'found': True,
                'name': info.get('longName', ticker),
                'sector': info.get('sector', 'Non défini'),
                'industry': info.get('industry', 'Non défini'),
                'currency': info.get('currency', 'USD'),
                'market_cap': info.get('marketCap', 0),
                'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0))
            }
        else:
            # 🔥 FALLBACK : Si pas d'infos mais ticker valide, créer une réponse basique
            if len(ticker) >= 2 and ticker.isalpha():
                st.warning(f"⚠️ Infos limitées pour {ticker}, utilisation des données par défaut")
                return {
                    'found': True,
                    'name': ticker,
                    'sector': 'Technology',  # Défaut le plus courant
                    'industry': 'Software',
                    'currency': 'USD' if not ticker.endswith('.PA') else 'EUR',
                    'market_cap': 0,
                    'current_price': 0
                }
            return {'found': False}
            
    except Exception as e:
        error_msg = str(e).lower()
        if 'rate limit' in error_msg or 'too many requests' in error_msg:
            st.warning(f"⏳ Limite de requêtes atteinte pour {ticker}. Utilisation des données en cache ou par défaut.")
            
            # 🔥 STRATÉGIE DE FALLBACK INTELLIGENTE
            if len(ticker) >= 2 and ticker.isalpha():
                # Détecter le marché par le suffixe
                if ticker.endswith('.PA'):  # Actions françaises
                    default_currency = 'EUR'
                    default_sector = 'Technology'
                elif ticker.endswith('.L'):  # Actions londoniennes
                    default_currency = 'GBP'
                    default_sector = 'Technology'
                else:  # Actions US par défaut
                    default_currency = 'USD'
                    default_sector = 'Technology'
                
                return {
                    'found': True,
                    'name': f"{ticker} (données limitées)",
                    'sector': default_sector,
                    'industry': 'Software',
                    'currency': default_currency,
                    'market_cap': 0,
                    'current_price': 0,
                    'rate_limited': True  # Flag pour indiquer des données limitées
                }
        
        return {'found': False, 'error': str(e)}

def map_to_categories(sector, industry):
    """
    🗂️ Mapper automatiquement les secteurs yfinance vers nos catégories
    """
    # Mapping des secteurs yfinance vers nos types/secteurs
    sector_mapping = {
        # Technology
        'Technology': {'Type': 'Actions', 'Secteur': 'Sensible', 'Category': 'Technologie'},
        'Communication Services': {'Type': 'Actions', 'Secteur': 'Sensible', 'Category': 'Services de communication'},
        
        # Healthcare
        'Healthcare': {'Type': 'Actions', 'Secteur': 'Défensif', 'Category': 'Santé'},
        
        # Financial
        'Financial Services': {'Type': 'Actions', 'Secteur': 'Cyclique', 'Category': 'Services financiers'},
        'Financial': {'Type': 'Actions', 'Secteur': 'Cyclique', 'Category': 'Services financiers'},
        
        # Consumer
        'Consumer Cyclical': {'Type': 'Actions', 'Secteur': 'Cyclique', 'Category': 'Consommation cyclique'},
        'Consumer Defensive': {'Type': 'Actions', 'Secteur': 'Défensif', 'Category': 'Consommation de base'},
        
        # Industrial
        'Industrials': {'Type': 'Actions', 'Secteur': 'Sensible', 'Category': 'Industrie'},
        
        # Energy
        'Energy': {'Type': 'Actions', 'Secteur': 'Sensible', 'Category': 'Energie'},
        
        # Materials
        'Basic Materials': {'Type': 'Actions', 'Secteur': 'Cyclique', 'Category': 'Matériaux de base'},
        
        # Utilities
        'Utilities': {'Type': 'Actions', 'Secteur': 'Défensif', 'Category': 'Service aux collectivités'},
        
        # Real Estate
        'Real Estate': {'Type': 'Actions', 'Secteur': 'Cyclique', 'Category': 'Services financiers'}
    }
    
    # Détection ETF dans le nom/industry
    if 'ETF' in industry.upper() or 'FUND' in industry.upper():
        if 'S&P' in industry.upper() or 'SPY' in industry.upper():
            return {'Type': 'ETF', 'Secteur': 'ETF', 'Category': 'S&P500'}
        elif 'NASDAQ' in industry.upper() or 'QQQ' in industry.upper():
            return {'Type': 'ETF', 'Secteur': 'ETF', 'Category': 'NASDAQ 100'}
        elif 'EURO' in industry.upper() or 'STOXX' in industry.upper():
            return {'Type': 'ETF', 'Secteur': 'ETF', 'Category': 'Euro STOXX50'}
        else:
            return {'Type': 'ETF', 'Secteur': 'ETF', 'Category': 'S&P500'}
    
    # Retourner le mapping ou valeur par défaut
    return sector_mapping.get(sector, {
        'Type': 'Actions', 
        'Secteur': 'Sensible', 
        'Category': 'Technologie'
    })

def display_tab2_ajout_achat():
    """
    Tab 2 – Ajout d'un nouvel achat dans le portefeuille
    🔥 VERSION COMPATIBLE PORTFOLIO VIDE + RECHERCHE TICKER + ACTUALISATION AUTO !
    """
    st.header("➕ Ajouter un achat")
    
    # 🔥 GUARD CLAUSE MODIFIÉE : Vérifier si un portfolio valide est chargé (peut être vide)
    def has_valid_portfolio():
        """Vérifier si un portfolio valide est chargé (peut être vide mais structuré)"""
        return (
            "df_data" in st.session_state and 
            st.session_state.df_data is not None and
            "input_file_path" in st.session_state and 
            st.session_state.input_file_path and 
            os.path.exists(st.session_state.input_file_path)
        )
    
    if not has_valid_portfolio():
        st.info("💡 Aucun fichier Excel chargé. Veuillez importer votre fichier dans la barre latérale ou créer un nouveau portfolio.")
        return
    
    # 🔥 INITIALISATION SÉCURISÉE DU DATAFRAME
    df = st.session_state.df_data.copy()
    
    # S'assurer que toutes les colonnes nécessaires existent
    required_columns = [
        "Date", "Compte", "Ticker", "Type", "Secteur", "Category", 
        "Entreprise", "Quantity", "Purchase price", "Purchase value", 
        "Current price", "Current value", "Units"
    ]
    
    for col in required_columns:
        if col not in df.columns:
            df[col] = None
    
    # Nettoyer les noms de colonnes
    df.columns = df.columns.str.strip()
    
    # 🔥 FIX CRITIQUE : S'assurer que la colonne Units existe et est bien formatée
    if "Units" not in df.columns:
        df["Units"] = "EUR"  # Valeur par défaut
    
    # 🔥 NETTOYER la colonne Units pour éviter les ambiguïtés
    df["Units"] = df["Units"].fillna("EUR").astype(str)
    
    # Mettre à jour le session_state avec les données nettoyées
    st.session_state.df_data = df
    
    # === GESTION PORTFOLIO VIDE ===
    if df.empty:
        st.info("📊 Portfolio vide - Premier investissement à ajouter !")
        existing_tickers = []
    else:
        existing_tickers = sorted(df["Ticker"].dropna().unique().tolist())
    
    # === SECTION CHOIX DU TICKER ===
    st.markdown("### 🎯 Sélection du titre")
    
    # Choix entre existant et nouveau
    if existing_tickers:
        choix_mode = st.radio(
            "Mode de saisie :",
            ["📋 Choisir un ticker existant", "🆕 Nouveau ticker"],
            horizontal=True
        )
    else:
        choix_mode = "🆕 Nouveau ticker"
        st.info("💡 Aucun ticker existant - Saisie d'un nouveau ticker")
    
    ticker_info = None
    auto_data = None
    
    if choix_mode == "📋 Choisir un ticker existant" and existing_tickers:
        # === TICKER EXISTANT ===
        ticker = st.selectbox("Choisir un ticker", options=existing_tickers)
        row = df[df["Ticker"] == ticker].iloc[0] if ticker in df["Ticker"].values else None
        
        if row is not None:
            st.success("ℹ️ Données récupérées automatiquement du portefeuille.")
            auto_data = {
                'Type': row["Type"],
                'Secteur': row["Secteur"],
                'Category': row["Category"],
                'Entreprise': row["Entreprise"]
            }
    else:
        # === NOUVEAU TICKER AVEC RECHERCHE ===
        st.markdown("#### 🔍 Recherche automatique d'informations")
        
        col_search, col_button = st.columns([3, 1])
        
        with col_search:
            ticker_input = st.text_input(
                "Entrer le ticker (ex: AAPL, GOOGL, NVDA...)",
                placeholder="AAPL",
                help="Saisissez le symbole boursier du titre"
            )
        
        with col_button:
            st.markdown("<br>", unsafe_allow_html=True)  # Espacement
            search_clicked = st.button("🔍 Rechercher", type="primary")
        
        ticker = ticker_input.upper() if ticker_input else ""
        
        # Recherche automatique si ticker saisi
        if ticker and (search_clicked or len(ticker) >= 3):
            with st.spinner(f"🔍 Recherche des informations pour {ticker}..."):
                ticker_info = search_ticker_info(ticker)
            
            if ticker_info['found']:
                # === AFFICHAGE DES INFOS TROUVÉES ===
                if ticker_info.get('rate_limited'):
                    st.warning(f"⚠️ Ticker {ticker} trouvé avec données limitées (rate limit Yahoo Finance)")
                else:
                    st.success(f"✅ Ticker {ticker} trouvé !")
                
                col_info1, col_info2 = st.columns(2)
                
                with col_info1:
                    st.markdown("**📊 Informations générales :**")
                    st.write(f"**Nom :** {ticker_info['name']}")
                    st.write(f"**Secteur :** {ticker_info['sector']}")
                    st.write(f"**Industrie :** {ticker_info['industry']}")
                
                with col_info2:
                    st.markdown("**💰 Données financières :**")
                    st.write(f"**Devise :** {ticker_info['currency']}")
                    if ticker_info['current_price'] > 0:
                        st.write(f"**Prix actuel :** {ticker_info['current_price']:.2f} {ticker_info['currency']}")
                    else:
                        st.write("**Prix actuel :** Non disponible (sera mis à jour après ajout)")
                    
                    if ticker_info['market_cap'] > 0:
                        cap_formatted = f"{ticker_info['market_cap']/1e9:.1f}Md" if ticker_info['market_cap'] > 1e9 else f"{ticker_info['market_cap']/1e6:.0f}M"
                        st.write(f"**Capitalisation :** {cap_formatted} {ticker_info['currency']}")
                    else:
                        st.write("**Capitalisation :** Non disponible")
                
                # === MAPPING AUTOMATIQUE ===
                auto_mapping = map_to_categories(ticker_info['sector'], ticker_info['industry'])
                
                st.markdown("**🗂️ Catégorisation automatique suggérée :**")
                col_cat1, col_cat2, col_cat3 = st.columns(3)
                with col_cat1:
                    st.info(f"**Type :** {auto_mapping['Type']}")
                with col_cat2:
                    st.info(f"**Secteur :** {auto_mapping['Secteur']}")
                with col_cat3:
                    st.info(f"**Catégorie :** {auto_mapping['Category']}")
                
                # 🔥 INFORMATION ADDITIONNELLE SI RATE LIMITED
                if ticker_info.get('rate_limited'):
                    st.info("💡 **Astuce :** Les informations complètes seront récupérées automatiquement lors de l'actualisation des cours après ajout.")
                
                # Préparer les données automatiques
                auto_data = {
                    'Type': auto_mapping['Type'],
                    'Secteur': auto_mapping['Secteur'],
                    'Category': auto_mapping['Category'],
                    'Entreprise': ticker_info['name']
                }
                
            elif ticker:
                st.error(f"❌ Ticker {ticker} non trouvé ou données indisponibles.")
                if 'error' in ticker_info:
                    error_msg = ticker_info['error']
                    if 'rate limit' in error_msg.lower():
                        st.warning("⏳ **Rate limit temporaire.** Vous pouvez continuer l'ajout, les données seront récupérées lors de l'actualisation automatique.")
                    else:
                        st.warning(f"Erreur : {error_msg}")
                st.info("💡 Vous pouvez continuer avec une saisie manuelle ci-dessous.")
    
    # === SECTION INFORMATIONS DU TITRE ===
    st.markdown("---")
    st.markdown("### 📝 Informations du titre")
    
    if auto_data:
        st.info("ℹ️ Données récupérées automatiquement. Vous pouvez les modifier si nécessaire.")
        type_ = st.selectbox("Type d'actif", list(SECTEUR_PAR_TYPE.keys()), 
                            index=list(SECTEUR_PAR_TYPE.keys()).index(auto_data['Type']))
        secteur_ = st.selectbox("Secteur", SECTEUR_PAR_TYPE.get(type_, []), 
                               index=SECTEUR_PAR_TYPE.get(type_, []).index(auto_data['Secteur']) if auto_data['Secteur'] in SECTEUR_PAR_TYPE.get(type_, []) else 0)
        categorie = st.selectbox("Catégorie", CATEGORY_LIST.get(secteur_, []), 
                                index=CATEGORY_LIST.get(secteur_, []).index(auto_data['Category']) if auto_data['Category'] in CATEGORY_LIST.get(secteur_, []) else 0)
        entreprise = st.text_input("Nom de l'entreprise", value=auto_data['Entreprise'])
    else:
        st.info("💡 Veuillez renseigner les informations manuellement.")
        type_ = st.selectbox("Type d'actif", list(SECTEUR_PAR_TYPE.keys()))
        secteur_ = st.selectbox("Secteur", SECTEUR_PAR_TYPE.get(type_, []))
        categorie = st.selectbox("Catégorie", CATEGORY_LIST.get(secteur_, []))
        entreprise = st.text_input("Nom de l'entreprise")
    
    # === SECTION DÉTAILS DE L'ACHAT ===
    st.markdown("---")
    st.markdown("### 💰 Détails de l'achat")
    
    # 🔥 SÉLECTEUR DE DEVISE HORS FORMULAIRE (RÉACTIF)
    col_devise_compte, _ = st.columns([1, 1])
    with col_devise_compte:
        devise = st.selectbox("💱 Devise", ["EUR", "USD"], key="devise_selector")
        
    with st.form("ajout_final_formulaire"):
        col_form1, col_form2 = st.columns(2)
        
        with col_form1:
            date = st.date_input("📅 Date", value=datetime.today())
            compte = st.selectbox("🏦 Compte", ["PEA", "CTO"])
            # 🔥 AFFICHAGE DEVISE SÉLECTIONNÉE (lecture seule dans le form)
            st.write(f"💱 **Devise sélectionnée :** {devise}")
        
        with col_form2:
            quantity = st.number_input("📊 Quantité", min_value=0.0, step=1.0, format="%.2f")
            # 🔥 LABEL RÉACTIF BASÉ SUR LA DEVISE SÉLECTIONNÉE
            prix_achat = st.number_input(f"💵 Prix d'achat ({devise})", min_value=0.0, step=0.01, format="%.4f")
            
            # Affichage du montant total
            if quantity > 0 and prix_achat > 0:
                montant_total = quantity * prix_achat
                st.metric("💰 Montant total", f"{montant_total:,.2f} {devise}")
        
        # Bouton de validation
        submit = st.form_submit_button("✅ Ajouter l'investissement", type="primary", use_container_width=True)
        
    # === TRAITEMENT DE L'AJOUT ===
    if submit:
        # Validations
        if not ticker:
            st.error("⚠️ Veuillez saisir un ticker.")
            return
            
        if quantity <= 0 or prix_achat <= 0:
            st.error("⚠️ La quantité et le prix d'achat doivent être supérieurs à 0.")
            return
            
        if not entreprise.strip():
            st.error("⚠️ Veuillez saisir le nom de l'entreprise.")
            return
        
        # 🔥 CRÉER LA NOUVELLE LIGNE AVEC CONTRÔLE STRICT
        new_row = pd.DataFrame([{
            "Date": pd.to_datetime(date),
            "Compte": str(compte),
            "Ticker": str(ticker),
            "Type": str(type_),
            "Secteur": str(secteur_),
            "Category": str(categorie),
            "Entreprise": str(entreprise.strip()),
            "Quantity": float(quantity),
            "Purchase price": float(prix_achat),
            "Purchase value": float(quantity * prix_achat),
            "Current price": None,
            "Current value": None,
            "Units": str(devise)  # 🔥 UTILISE LA DEVISE SÉLECTIONNÉE
        }])
        
        # 🔥 GESTION SPÉCIALE POUR PORTFOLIO VIDE
        try:
            if df.empty:
                # Pour un portfolio vide, utiliser directement la nouvelle ligne
                df_updated = new_row.copy()
                st.info("🎉 Premier investissement ajouté au portfolio !")
            else:
                # S'assurer que les types sont compatibles avant concat
                df_original = st.session_state.df_data.copy()
                
                # Aligner les colonnes et types
                for col in new_row.columns:
                    if col in df_original.columns:
                        # Convertir la colonne existante au même type si nécessaire
                        if col == "Units":
                            df_original[col] = df_original[col].fillna("EUR").astype(str)
                        elif col in ["Compte", "Ticker", "Type", "Secteur", "Category", "Entreprise"]:
                            df_original[col] = df_original[col].astype(str)
                
                # Concaténation
                df_updated = pd.concat([df_original, new_row], ignore_index=True)
            
            # 🔥 NETTOYER ENCORE UNE FOIS APRÈS CONCAT OU PREMIÈRE LIGNE
            df_updated["Units"] = df_updated["Units"].fillna("EUR").astype(str)
            
            # Mettre à jour le session state
            st.session_state.df_data = df_updated
            st.session_state.data_modified = True
            st.session_state.current_values_updated = False  # Force refresh des prix
            
            # Mettre à jour le nom du fichier avec la date actuelle
            if "base_filename" in st.session_state:
                today_str = datetime.today().strftime('%Y%m%d')
                st.session_state.save_filename = f"{st.session_state.base_filename}_{today_str}.xlsx"
            
            # 🔥 NOUVEAUTÉ : ACTUALISATION AUTOMATIQUE DES COURS
            with st.spinner("💾 Sauvegarde et actualisation des cours..."):
                # Sauvegarder d'abord
                success_save = save_to_excel()
                
                if success_save:
                    # Puis actualiser les cours automatiquement
                    df_with_prices = update_portfolio_prices_optimized(df_updated)
                    st.session_state.df_data = df_with_prices
                    
                    # Sauvegarder à nouveau avec les nouveaux prix
                    success_final = save_to_excel()
                    
                    if success_final:
                        st.success(f"✅ Investissement {ticker} ({entreprise}) ajouté avec succès!")
                        st.success(f"💰 Montant: {quantity} × {prix_achat} {devise} = {quantity * prix_achat:,.2f} {devise}")
                        st.success("📈 Cours automatiquement mis à jour!")
                        st.info("💡 Actualisation automatique des autres onglets...")
                        
                        # Actualiser automatiquement après ajout réussi
                        st.rerun()
                    else:
                        st.warning("⚠️ Investissement ajouté mais erreur lors de la sauvegarde finale")
                else:
                    st.error("❌ Erreur lors de la sauvegarde initiale")
                
        except Exception as e:
            st.error(f"❌ Erreur lors de l'ajout : {e}")
            
            # Debug en mode développement
            with st.expander("🔍 Informations de debug", expanded=False):
                st.write(f"**Types de données:** devise={type(devise)}, ticker={type(ticker)}")
                st.write(f"**Portfolio vide:** {df.empty}")
                if not df.empty:
                    st.write(f"**Colonnes DataFrame:** {list(st.session_state.df_data.columns)}")
                    if "Units" in st.session_state.df_data.columns:
                        st.write(f"**Types Units existants:** {st.session_state.df_data['Units'].dtype}")
                        st.write(f"**Valeurs Units:** {st.session_state.df_data['Units'].unique()}")
                st.write(f"**Erreur complète:** {str(e)}")
