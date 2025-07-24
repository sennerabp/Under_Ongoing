import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import yfinance as yf
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def display_tab8_analyse():
    st.title("🔍 Analyse complète d'une société")
    st.markdown("### 🚀 TLB INVESTOR - Validateur Automatisé")

    # Interface de recherche dans le contenu principal
    col1, col2 = st.columns([3, 1])
    
    with col1:
        ticker = st.text_input(
            "🎯 Entrez le symbole de l'entreprise", 
            key="ticker_complete",
            placeholder="Ex: AAPL pour Apple, MSFT pour Microsoft, MC.PA pour LVMH...",
            help="Le ticker est le code boursier de l'entreprise. Ajoutez .PA pour les actions françaises"
        )
    
    with col2:
        st.markdown("**[🔍 Rechercher un ticker](https://finance.yahoo.com/lookup/)**")

    # Analyser automatiquement si un ticker est saisi
    if ticker:
        analyze_company(ticker.upper())
    else:
        # Instructions d'utilisation si pas de ticker
        display_instructions()

def analyze_company(ticker):
    """Analyser une entreprise complètement"""
    
    try:
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("🔄 Récupération des données...")
        progress_bar.progress(20)
        
        # Récupération des données
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="max")
        
        if not info or 'longName' not in info:
            st.error(f"❌ Impossible de trouver les données pour {ticker}")
            progress_bar.empty()
            status_text.empty()
            return
        
        progress_bar.progress(50)
        status_text.text("📊 Calcul des métriques...")
        
        # Calcul des métriques
        metrics_data = calculate_all_metrics(info, hist)
        
        progress_bar.progress(80)
        status_text.text("📋 Génération du rapport...")
        
        # === EN-TÊTE DE L'ANALYSE ===
        st.markdown("---")
        display_company_header(info, ticker)
        
        # === EXPLICATION DES INDICES ===
        st.markdown("---")
        display_indices_explanation()
        
        # === GRAPHIQUES DE PERFORMANCE ===
        st.markdown("---")
        display_price_chart(hist, info)
        
        # === TABLEAU D'ANALYSE PRINCIPAL ===
        st.markdown("---")
        display_metrics_table(metrics_data, info)
        
        # === RÉSUMÉ DES SCORES ===
        st.markdown("---")
        display_score_summary(metrics_data)
        
        # === GRAPHIQUE RADAR ===
        st.markdown("---")
        display_radar_chart(metrics_data)
        
        progress_bar.progress(100)
        status_text.text("✅ Analyse terminée !")
        
        # Nettoyage après 1 seconde
        import time
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        
    except Exception as e:
        st.error(f"❌ Erreur lors de l'analyse : {str(e)}")
        st.info("💡 Vérifiez que le symbole est correct (ex: AAPL, GOOGL, MSFT, MC.PA pour LVMH)")
        if 'progress_bar' in locals():
            progress_bar.empty()
        if 'status_text' in locals():
            status_text.empty()

def display_instructions():
    """Afficher les instructions d'utilisation"""
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 💡 Exemples de symboles :
        - **🇺🇸 USA :** AAPL, MSFT, GOOGL, TSLA
        - **🇫🇷 France :** MC.PA, OR.PA, AI.PA, BNP.PA
        - **🇩🇪 Allemagne :** SAP.DE, VOW3.DE
        """)
    
    with col2:
        st.markdown("""
        ### 🔍 Comment utiliser :
        
        **1. Saisir le ticker** de l'entreprise
        **2. Analyser les résultats** avec les tooltips
        **3. Consulter le radar** pour une vue synthétique
        **4. Vérifier les critères** éliminatoires
        
        Utilisez le **guide des indices** pour comprendre chaque métrique !
        """)

def display_indices_explanation():
    """Afficher l'explication des indices financiers"""
    
    st.header("📚 Guide des Indices Financiers")
    
    with st.expander("📖 Cliquez pour voir les explications des indices", expanded=False):
        
        st.markdown("""
        ### 📈 **VALORISATION**
        
        **PER (Price Earnings Ratio)** : Prix payé pour 1€ de bénéfice annuel
        - *Plus le PER est bas, moins l'action est chère*
        - Exemple : PER de 15 = vous payez 15€ pour chaque 1€ de bénéfice
        
        **PEG (Price Earnings to Growth)** : PER ajusté de la croissance
        - *<1 = croissance pas chère, >1 = croissance chère*
        - Permet de savoir si la croissance justifie le prix
        
        **P/B (Price to Book)** : Prix vs valeur comptable
        - *<1 = action cotée en dessous de sa valeur comptable*
        - Mesure si l'entreprise vaut plus ou moins que ses actifs nets
        
        **P/S (Price to Sales)** : Prix vs chiffre d'affaires
        - *Varie selon le secteur d'activité*
        - Utile pour comparer des entreprises du même secteur
        
        **EV/Revenue** : Valeur d'entreprise vs revenus
        - *Mesure la valorisation totale incluant la dette*
        - Plus précis que P/S car inclut l'endettement
        
        **EV/EBITDA** : Valeur d'entreprise vs bénéfices avant amortissements
        - *Standard du marché pour comparer les entreprises*
        - Élimine les effets comptables et fiscaux
        
        ---
        
        ### 💰 **RENTABILITÉ**
        
        **Marge Brute** : Profit après coûts de production
        - *Varie énormément selon l'industrie*
        - Montre l'efficacité de la production
        
        **Marge Opérationnelle** : Efficacité opérationnelle
        - *>15% = très bon niveau d'efficacité*
        - Mesure la rentabilité des opérations courantes
        
        **Marge Nette** : Profit final après tous les coûts
        - *>10% = entreprise très rentable*
        - Le ratio le plus important pour la rentabilité
        
        **ROE (Return on Equity)** : Rendement des capitaux propres
        - *>15% = excellente gestion des fonds*
        - Mesure l'efficacité de l'utilisation de l'argent des actionnaires
        
        **ROA (Return on Assets)** : Efficacité d'utilisation des actifs
        - *>7% = très bonne utilisation des actifs*
        - Montre si l'entreprise génère du profit avec ses actifs
        
        ---
        
        ### 🚀 **CROISSANCE**
        
        **Croissance CA** : Évolution du chiffre d'affaires
        - *>10% = forte croissance d'activité*
        - Indique si l'entreprise gagne des parts de marché
        
        **Croissance Bénéfices** : Évolution des profits
        - *Plus importante que la croissance du CA*
        - Une entreprise peut croître sans être plus rentable
        
        **Croissance Trimestrielle** : Tendances récentes
        - *Permet de voir les dernières évolutions*
        - Important pour détecter les changements de tendance
        
        ---
        
        ### 🛡️ **SOLIDITÉ FINANCIÈRE**
        
        **Dette/Capitaux** : Niveau d'endettement
        - *<30% = structure financière très saine*
        - Trop de dette peut mettre l'entreprise en danger
        
        **Ratio de Liquidité** : Capacité à payer les dettes court terme
        - *>1.5 = bon niveau de sécurité financière*
        - Mesure si l'entreprise peut faire face à ses obligations
        
        **Trésorerie** : Liquidités disponibles
        - *Dépend de la taille de l'entreprise*
        - Importante pour résister aux crises
        
        **Free Cash Flow** : Argent généré après investissements
        - *Crucial pour la santé financière*
        - Permet dividendes, rachats d'actions, croissance
        
        ---
        
        ### 💎 **DIVIDENDES & PERFORMANCE**
        
        **Rendement Dividende** : Dividende annuel / Prix de l'action
        - *3-5% = niveau idéal*
        - Trop haut peut signaler des problèmes
        
        **Taux de Distribution** : Part des bénéfices distribués
        - *<80% = dividende durable*
        - >100% = dividende en danger
        
        **Bêta** : Volatilité vs marché
        - *<1 = moins volatil que le marché*
        - Mesure le risque de l'action
        
        **Performance Historique** : Évolution du cours
        - *Importante pour juger la qualité de gestion*
        - Performance 5 ans très révélatrice
        """)

def display_company_header(info, ticker):
    """Afficher l'en-tête de l'entreprise avec informations complètes"""
    
    st.markdown("### 🏢 Informations générales")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        company_name = info.get('longName', ticker)
        st.metric("🏢 Entreprise", company_name[:20] + "..." if len(company_name) > 20 else company_name)
        
    with col2:
        sector = info.get('sector', 'Non défini')
        st.metric("🏭 Secteur", sector)
        
    with col3:
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        currency = info.get('currency', 'USD')
        if current_price:
            st.metric("💰 Prix", f"{current_price:.2f} {currency}")
        
    with col4:
        market_cap = info.get('marketCap', 0)
        if market_cap:
            if market_cap >= 1e12:
                cap_str = f"{market_cap/1e12:.1f}T"
            elif market_cap >= 1e9:
                cap_str = f"{market_cap/1e9:.1f}Md"
            else:
                cap_str = f"{market_cap/1e6:.0f}M"
            st.metric("📊 Capitalisation", f"{cap_str} {info.get('currency', 'USD')}")

    # === SECTION VIE DE L'ENTREPRISE AUTOMATISÉE ===
    st.markdown("---")
    st.markdown("### 🌟 Vie de l'entreprise")
    
    # Récupération automatique des informations
    business_summary = info.get('longBusinessSummary', 'Non disponible')
    country = info.get('country', 'Non spécifié')
    city = info.get('city', 'Non spécifié')
    website = info.get('website', 'Non disponible')
    employees = info.get('fullTimeEmployees', 'Non disponible')
    industry = info.get('industry', 'Non spécifié')
    
    # Affichage des informations de base
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.markdown("**🌍 Localisation :**")
        st.write(f"📍 **Siège social :** {city}, {country}")
        if website != 'Non disponible':
            st.write(f"🌐 **Site web :** [{website}]({website})")
        if employees != 'Non disponible':
            st.write(f"👥 **Employés :** {employees:,}")
        st.write(f"🏭 **Industrie :** {industry}")
    
    with col_info2:
        st.markdown("**📋 Activité principale :**")
        if business_summary != 'Non disponible':
            # Limiter la description à 400 caractères
            summary_short = business_summary[:400] + "..." if len(business_summary) > 400 else business_summary
            st.write(summary_short)
        else:
            st.write("Description non disponible")

    # === CRITÈRES TLB AUTOMATIQUES ===
    st.markdown("---")
    st.markdown("### 🎯 Critères TLB INVESTOR - Vie de l'entreprise")
    
    # Analyse automatique des critères TLB
    analyze_tlb_criteria_auto(info, ticker)

def analyze_tlb_criteria_auto(info, ticker):
    """Analyser automatiquement les critères TLB INVESTOR"""
    
    col_tlb1, col_tlb2 = st.columns(2)
    
    with col_tlb1:
        st.markdown("**🏆 Analyse de position :**")
        
        # Position sur le marché basée sur la capitalisation
        market_cap = info.get('marketCap', 0)
        if market_cap:
            market_cap_mds = market_cap / 1e9
            if market_cap_mds > 500:
                position_marche = "🟢 Mega Cap - Leader probable"
                position_score = 2
            elif market_cap_mds > 100:
                position_marche = "🔵 Large Cap - Top player"
                position_score = 1
            elif market_cap_mds > 10:
                position_marche = "🟡 Mid Cap - Challenger"
                position_score = 0
            else:
                position_marche = "🔴 Small Cap - Acteur mineur"
                position_score = -1
        else:
            position_marche = "❓ Position indéterminée"
            position_score = 0
        
        st.write(f"📊 **Position marché :** {position_marche}")
        
        # Complexité de l'activité basée sur le secteur
        sector = info.get('sector', '').lower()
        industry = info.get('industry', '').lower()
        
        simple_sectors = ['consumer defensive', 'utilities', 'real estate']
        complex_sectors = ['technology', 'healthcare', 'financial services']
        
        if any(s in sector for s in simple_sectors):
            complexite = "🟢 Activité simple à comprendre"
            complexite_score = 1
        elif any(s in sector for s in complex_sectors):
            complexite = "🟡 Activité moyennement complexe"
            complexite_score = 0
        else:
            complexite = "🔴 Activité complexe"
            complexite_score = -1
            
        st.write(f"🧠 **Complexité :** {complexite}")
        
        # État actionnaire (approximation basée sur le pays)
        country = info.get('country', '').lower()
        if 'china' in country:
            etat_actionnaire = "🔴 Risque État actionnaire (Chine)"
            etat_score = -2
        elif country in ['france', 'germany', 'italy']:
            etat_actionnaire = "🟡 État potentiellement actionnaire"
            etat_score = -1
        else:
            etat_actionnaire = "🟢 Pas d'État actionnaire apparent"
            etat_score = 1
            
        st.write(f"🏛️ **État actionnaire :** {etat_actionnaire}")
        
    with col_tlb2:
        st.markdown("**📈 Informations complémentaires :**")
        
        # Répartition géographique si disponible
        revenue_data = get_revenue_breakdown(info)
        if revenue_data:
            st.write("💼 **Répartition estimée :**")
            st.write(revenue_data)
        
        # Informations PDG et actualités
        ceo_info = get_ceo_info(info)
        if ceo_info:
            st.write("👔 **Direction :**")
            st.write(ceo_info)
        
        # Récupération des derniers articles
        news_headlines = get_recent_news(ticker)
        if news_headlines:
            st.write("📰 **Actualités récentes (PDG/Entreprise) :**")
            for i, headline in enumerate(news_headlines[:4], 1):
                st.write(f"**{i}.** {headline}")
        else:
            st.write("📰 **Actualités :** Non disponibles")
    
    # === SCORE TLB AUTOMATIQUE ===
    st.markdown("---")
    st.markdown("### 🏅 Évaluation TLB - Vie de l'entreprise")
    
    total_score = position_score + complexite_score + etat_score
    
    col_score1, col_score2 = st.columns(2)
    
    with col_score1:
        if total_score >= 3:
            st.success(f"🟢 **EXCELLENT** (Score: {total_score}/4)")
            recommendation = "Entreprise de qualité exceptionnelle"
        elif total_score >= 1:
            st.info(f"🔵 **BON** (Score: {total_score}/4)")
            recommendation = "Bonne entreprise, critères favorables"
        elif total_score >= -1:
            st.warning(f"🟡 **MOYEN** (Score: {total_score}/4)")
            recommendation = "Quelques points de vigilance"
        else:
            st.error(f"🔴 **DÉFAVORABLE** (Score: {total_score}/4)")
            recommendation = "Plusieurs critères défavorables"
    
    with col_score2:
        st.write(f"**💡 Recommandation :** {recommendation}")
        
        # Détail des points
        if position_score > 0:
            st.write("✅ Position de marché forte")
        if complexite_score > 0:
            st.write("✅ Activité compréhensible")
        if etat_score > 0:
            st.write("✅ Indépendance vis-à-vis de l'État")

def get_revenue_breakdown(info):
    """Obtenir une estimation de la répartition du CA"""
    
    # Informations basées sur le secteur et le pays
    country = info.get('country', '')
    sector = info.get('sector', '')
    
    # Estimations basiques selon le pays d'origine
    if country == 'United States':
        return "Estimation : 60% Amérique du Nord, 25% International, 15% Autres"
    elif country in ['Germany', 'France', 'United Kingdom']:
        return "Estimation : 50% Europe, 30% International, 20% Autres"
    elif country == 'China':
        return "Estimation : 70% Chine/Asie, 20% International, 10% Autres"
    else:
        return "Répartition géographique non estimable"

def get_ceo_info(info):
    """Récupérer les informations sur le PDG"""
    
    try:
        # Tentative de récupération des officiers
        officers = info.get('companyOfficers', [])
        if officers:
            ceo = next((officer for officer in officers if 'CEO' in officer.get('title', '').upper()), None)
            if ceo:
                name = ceo.get('name', 'Non disponible')
                age = ceo.get('age', 'Non disponible')
                title = ceo.get('title', 'CEO')
                result = f"**{title} :** {name}"
                if age != 'Non disponible':
                    result += f" ({age} ans)"
                return result
        
        return "Informations PDG non disponibles"
        
    except Exception:
        return "Informations PDG non disponibles"

def get_recent_news(ticker):
    """Récupérer les titres d'actualités récentes"""
    
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        
        headlines = []
        if news:
            for article in news[:4]:  # Limiter à 4 articles
                title = article.get('title', '')
                if title:
                    # Limiter la longueur du titre
                    title_short = title[:80] + "..." if len(title) > 80 else title
                    headlines.append(title_short)
        
        return headlines if headlines else None
        
    except Exception:
        return None

def calculate_all_metrics(info, hist):
    """Calculer toutes les métriques financières"""
    
    def safe_get(key, default=None):
        value = info.get(key, default)
        if value in [None, 'N/A', 0]:
            return default
        try:
            return float(value)
        except:
            return default
    
    # Dictionnaire pour stocker toutes les métriques
    metrics = {}
    
    # === VALORISATION ===
    metrics['PER'] = safe_get('trailingPE')
    metrics['PEG'] = safe_get('pegRatio')
    metrics['P/B'] = safe_get('priceToBook')
    metrics['P/S'] = safe_get('priceToSalesTrailing12Months')
    metrics['EV/Revenue'] = safe_get('enterpriseToRevenue')
    metrics['EV/EBITDA'] = safe_get('enterpriseToEbitda')
    
    # === RENTABILITÉ ===
    metrics['Marge Brute (%)'] = safe_get('grossMargins', 0) * 100 if safe_get('grossMargins') else None
    metrics['Marge Opérationnelle (%)'] = safe_get('operatingMargins', 0) * 100 if safe_get('operatingMargins') else None
    metrics['Marge Nette (%)'] = safe_get('profitMargins', 0) * 100 if safe_get('profitMargins') else None
    metrics['ROE (%)'] = safe_get('returnOnEquity', 0) * 100 if safe_get('returnOnEquity') else None
    metrics['ROA (%)'] = safe_get('returnOnAssets', 0) * 100 if safe_get('returnOnAssets') else None
    
    # === CROISSANCE ===
    metrics['Croissance CA (%)'] = safe_get('revenueGrowth', 0) * 100 if safe_get('revenueGrowth') else None
    metrics['Croissance Bénéfices (%)'] = safe_get('earningsGrowth', 0) * 100 if safe_get('earningsGrowth') else None
    metrics['Croissance CA Trim (%)'] = safe_get('quarterlyRevenueGrowth', 0) * 100 if safe_get('quarterlyRevenueGrowth') else None
    metrics['Croissance Bén Trim (%)'] = safe_get('quarterlyEarningsGrowth', 0) * 100 if safe_get('quarterlyEarningsGrowth') else None
    
    # Calcul des revenues des 5 dernières années
    try:
        stock = yf.Ticker(info.get('symbol', ''))
        financials = stock.financials
        if not financials.empty and 'Total Revenue' in financials.index:
            revenues = financials.loc['Total Revenue'].dropna()
            if len(revenues) >= 2:
                # Prendre les 5 dernières années disponibles
                recent_revenues = revenues.head(min(5, len(revenues)))
                revenue_values = []
                revenue_years = []
                
                for date, revenue in recent_revenues.items():
                    year = date.year
                    revenue_billions = revenue / 1e9  # Convertir en milliards
                    revenue_values.append(revenue_billions)
                    revenue_years.append(year)
                
                # Créer une chaîne avec les valeurs des 5 dernières années
                if len(revenue_values) >= 2:
                    revenue_trend = []
                    for i, (year, value) in enumerate(zip(revenue_years, revenue_values)):
                        if i < len(revenue_values) - 1:
                            growth = ((revenue_values[i] - revenue_values[i+1]) / revenue_values[i+1]) * 100
                            revenue_trend.append(f"{year}: {value:.1f}Md ({growth:+.1f}%)")
                        else:
                            revenue_trend.append(f"{year}: {value:.1f}Md")
                    
                    metrics['CA 5 ans'] = " | ".join(revenue_trend)
                else:
                    metrics['CA 5 ans'] = f"Données limitées: {revenue_values[0]:.1f}Md"
            else:
                metrics['CA 5 ans'] = "Données insuffisantes"
        else:
            metrics['CA 5 ans'] = "Non disponible"
    except Exception as e:
        metrics['CA 5 ans'] = "Erreur de récupération"
    
    # === SOLIDITÉ FINANCIÈRE ===
    metrics['Dette/Capitaux (%)'] = safe_get('debtToEquity', 0)
    metrics['Ratio Liquidité'] = safe_get('currentRatio')
    metrics['Ratio Liquidité Imm'] = safe_get('quickRatio')
    metrics['Trésorerie (Mds)'] = safe_get('totalCash', 0) / 1e9 if safe_get('totalCash') else None
    metrics['Free Cash Flow (Mds)'] = safe_get('freeCashflow', 0) / 1e9 if safe_get('freeCashflow') else None
    
    # === DIVIDENDES ===
    metrics['Rendement Dividende (%)'] = safe_get('dividendYield', 0) * 100 if safe_get('dividendYield') else None
    metrics['Taux Distribution (%)'] = safe_get('payoutRatio', 0) * 100 if safe_get('payoutRatio') else None
    metrics['Dividende/Action ($)'] = safe_get('dividendRate')
    
    # === PERFORMANCE ===
    if not hist.empty and len(hist) > 0:
        current_price = hist['Close'][-1]
        
        # Performance 1 an
        if len(hist) >= 252:
            price_1y_ago = hist['Close'][-252]
            metrics['Performance 1 an (%)'] = ((current_price - price_1y_ago) / price_1y_ago) * 100
        
        # Performance 3 ans
        if len(hist) >= 756:
            price_3y_ago = hist['Close'][-756]
            metrics['Performance 3 ans (%)'] = ((current_price - price_3y_ago) / price_3y_ago) * 100
        
        # Performance 5 ans
        if len(hist) >= 1260:
            price_5y_ago = hist['Close'][-1260]
            metrics['Performance 5 ans (%)'] = ((current_price - price_5y_ago) / price_5y_ago) * 100
        
        # Volatilité
        returns = hist['Close'].pct_change().dropna()
        if len(returns) > 0:
            metrics['Volatilité (%)'] = returns.std() * np.sqrt(252) * 100
    
    # === QUALITÉ ===
    metrics['Bêta'] = safe_get('beta')
    metrics['Capitalisation (Mds)'] = safe_get('marketCap', 0) / 1e9 if safe_get('marketCap') else None
    metrics['Volume Moyen'] = safe_get('averageVolume')
    metrics['Flottant (%)'] = safe_get('floatShares', 0) / safe_get('sharesOutstanding', 1) * 100 if safe_get('sharesOutstanding') else None
    
    return metrics

def display_price_chart(hist, info):
    """Afficher le graphique de prix avec sélection de période"""
    
    st.header("📈 Évolution du Prix de l'Action")
    
    if hist.empty:
        st.warning("Aucune donnée historique disponible")
        return
    
    # Sélecteur de période
    col1, col2 = st.columns([1, 4])
    
    with col1:
        period_options = {
            "Max": len(hist),
            "5 ans": min(1260, len(hist)),
            "1 an": min(252, len(hist)),
            "6 mois": min(126, len(hist)),
            "3 mois": min(63, len(hist))
        }
        
        selected_period = st.selectbox(
            "Période d'affichage",
            options=list(period_options.keys()),
            index=1
        )
    
    # Filtrer les données selon la période sélectionnée
    days_to_show = period_options[selected_period]
    hist_filtered = hist.tail(days_to_show)
    
    # Calculer la performance sur la période
    if len(hist_filtered) > 1:
        start_price = hist_filtered['Close'].iloc[0]
        end_price = hist_filtered['Close'].iloc[-1]
        performance = ((end_price - start_price) / start_price) * 100
        
        with col2:
            st.metric(
                f"Performance sur {selected_period.lower()}",
                f"{performance:+.1f}%",
                f"${end_price:.2f} actuel"
            )
    
    # Créer le graphique
    fig = go.Figure()
    
    # Ligne de prix principal
    fig.add_trace(go.Scatter(
        x=hist_filtered.index,
        y=hist_filtered['Close'],
        mode='lines',
        name='Prix de clôture',
        line=dict(color='#2ecc71', width=2),
        hovertemplate='<b>Date:</b> %{x}<br><b>Prix:</b> $%{y:.2f}<extra></extra>'
    ))
    
    # Ajouter des moyennes mobiles
    if len(hist_filtered) > 50:
        ma_50 = hist_filtered['Close'].rolling(window=50).mean()
        fig.add_trace(go.Scatter(
            x=hist_filtered.index,
            y=ma_50,
            mode='lines',
            name='Moyenne mobile 50j',
            line=dict(color='#f39c12', width=1, dash='dash'),
            hovertemplate='<b>MM50:</b> $%{y:.2f}<extra></extra>'
        ))
    
    if len(hist_filtered) > 200:
        ma_200 = hist_filtered['Close'].rolling(window=200).mean()
        fig.add_trace(go.Scatter(
            x=hist_filtered.index,
            y=ma_200,
            mode='lines',
            name='Moyenne mobile 200j',
            line=dict(color='#e74c3c', width=1, dash='dot'),
            hovertemplate='<b>MM200:</b> $%{y:.2f}<extra></extra>'
        ))
    
    # Configuration du graphique
    fig.update_layout(
        title=f"Évolution du cours - {selected_period}",
        xaxis_title="Date",
        yaxis_title="Prix ($)",
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    # Améliorer l'axe X
    fig.update_xaxes(
        gridcolor='lightgray',
        gridwidth=0.5,
        showgrid=True
    )
    
    # Améliorer l'axe Y
    fig.update_yaxes(
        gridcolor='lightgray',
        gridwidth=0.5,
        showgrid=True
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_metrics_table(metrics_data, info):
    """Afficher le tableau principal des métriques selon le format TLB INVESTOR exact"""
    
    st.header("📋 Validateur Automatisé TLB INVESTOR")
    
    # Métriques selon le format TLB INVESTOR exact avec explications
    tlb_metrics = [
        ("Capitalisation (Mds)", "Capitalisation (Mds)", "> 50", "10-50", "2-10", "< 2", "Taille de l'entreprise. Plus la capitalisation est élevée, plus l'entreprise est stable et liquide."),
        ("Tendance du cours long terme", "Performance 5 ans (%)", "Haussière", "Stagnante", "Baissière", "Chute libre", "Performance sur 5 ans. Une tendance haussière indique une création de valeur durable."),
        ("Chiffre d'affaires 5 ans", "CA 5 ans", "Haussier", "Stagnant", "Baissier", "Baissier > 5 ans", "Évolution du chiffre d'affaires sur 5 ans. Valeurs en milliards et croissance annuelle."),
        ("Résultat net", "Croissance Bénéfices (%)", "Haussier", "Stagnant", "Baissier", "Négatif > 5 ans", "Évolution des bénéfices. Plus importante que la croissance du CA car elle mesure la rentabilité."),
        ("Free Cash Flow", "Free Cash Flow (Mds)", "Haussier", "Stagnant", "Baissier", "Négatif > 5 ans", "Argent généré après investissements. Crucial pour dividendes et croissance future."),
        ("Marge d'exploitation", "Marge Opérationnelle (%)", "> 15%", "8-15%", "< 8%", "Négative", "Efficacité opérationnelle. >15% indique une excellente maîtrise des coûts."),
        ("Rendement dividende", "Rendement Dividende (%)", "3-5%", "2-3% ou 5-8%", "> 8%", "> 10%", "Dividende annuel / Prix de l'action. 3-5% est l'équilibre idéal entre rendement et croissance."),
        ("Historique dividendes", "Taux Distribution (%)", "Augmentation", "Stagnation", "Baisse", "Suppression", "Évolution des dividendes dans le temps. L'augmentation régulière est un signe de solidité."),
        ("Pay out ratio", "Taux Distribution (%)", "< seuil secteur", "= seuil secteur", "> seuil secteur", "> 100%", "Part des bénéfices distribués en dividendes. <80% assure la durabilité."),
        ("PER actuel", "PER", "< 15", "15-25", "25-50", "> 50", "Prix payé pour 1€ de bénéfice annuel. Plus bas = action moins chère."),
        ("Capitaux propres", "P/B", "Augmentation", "Stagnante", "Baisse", "< dette", "Prix vs valeur comptable. <2 indique généralement une valorisation attractive."),
        ("ROA", "ROA (%)", "> 8%", "5-8%", "< 5%", "Négatif", "Efficacité d'utilisation des actifs. >7% indique une très bonne gestion."),
        ("Évolution dettes", "Dette/Capitaux (%)", "Aucune/Baisse", "Stagnante", "Augmente", "> 100%", "Niveau d'endettement. <30% assure une structure financière saine."),
        ("Leverage", "Dette/Capitaux (%)", "0-3", "3-4", "4-5", "> 5", "Ratio dette/capitaux propres. Mesure le levier financier et le risque."),
        ("Bêta", "Bêta", "< 0.7", "0.7-1", "1-1.3", "> 1.8", "Volatilité vs marché. <1 = moins volatil que le marché général."),
        ("PEG", "PEG", "< 1", "= 1", "> 1", "> 2.5", "PER ajusté de la croissance. <1 = croissance pas chère, >1 = croissance chère.")
    ]
    
    # Construction du HTML complet avec tooltips
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            .tlb-table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-family: Arial, sans-serif;
                border: 2px solid #000;
            }
            
            .tlb-table th {
                background-color: #9932cc;
                color: white;
                font-weight: bold;
                padding: 12px 8px;
                text-align: center;
                border: 1px solid #000;
                font-size: 13px;
            }
            
            .tlb-table td {
                padding: 10px 8px;
                border: 1px solid #000;
                text-align: center;
                font-size: 12px;
                background-color: white;
                color: black;
            }
            
            .criteria-cell {
                text-align: left;
                font-weight: 600;
                background-color: #f5f5f5;
                padding-left: 15px;
                position: relative;
            }
            
            .value-cell {
                background-color: #e8f5e8;
                font-weight: bold;
                color: #000;
            }
            
            .tres-bon-cell { 
                background-color: #90EE90; 
                color: #000;
            }
            .bon-cell { 
                background-color: #87CEEB; 
                color: #000;
            }
            .mauvais-cell { 
                background-color: #FFD700; 
                color: #000;
            }
            .eliminatoire-cell { 
                background-color: #FF6347; 
                color: #000;
            }
            
            .note-tres-bon { 
                background-color: #90EE90 !important; 
                color: black !important; 
                font-weight: bold !important;
                border: 3px solid #228B22 !important;
                box-shadow: 0 0 10px rgba(34, 139, 34, 0.5);
            }
            .note-bon { 
                background-color: #87CEEB !important; 
                color: black !important; 
                font-weight: bold !important;
                border: 3px solid #4682B4 !important;
                box-shadow: 0 0 10px rgba(70, 130, 180, 0.5);
            }
            .note-mauvais { 
                background-color: #FFD700 !important; 
                color: black !important; 
                font-weight: bold !important;
                border: 3px solid #FFA500 !important;
                box-shadow: 0 0 10px rgba(255, 165, 0, 0.5);
            }
            .note-eliminatoire { 
                background-color: #FF6347 !important; 
                color: black !important; 
                font-weight: bold !important;
                border: 3px solid #DC143C !important;
                box-shadow: 0 0 10px rgba(220, 20, 60, 0.5);
            }
            
            .tooltip {
                position: relative;
                cursor: help;
            }
            
            .tooltip-icon {
                display: inline-block;
                width: 16px;
                height: 16px;
                background-color: #9932cc;
                color: white;
                border-radius: 50%;
                text-align: center;
                font-size: 12px;
                font-weight: bold;
                margin-left: 5px;
                line-height: 16px;
            }
            
            .tooltip .tooltiptext {
                visibility: hidden;
                width: 300px;
                background-color: #333;
                color: #fff;
                text-align: left;
                border-radius: 6px;
                padding: 10px;
                position: absolute;
                z-index: 1000;
                left: 50%;
                margin-left: -150px;
                top: -50px;
                opacity: 0;
                transition: opacity 0.3s;
                font-size: 12px;
                line-height: 1.4;
                box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            }
            
            .tooltip .tooltiptext::after {
                content: "";
                position: absolute;
                top: 100%;
                left: 50%;
                margin-left: -5px;
                border-width: 5px;
                border-style: solid;
                border-color: #333 transparent transparent transparent;
            }
            
            .tooltip:hover .tooltiptext {
                visibility: visible;
                opacity: 1;
            }
        </style>
    </head>
    <body>
        <table class="tlb-table">
            <thead>
                <tr>
                    <th>LES CRITÈRES</th>
                    <th>VALEUR ACTUELLE</th>
                    <th>TRÈS BON</th>
                    <th>BON</th>
                    <th>MAUVAIS</th>
                    <th>ÉLIMINATOIRE</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Ajouter les lignes de données
    for criteria_name, metric_key, tres_bon, bon, mauvais, eliminatoire, explanation in tlb_metrics:
        value = metrics_data.get(metric_key)
        
        # Formater la valeur
        if value is not None:
            if isinstance(value, (int, float)):
                if 'Mds' in metric_key:
                    formatted_value = f"{value:.1f}"
                elif '%' in metric_key:
                    formatted_value = f"{value:.1f}%"
                elif metric_key in ['PER', 'PEG', 'P/B', 'Bêta']:
                    formatted_value = f"{value:.2f}"
                else:
                    formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)
        else:
            formatted_value = "N/A"
        
        # Traitement spécial pour CA 5 ans
        if metric_key == "CA 5 ans" and isinstance(value, str):
            formatted_value = value
            if "+" in value and len([x for x in value.split("|") if "+" in x]) >= 3:
                score_label, score_emoji = "TRÈS BON", "🟢"
            elif "+" in value and len([x for x in value.split("|") if "+" in x]) >= 1:
                score_label, score_emoji = "BON", "🔵"
            elif "-" in value and len([x for x in value.split("|") if "-" in x]) >= 3:
                score_label, score_emoji = "ÉLIMINATOIRE", "🔴"
            else:
                score_label, score_emoji = "MAUVAIS", "🟡"
        else:
            if value is not None:
                score_label, score_emoji, _ = get_metric_score(metric_key, value)
            else:
                score_label, score_emoji = "N/A", "⚪"
        
        # Déterminer quelle cellule surligner
        tres_bon_class = "tres-bon-cell"
        bon_class = "bon-cell"
        mauvais_class = "mauvais-cell"
        eliminatoire_class = "eliminatoire-cell"
        
        if score_label == "TRÈS BON":
            tres_bon_class = "note-tres-bon"
        elif score_label == "BON":
            bon_class = "note-bon"
        elif score_label == "MAUVAIS":
            mauvais_class = "note-mauvais"
        elif score_label == "ÉLIMINATOIRE":
            eliminatoire_class = "note-eliminatoire"
        
        # Ajouter la ligne au HTML
        html_content += f"""
                <tr>
                    <td class="criteria-cell">
                        <div class="tooltip">
                            {criteria_name}
                            <span class="tooltip-icon">?</span>
                            <span class="tooltiptext">{explanation}</span>
                        </div>
                    </td>
                    <td class="value-cell">{formatted_value}</td>
                    <td class="{tres_bon_class}">{tres_bon}</td>
                    <td class="{bon_class}">{bon}</td>
                    <td class="{mauvais_class}">{mauvais}</td>
                    <td class="{eliminatoire_class}">{eliminatoire}</td>
                </tr>
        """
    
    # Fermer le HTML
    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """
    
    components.html(html_content, height=600, scrolling=True)

def get_metric_score(metric_name, value):
    """Calculer le score d'une métrique selon les seuils TLB INVESTOR"""
    
    if value is None:
        return "N/A", "⚪", "Donnée non disponible"
    
    scoring_rules = {
        'PER': {
            'ranges': [(0, 15, 'TRÈS BON', '🟢'), (15, 25, 'BON', '🔵'), (25, 50, 'MAUVAIS', '🟡'), (50, float('inf'), 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Prix payé pour 1€ de bénéfice annuel. Plus bas = moins cher.'
        },
        'PEG': {
            'ranges': [(0, 1, 'TRÈS BON', '🟢'), (1, 1, 'BON', '🔵'), (1, 2.5, 'MAUVAIS', '🟡'), (2.5, float('inf'), 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'PER ajusté de la croissance. <1 = croissance pas chère.'
        },
        'P/B': {
            'ranges': [(0, 1, 'TRÈS BON', '🟢'), (1, 2, 'BON', '🔵'), (2, 5, 'MAUVAIS', '🟡'), (5, float('inf'), 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Prix vs valeur comptable. <2 généralement attractif.'
        },
        'P/S': {
            'ranges': [(0, 2, 'TRÈS BON', '🟢'), (2, 4, 'BON', '🔵'), (4, 10, 'MAUVAIS', '🟡'), (10, float('inf'), 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Prix vs chiffre d\'affaires. Varie selon le secteur.'
        },
        'EV/Revenue': {
            'ranges': [(0, 3, 'TRÈS BON', '🟢'), (3, 5, 'BON', '🔵'), (5, 12, 'MAUVAIS', '🟡'), (12, float('inf'), 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Valeur d\'entreprise vs revenus. Mesure la valorisation totale.'
        },
        'EV/EBITDA': {
            'ranges': [(0, 8, 'TRÈS BON', '🟢'), (8, 12, 'BON', '🔵'), (12, 25, 'MAUVAIS', '🟡'), (25, float('inf'), 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Valeur vs bénéfices avant amortissements. Standard du marché.'
        },
        'Marge Brute (%)': {
            'ranges': [(40, float('inf'), 'TRÈS BON', '🟢'), (25, 40, 'BON', '🔵'), (5, 25, 'MAUVAIS', '🟡'), (0, 5, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Profit après coûts de production. Varie selon l\'industrie.'
        },
        'Marge Opérationnelle (%)': {
            'ranges': [(15, float('inf'), 'TRÈS BON', '🟢'), (8, 15, 'BON', '🔵'), (0, 8, 'MAUVAIS', '🟡'), (-float('inf'), 0, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Efficacité opérationnelle. >15% = très bon.'
        },
        'Marge Nette (%)': {
            'ranges': [(15, float('inf'), 'TRÈS BON', '🟢'), (8, 15, 'BON', '🔵'), (0, 8, 'MAUVAIS', '🟡'), (-float('inf'), 0, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Profit final. >10% = entreprise très rentable.'
        },
        'ROE (%)': {
            'ranges': [(20, float('inf'), 'TRÈS BON', '🟢'), (15, 20, 'BON', '🔵'), (5, 15, 'MAUVAIS', '🟡'), (0, 5, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Rendement des capitaux propres. >15% = excellente gestion.'
        },
        'ROA (%)': {
            'ranges': [(8, float('inf'), 'TRÈS BON', '🟢'), (5, 8, 'BON', '🔵'), (0, 5, 'MAUVAIS', '🟡'), (-float('inf'), 0, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Efficacité d\'utilisation des actifs. >7% = très bon.'
        },
        'Croissance CA (%)': {
            'ranges': [(20, float('inf'), 'TRÈS BON', '🟢'), (10, 20, 'BON', '🔵'), (0, 10, 'MAUVAIS', '🟡'), (-float('inf'), 0, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Croissance du chiffre d\'affaires. >10% = forte croissance.'
        },
        'Croissance Bénéfices (%)': {
            'ranges': [(25, float('inf'), 'TRÈS BON', '🟢'), (15, 25, 'BON', '🔵'), (0, 15, 'MAUVAIS', '🟡'), (-float('inf'), 0, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Croissance des bénéfices. Plus importante que le CA.'
        },
        'Croissance CA Trim (%)': {
            'ranges': [(15, float('inf'), 'TRÈS BON', '🟢'), (5, 15, 'BON', '🔵'), (-5, 5, 'MAUVAIS', '🟡'), (-float('inf'), -5, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Tendance récente du chiffre d\'affaires.'
        },
        'Croissance Bén Trim (%)': {
            'ranges': [(20, float('inf'), 'TRÈS BON', '🟢'), (10, 20, 'BON', '🔵'), (-10, 10, 'MAUVAIS', '🟡'), (-float('inf'), -10, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Dynamique récente des bénéfices.'
        },
        'Dette/Capitaux (%)': {
            'ranges': [(0, 20, 'TRÈS BON', '🟢'), (20, 40, 'BON', '🔵'), (40, 100, 'MAUVAIS', '🟡'), (100, float('inf'), 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Niveau d\'endettement. <30% = très sain.'
        },
        'Ratio Liquidité': {
            'ranges': [(2, float('inf'), 'TRÈS BON', '🟢'), (1.5, 2, 'BON', '🔵'), (1, 1.5, 'MAUVAIS', '🟡'), (0, 1, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Capacité à payer les dettes court terme. >1.5 = bon.'
        },
        'Ratio Liquidité Imm': {
            'ranges': [(1.5, float('inf'), 'TRÈS BON', '🟢'), (1.2, 1.5, 'BON', '🔵'), (0.8, 1.2, 'MAUVAIS', '🟡'), (0, 0.8, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Liquidité sans les stocks. >1 = sécurisant.'
        },
        'Trésorerie (Mds)': {
            'ranges': [(5, float('inf'), 'TRÈS BON', '🟢'), (2, 5, 'BON', '🔵'), (0.1, 2, 'MAUVAIS', '🟡'), (0, 0.1, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Liquidités disponibles. Dépend de la taille de l\'entreprise.'
        },
        'Free Cash Flow (Mds)': {
            'ranges': [(2, float('inf'), 'TRÈS BON', '🟢'), (0.5, 2, 'BON', '🔵'), (-0.5, 0.5, 'MAUVAIS', '🟡'), (-float('inf'), -0.5, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Argent généré après investissements. Crucial pour la santé.'
        },
        'Rendement Dividende (%)': {
            'ranges': [(3, 5, 'TRÈS BON', '🟢'), (2, 3, 'BON', '🔵'), (0.1, 2, 'MAUVAIS', '🟡'), (0, 0.1, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Rendement annuel du dividende. 3-5% = idéal.'
        },
        'Taux Distribution (%)': {
            'ranges': [(20, 60, 'TRÈS BON', '🟢'), (60, 80, 'BON', '🔵'), (80, 120, 'MAUVAIS', '🟡'), (120, float('inf'), 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Part des bénéfices distribués. <80% = durable.'
        },
        'Dividende/Action ($)': {
            'ranges': [(2, float('inf'), 'TRÈS BON', '🟢'), (1, 2, 'BON', '🔵'), (0.1, 1, 'MAUVAIS', '🟡'), (0, 0.1, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Montant annuel par action. Varie selon le prix de l\'action.'
        },
        'Performance 1 an (%)': {
            'ranges': [(20, float('inf'), 'TRÈS BON', '🟢'), (10, 20, 'BON', '🔵'), (-10, 10, 'MAUVAIS', '🟡'), (-float('inf'), -10, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Performance sur 12 mois vs marché.'
        },
        'Performance 3 ans (%)': {
            'ranges': [(50, float('inf'), 'TRÈS BON', '🟢'), (20, 50, 'BON', '🔵'), (-20, 20, 'MAUVAIS', '🟡'), (-float('inf'), -20, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Performance cumulée sur 3 ans.'
        },
        'Performance 5 ans (%)': {
            'ranges': [(100, float('inf'), 'TRÈS BON', '🟢'), (50, 100, 'BON', '🔵'), (-30, 50, 'MAUVAIS', '🟡'), (-float('inf'), -30, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Performance à long terme. Très révélatrice.'
        },
        'Volatilité (%)': {
            'ranges': [(0, 15, 'TRÈS BON', '🟢'), (15, 25, 'BON', '🔵'), (25, 50, 'MAUVAIS', '🟡'), (50, float('inf'), 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Variabilité des prix. <20% = stable.'
        },
        'Bêta': {
            'ranges': [(0, 0.7, 'TRÈS BON', '🟢'), (0.7, 1, 'BON', '🔵'), (1, 1.8, 'MAUVAIS', '🟡'), (1.8, float('inf'), 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Volatilité vs marché. <1 = moins volatil que le marché.'
        },
        'Capitalisation (Mds)': {
            'ranges': [(50, float('inf'), 'TRÈS BON', '🟢'), (10, 50, 'BON', '🔵'), (2, 10, 'MAUVAIS', '🟡'), (0, 2, 'ÉLIMINATOIRE', '🔴')],
            'explanation': 'Taille de l\'entreprise. >10Mds = Large Cap.'
        }
    }
    
    if metric_name in scoring_rules:
        rule = scoring_rules[metric_name]
        for min_val, max_val, label, emoji in rule['ranges']:
            if min_val <= value < max_val:
                return label, emoji, rule['explanation']
    
    return "MAUVAIS", "🟡", "Critère à analyser"

def display_score_summary(metrics_data):
    """Afficher le résumé des scores SANS score global"""
    
    st.header("🎯 Résumé des Évaluations")
    
    # Compter les scores
    scores = []
    for metric, value in metrics_data.items():
        if value is not None:
            score_label, score_emoji, _ = get_metric_score(metric, value)
            scores.append(score_label)
    
    tres_bon_count = scores.count('TRÈS BON')
    bon_count = scores.count('BON')
    mauvais_count = scores.count('MAUVAIS')
    eliminatoire_count = scores.count('ÉLIMINATOIRE')
    total_scores = len(scores)
    
    # Affichage des compteurs uniquement
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "🟢 TRÈS BON", 
            tres_bon_count, 
            f"{tres_bon_count/total_scores*100:.0f}%" if total_scores > 0 else "0%"
        )
    
    with col2:
        st.metric(
            "🔵 BON", 
            bon_count, 
            f"{bon_count/total_scores*100:.0f}%" if total_scores > 0 else "0%"
        )
    
    with col3:
        st.metric(
            "🟡 MAUVAIS", 
            mauvais_count, 
            f"{mauvais_count/total_scores*100:.0f}%" if total_scores > 0 else "0%"
        )
    
    with col4:
        st.metric(
            "🟣 ÉLIMINATOIRE", 
            eliminatoire_count, 
            f"{eliminatoire_count/total_scores*100:.0f}%" if total_scores > 0 else "0%"
        )

def display_radar_chart(metrics_data):
    """Afficher un graphique radar des principales métriques"""
    
    st.header("📊 Profil de Performance - Radar")
    
    # Sélectionner les métriques clés pour le radar
    key_metrics = {
        'Valorisation': metrics_data.get('PER'),
        'Rentabilité': metrics_data.get('ROE (%)'),
        'Croissance': metrics_data.get('Croissance CA (%)'),
        'Solidité': 100 - metrics_data.get('Dette/Capitaux (%)', 50),
        'Dividende': metrics_data.get('Rendement Dividende (%)', 0),
        'Performance': metrics_data.get('Performance 1 an (%)', 0)
    }
    
    # Normaliser les scores pour le radar (0-5)
    radar_scores = []
    radar_labels = []
    
    for label, value in key_metrics.items():
        if value is not None:
            # Convertir en score 0-5 basé sur les niveaux TLB
            if label == 'Valorisation':
                if value <= 12:
                    score = 5
                elif value <= 18:
                    score = 4
                elif value <= 25:
                    score = 3
                elif value <= 35:
                    score = 2
                else:
                    score = 1
            elif label == 'Rentabilité':
                if value >= 20:
                    score = 5
                elif value >= 15:
                    score = 4
                elif value >= 10:
                    score = 3
                elif value >= 5:
                    score = 2
                else:
                    score = 1
            elif label == 'Croissance':
                if value >= 20:
                    score = 5
                elif value >= 10:
                    score = 4
                elif value >= 3:
                    score = 3
                elif value >= 0:
                    score = 2
                else:
                    score = 1
            elif label == 'Solidité':
                if value >= 80:
                    score = 5
                elif value >= 60:
                    score = 4
                elif value >= 40:
                    score = 3
                elif value >= 20:
                    score = 2
                else:
                    score = 1
            elif label == 'Dividende':
                if 3 <= value <= 6:
                    score = 5
                elif 2 <= value < 3:
                    score = 4
                elif 1 <= value < 2:
                    score = 3
                elif 0.1 <= value < 1:
                    score = 2
                else:
                    score = 1
            elif label == 'Performance':
                if value >= 20:
                    score = 5
                elif value >= 10:
                    score = 4
                elif value >= 0:
                    score = 3
                elif value >= -10:
                    score = 2
                else:
                    score = 1
            else:
                score = 3
            
            radar_scores.append(score)
            radar_labels.append(label)
    
    if radar_scores and len(radar_scores) >= 3:
        # Fermer le polygone
        radar_scores_closed = radar_scores + [radar_scores[0]]
        radar_labels_closed = radar_labels + [radar_labels[0]]
        
        fig_radar = go.Figure()
        
        fig_radar.add_trace(go.Scatterpolar(
            r=radar_scores_closed,
            theta=radar_labels_closed,
            fill='toself',
            name='Performance',
            line=dict(color='#9932cc', width=3),
            fillcolor='rgba(153, 50, 204, 0.3)',
            hovertemplate='<b>%{theta}</b><br>Score: %{r}/5<extra></extra>'
        ))
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 5],
                    tickvals=[1, 2, 3, 4, 5],
                    ticktext=['Éliminatoire', 'Mauvais', 'Moyen', 'Bon', 'Très Bon'],
                    gridcolor='lightgray'
                ),
                angularaxis=dict(
                    gridcolor='lightgray'
                )
            ),
            showlegend=False,
            title={
                'text': "Profil TLB INVESTOR (1-5)",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16}
            },
            height=500,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig_radar, use_container_width=True)
        
        # Ajouter l'explication des critères analysés APRÈS le radar
        st.markdown("---")
        st.markdown("### 🎯 Critères analysés dans le radar")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **📈 VALORISATION**
            - PER, PEG, P/B, P/S
            - EV/EBITDA, EV/Revenue
            
            **💰 RENTABILITÉ**
            - Marges (Brute, Opé, Nette)
            - ROE, ROA
            
            **🚀 CROISSANCE**
            - CA, Bénéfices
            - Tendances trimestrielles
            """)
        
        with col2:
            st.markdown("""
            **🛡️ SOLIDITÉ**
            - Endettement, Liquidité
            - Trésorerie, Free Cash Flow
            
            **💎 QUALITÉ**
            - Dividendes, Volatilité
            - Performance historique
            
            **📊 Le radar synthétise** ces 6 dimensions clés
            """)
            
    else:
        st.warning("Données insuffisantes pour générer le graphique radar")

if __name__ == "__main__":
    st.set_page_config(
        page_title="TLB INVESTOR - Analyseur Financier",
        page_icon="📊",
        layout="wide"
    )
    
    display_tab8_analyse()
