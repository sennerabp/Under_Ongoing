import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
import requests
import time
from modules.tab0_constants import save_to_excel

def get_dividend_history_yfinance(ticker, start_date):
    """
    Récupérer l'historique des dividendes via Yahoo Finance
    """
    try:
        stock = yf.Ticker(ticker)
        
        # Récupérer les dividendes depuis la date d'achat
        dividends = stock.dividends
        
        if dividends.empty:
            return pd.DataFrame()
        
        # Normaliser les fuseaux horaires pour la comparaison
        if dividends.index.tz is not None:
            # Si les dividendes ont un fuseau horaire, convertir en UTC puis supprimer le fuseau
            dividends.index = dividends.index.tz_convert('UTC').tz_localize(None)
        
        # S'assurer que start_date est également sans fuseau horaire
        if hasattr(start_date, 'tz_localize'):
            start_date = start_date.tz_localize(None)
        elif hasattr(start_date, 'tz'):
            start_date = pd.Timestamp(start_date).tz_localize(None)
        else:
            start_date = pd.Timestamp(start_date)
        
        # Filtrer depuis la date d'achat
        dividends = dividends[dividends.index >= start_date]
        
        if dividends.empty:
            return pd.DataFrame()
        
        # Convertir en DataFrame avec les informations nécessaires
        div_df = pd.DataFrame({
            'Date paiement': dividends.index,
            'Ticker': ticker,
            'Dividende par action': dividends.values,
            'Devise': 'USD'  # Par défaut USD, sera ajusté plus tard
        })
        
        return div_df
        
    except Exception as e:
        st.warning(f"Erreur lors de la récupération des dividendes pour {ticker}: {e}")
        return pd.DataFrame()

def get_next_dividend_estimate(ticker, historical_dividends):
    """
    Estimer le prochain dividende basé sur l'historique
    """
    try:
        if historical_dividends.empty or len(historical_dividends) < 2:
            return None
        
        # Calculer la fréquence moyenne entre les dividendes
        dates = pd.to_datetime(historical_dividends['Date paiement']).sort_values()
        intervals = []
        
        for i in range(1, len(dates)):
            interval = (dates.iloc[i] - dates.iloc[i-1]).days
            intervals.append(interval)
        
        if not intervals:
            return None
        
        # Fréquence moyenne
        avg_interval = np.mean(intervals)
        
        # Dernière date de dividende
        last_date = dates.max()
        
        # Estimation de la prochaine date
        next_date = last_date + timedelta(days=avg_interval)
        
        # Estimation du montant (moyenne des 3 derniers)
        last_amounts = historical_dividends['Dividende par action'].tail(3)
        estimated_amount = last_amounts.mean()
        
        return {
            'Date estimée': next_date,
            'Montant estimé': estimated_amount,
            'Confiance': 'Élevée' if len(historical_dividends) >= 4 else 'Moyenne',
            'Fréquence (jours)': avg_interval
        }
        
    except Exception as e:
        st.warning(f"Erreur estimation dividende pour {ticker}: {e}")
        return None

def get_company_info(ticker):
    """
    Récupérer les informations de l'entreprise
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            'Nom': info.get('longName', ticker),
            'Devise': info.get('currency', 'USD'),
            'Secteur': info.get('sector', 'N/A'),
            'Rendement dividende': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
        }
    except:
        return {
            'Nom': ticker,
            'Devise': 'USD',
            'Secteur': 'N/A',
            'Rendement dividende': 0
        }

def calculate_dividend_amounts(dividends_df, holdings_df):
    """
    Calculer les montants réels de dividendes selon les quantités détenues
    """
    results = []
    
    for _, div_row in dividends_df.iterrows():
        ticker = div_row['Ticker']
        div_date = pd.to_datetime(div_row['Date paiement'])
        div_per_share = div_row['Dividende par action']
        
        # Trouver les achats antérieurs à cette date de dividende
        relevant_purchases = holdings_df[
            (holdings_df['Ticker'] == ticker) & 
            (pd.to_datetime(holdings_df['Date']) <= div_date)
        ]
        
        if not relevant_purchases.empty:
            # Quantité totale détenue à cette date
            total_quantity = relevant_purchases['Quantity'].sum()
            
            # Montant brut du dividende
            gross_amount = total_quantity * div_per_share
            
            # Estimation de l'impôt (30% fixe)
            tax_rate = 0.30
            net_amount = gross_amount * (1 - tax_rate)
            
            results.append({
                'Date paiement': div_date,
                'Ticker': ticker,
                'Entreprise': relevant_purchases['Entreprise'].iloc[0],
                'Dividende par action': div_per_share,
                'Quantité détenue': total_quantity,
                'Montant brut (€)': gross_amount,
                'Montant net (€)': net_amount,
                'Devise': div_row['Devise'],
                'Type': 'Calculé automatiquement'
            })
    
    return pd.DataFrame(results)

def display_tab6_dividendes():
    st.markdown("## 💰 Suivi des Dividendes")

    # 🚨 Guard clause si pas de fichier Excel chargé
    if "df_data" not in st.session_state or st.session_state.df_data.empty:
        st.info("💡 Aucun fichier Excel chargé. Veuillez importer votre fichier dans la barre latérale.")
        return

    # === RECHERCHE AUTOMATIQUE DES DIVIDENDES ===
    st.markdown("### 🔍 Recherche automatique des dividendes")
    
    df_data = st.session_state.df_data.copy()
    df_data['Date'] = pd.to_datetime(df_data['Date'], errors='coerce')
    
    # Bouton pour lancer la recherche automatique
    if st.button("🚀 Rechercher automatiquement tous les dividendes", key="auto_dividend_search", type="primary"):
        
        # Récupérer la liste unique des tickers
        tickers = df_data['Ticker'].dropna().unique()
        
        st.info(f"🔍 Recherche en cours pour {len(tickers)} titres...")
        
        # Barre de progression
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_dividends = []
        next_dividends = []
        
        for i, ticker in enumerate(tickers):
            try:
                status_text.text(f"Traitement de {ticker}...")
                
                # Date du premier achat pour ce ticker (normaliser le fuseau horaire)
                first_purchase_date = df_data[df_data['Ticker'] == ticker]['Date'].min()
                # S'assurer que la date est sans fuseau horaire
                if hasattr(first_purchase_date, 'tz_localize'):
                    first_purchase_date = first_purchase_date.tz_localize(None)
                elif hasattr(first_purchase_date, 'tz') and first_purchase_date.tz is not None:
                    first_purchase_date = first_purchase_date.tz_convert(None)
                
                # Récupérer l'historique des dividendes
                div_history = get_dividend_history_yfinance(ticker, first_purchase_date)
                
                if not div_history.empty:
                    # Informations de l'entreprise
                    company_info = get_company_info(ticker)
                    div_history['Entreprise'] = company_info['Nom']
                    div_history['Devise'] = company_info['Devise']
                    
                    all_dividends.append(div_history)
                    
                    # Estimation du prochain dividende
                    next_div = get_next_dividend_estimate(ticker, div_history)
                    if next_div:
                        next_div['Ticker'] = ticker
                        next_div['Entreprise'] = company_info['Nom']
                        next_dividends.append(next_div)
                
                # Petite pause pour éviter de surcharger l'API
                time.sleep(0.1)
                
            except Exception as e:
                st.warning(f"Erreur pour {ticker}: {e}")
            
            # Mise à jour de la progression
            progress_bar.progress((i + 1) / len(tickers))
        
        # Consolidation des résultats
        if all_dividends:
            consolidated_dividends = pd.concat(all_dividends, ignore_index=True)
            
            # Calculer les montants réels basés sur les quantités détenues
            calculated_dividends = calculate_dividend_amounts(consolidated_dividends, df_data)
            
            if not calculated_dividends.empty:
                # Mettre à jour le session state
                st.session_state.df_dividendes = calculated_dividends
                st.session_state.data_modified = True
                
                # Sauvegarder automatiquement
                save_to_excel()
                
                st.success(f"✅ {len(calculated_dividends)} dividendes trouvés et sauvegardés!")
                st.rerun()
            else:
                st.info("Aucun dividende trouvé pour la période détenue.")
        else:
            st.info("Aucun dividende trouvé pour les titres du portefeuille.")
        
        progress_bar.empty()
        status_text.empty()

    # === ANALYSE DES DIVIDENDES EXISTANTS ===
    df_div = st.session_state.df_dividendes.copy()
    
    if df_div.empty:
        st.info("💡 Aucun dividende enregistré. Utilisez la recherche automatique ci-dessus pour détecter vos dividendes.")
        return
    
    # Préparation des données
    df_div["Date paiement"] = pd.to_datetime(df_div["Date paiement"], errors='coerce')
    df_div = df_div.dropna(subset=["Date paiement"])
    df_div["Montant brut (€)"] = pd.to_numeric(df_div["Montant brut (€)"], errors="coerce").fillna(0)
    df_div["Montant net (€)"] = pd.to_numeric(df_div["Montant net (€)"], errors="coerce").fillna(0)

    # === STATISTIQUES GÉNÉRALES ===
    st.markdown("---")
    st.markdown("### 📊 Vue d'ensemble des dividendes")
    
    # Statistiques globales
    total_dividendes = df_div["Montant net (€)"].sum()
    nb_versements = len(df_div)
    nb_entreprises = df_div['Entreprise'].nunique()
    moyenne_versement = df_div["Montant net (€)"].mean()
    
    # Filtrer les 12 derniers mois
    twelve_months_ago = datetime.now() - timedelta(days=365)
    recent_dividends = df_div[df_div["Date paiement"] >= twelve_months_ago]
    total_12m = recent_dividends["Montant net (€)"].sum()
    
    col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)
    
    with col_stat1:
        st.metric("💰 Total dividendes", f"{total_dividendes:,.0f} €")
    
    with col_stat2:
        st.metric("📊 Versements", f"{nb_versements}")
    
    with col_stat3:
        st.metric("🏢 Entreprises", f"{nb_entreprises}")
    
    with col_stat4:
        st.metric("💸 Moyenne/versement", f"{moyenne_versement:,.0f} €")
    
    with col_stat5:
        st.metric("📅 Total 12 mois", f"{total_12m:,.0f} €")

    # === ANALYSE PAR ENTREPRISE ===
    st.markdown("### 🏢 Analyse par entreprise")
    
    # Calculs par entreprise
    div_by_company = df_div.groupby('Entreprise').agg({
        'Montant net (€)': ['sum', 'count', 'mean'],
        'Date paiement': ['min', 'max']
    }).round(2)
    
    # Aplatir les colonnes
    div_by_company.columns = ['Total versé (€)', 'Nb versements', 'Montant moyen (€)', 'Premier dividende', 'Dernier dividende']
    div_by_company = div_by_company.reset_index()
    div_by_company = div_by_company.sort_values('Total versé (€)', ascending=False)
    
    # Calculer la fréquence
    div_by_company['Période (jours)'] = (div_by_company['Dernier dividende'] - div_by_company['Premier dividende']).dt.days
    div_by_company['Fréquence estimée (jours)'] = np.where(
        div_by_company['Nb versements'] > 1,
        (div_by_company['Période (jours)'] / (div_by_company['Nb versements'] - 1)).round(0).astype('Int64'),
        np.nan
    )
    
    col_table, col_charts = st.columns([1, 1])
    
    with col_table:
        st.markdown("#### 📋 Tableau récapitulatif")
        # Formatter le tableau pour l'affichage
        display_columns = ['Entreprise', 'Total versé (€)', 'Nb versements', 'Montant moyen (€)', 'Fréquence estimée (jours)']
        st.dataframe(
            div_by_company[display_columns].head(10),
            use_container_width=True,
            hide_index=True
        )
    
    with col_charts:
        st.markdown("#### 🥇 Top contributeurs")
        # Graphique en secteurs des top contributeurs
        top_5_companies = div_by_company.head(5)
        
        fig_pie = px.pie(
            top_5_companies,
            values='Total versé (€)',
            names='Entreprise',
            title="Répartition des dividendes (Top 5)",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fig_pie.update_layout(
            height=300,
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.01)
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)

    # === ÉVOLUTION TEMPORELLE ===
    st.markdown("### 📈 Évolution temporelle des dividendes")
    
    col_period1, col_period2 = st.columns(2)
    
    with col_period1:
        st.markdown("#### 📅 Dividendes mensuels")
        
        # Grouper par mois
        df_div_monthly = df_div.copy()
        df_div_monthly['Mois'] = df_div_monthly['Date paiement'].dt.to_period('M')
        monthly_div = df_div_monthly.groupby('Mois')['Montant net (€)'].sum().reset_index()
        monthly_div['Mois_str'] = monthly_div['Mois'].dt.strftime('%Y-%m')
        
        fig_monthly = px.bar(
            monthly_div,
            x='Mois_str',
            y='Montant net (€)',
            title="Évolution mensuelle",
            color='Montant net (€)',
            color_continuous_scale='Blues'
        )
        
        fig_monthly.update_layout(
            xaxis_title="Mois",
            yaxis_title="Montant (€)",
            height=400,
            xaxis={'type': 'category'},
            xaxis_tickangle=-45
        )
        
        st.plotly_chart(fig_monthly, use_container_width=True)
    
    with col_period2:
        st.markdown("#### 🏢 Contributions par entreprise")
        
        # Graphique en barres des contributions par entreprise
        top_10_companies = div_by_company.head(10)
        
        fig_companies = px.bar(
            top_10_companies,
            x='Total versé (€)',
            y='Entreprise',
            orientation='h',
            title="Top 10 des entreprises",
            color='Total versé (€)',
            color_continuous_scale='Greens'
        )
        
        fig_companies.update_layout(
            height=400,
            yaxis=dict(autorange="reversed")  # Inverser l'ordre pour avoir le plus grand en haut
        )
        
        st.plotly_chart(fig_companies, use_container_width=True)

    # === PROCHAINS DIVIDENDES ESTIMÉS ===
    st.markdown("### 🔮 Prochains dividendes estimés")
    
    # Analyse des patterns pour estimer les prochains dividendes
    prochains_dividendes = []
    date_actuelle = datetime.now()
    
    for entreprise in df_div['Entreprise'].unique():
        # Derniers dividendes de cette entreprise
        div_entreprise = df_div[df_div['Entreprise'] == entreprise].sort_values("Date paiement")
        if len(div_entreprise) >= 2:
            # Calculer la fréquence moyenne
            dates = div_entreprise["Date paiement"].dt.date
            intervals = [(dates.iloc[i] - dates.iloc[i-1]).days for i in range(1, len(dates))]
            interval_moyen = np.mean(intervals) if intervals else 365
            
            # Prochaine date estimée
            derniere_date = div_entreprise["Date paiement"].iloc[-1]
            prochaine_date = derniere_date + timedelta(days=interval_moyen)
            
            if prochaine_date > date_actuelle and prochaine_date <= date_actuelle + timedelta(days=180):
                montant_moyen = div_entreprise["Montant net (€)"].tail(3).mean()
                prochains_dividendes.append({
                    "Entreprise": entreprise,
                    "Date estimée": prochaine_date.date(),
                    "Montant estimé (€)": f"{montant_moyen:.0f}",
                    "Fréquence (jours)": f"{interval_moyen:.0f}",
                    "Confiance": "Élevée" if len(div_entreprise) >= 4 else "Moyenne",
                    "Dernier versement": derniere_date.strftime('%d/%m/%Y')
                })
    
    if prochains_dividendes:
        df_prochains = pd.DataFrame(prochains_dividendes).sort_values("Date estimée")
        
        col_next1, col_next2 = st.columns([2, 1])
        
        with col_next1:
            st.dataframe(df_prochains, use_container_width=True, hide_index=True)
        
        with col_next2:
            # Résumé des prochains 3 mois
            trois_mois = datetime.now() + timedelta(days=90)
            prochains_3m = df_prochains[pd.to_datetime(df_prochains['Date estimée']) <= trois_mois]
            
            if not prochains_3m.empty:
                total_estime_3m = prochains_3m['Montant estimé (€)'].str.replace('€', '').astype(float).sum()
                nb_versements_3m = len(prochains_3m)
                
                st.markdown("**📅 Prochains 3 mois :**")
                st.metric("Versements attendus", f"{nb_versements_3m}")
                st.metric("Montant estimé", f"{total_estime_3m:.0f} €")
            else:
                st.info("Aucun dividende estimé dans les 3 prochains mois")
    else:
        st.info("Impossible d'estimer les prochains dividendes. Besoin de plus d'historique.")

    # === HISTORIQUE DÉTAILLÉ ===
    with st.expander("📜 Historique complet des dividendes", expanded=False):
        # Trier par date décroissante
        df_div_display = df_div.sort_values("Date paiement", ascending=False)
        
        # Colonnes à afficher
        display_cols = ['Date paiement', 'Entreprise', 'Montant net (€)', 'Montant brut (€)', 'Dividende par action', 'Quantité détenue']
        available_cols = [col for col in display_cols if col in df_div_display.columns]
        
        st.dataframe(
            df_div_display[available_cols],
            use_container_width=True,
            hide_index=True
        )
        
        # Statistiques de l'historique
        st.markdown("**📊 Statistiques de l'historique :**")
        col_hist1, col_hist2, col_hist3 = st.columns(3)
        
        with col_hist1:
            st.write(f"• **Période :** {df_div['Date paiement'].min().strftime('%m/%Y')} - {df_div['Date paiement'].max().strftime('%m/%Y')}")
        
        with col_hist2:
            duree_historique = (df_div['Date paiement'].max() - df_div['Date paiement'].min()).days / 365.25
            st.write(f"• **Durée :** {duree_historique:.1f} ans")
        
        with col_hist3:
            freq_moyenne = len(df_div) / duree_historique if duree_historique > 0 else 0
            st.write(f"• **Fréquence :** {freq_moyenne:.1f} versements/an")
