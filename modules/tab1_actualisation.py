import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from modules.tab0_constants import SECTEUR_PAR_TYPE, CATEGORY_LIST, SECTOR_COLORS, save_to_excel
import calendar
import numpy as np

# Importer le nouveau gestionnaire de cache
from modules.yfinance_cache_manager import (
    get_cache_manager, 
    update_portfolio_prices_optimized, 
    get_real_time_data_optimized,
    display_cache_debug_info
)

def add_eur_columns(df):
    """
    🔥 SOLUTION DÉFINITIVE : Ajouter les colonnes EUR pour TOUT !
    """
    cache_manager = get_cache_manager()
    eurusd_rate = cache_manager.get_eurusd_rate()
    
    df = df.copy()
    
    # S'assurer que Units existe
    if "Units" not in df.columns:
        df["Units"] = "EUR"
    df["Units"] = df["Units"].fillna("EUR").astype(str)
    
    # 🔥 CRÉER LES COLONNES EUR POUR TOUT
    df["Purchase_value_EUR"] = df["Purchase value"].copy()
    df["Current_value_EUR"] = df["Current value"].copy()
    
    # Convertir SEULEMENT les lignes USD
    for idx, row in df.iterrows():
        if str(row["Units"]).upper() == "USD":
            df.loc[idx, "Purchase_value_EUR"] = row["Purchase value"] * eurusd_rate
            if pd.notnull(row["Current value"]):
                df.loc[idx, "Current_value_EUR"] = row["Current value"] * eurusd_rate
    
    return df

def display_tab1_actualisation():
    """
    🔄 Tab 1 – VERSION FINALE SANS PRISE DE TÊTE
    """
    st.subheader("🔄 Actualisation des cours boursiers")

    # Guard clause si pas de fichier Excel chargé
    if "df_data" not in st.session_state or st.session_state.df_data.empty:
        st.info("💡 Aucun fichier Excel chargé. Veuillez importer votre fichier dans la barre latérale.")
        return

    # Copie & nettoyage du DataFrame
    df = st.session_state.df_data.copy()
    df.columns = [str(c).strip() for c in df.columns]
    
    # Récupérer le gestionnaire de cache
    cache_manager = get_cache_manager()
    
    # === INTERFACE D'ACTUALISATION SIMPLIFIÉE ===
    if st.button("📈 Actualiser cours boursiers", key="btn_update_main", type="primary"):
        with st.spinner("🔄 Actualisation en cours..."):
            df_updated = update_portfolio_prices_optimized(df)
            st.session_state.df_data = df_updated
            st.session_state.data_modified = True
            
            # Sauvegarder immédiatement
            try:
                success = save_to_excel()
                if success:
                    st.success("✅ Cours mis à jour et sauvegardés")
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la sauvegarde")
            except Exception as e:
                st.error(f"❌ Erreur lors de la sauvegarde : {e}")
                
    # Auto-actualisation si les données sont vides
    if "Current value" not in df.columns or df["Current value"].isna().all():
        st.info("🔄 Première actualisation automatique...")
        df = update_portfolio_prices_optimized(df)
        st.session_state.df_data = df

    # === TRAITEMENT PRINCIPAL ===
    if "df_data" in st.session_state and not st.session_state.df_data.empty:
        df = st.session_state.df_data.copy()
        df.columns = df.columns.str.strip()

        # Vérifier qu'on a des valeurs actuelles
        if "Current value" in df.columns and not df["Current value"].isna().all():
            
            # 🔥 CRÉER LES COLONNES EUR UNE FOIS POUR TOUTES !
            df = add_eur_columns(df)
            
            tickers = df["Ticker"].dropna().unique().tolist()
            
            # Récupération optimisée des données temps réel
            with st.spinner("📊 Récupération des données temps réel..."):
                real_time_data = get_real_time_data_optimized(tickers)

            # === REGROUPEMENT AVEC LES COLONNES EUR ===
            grouped = df.groupby("Ticker").agg({
                "Entreprise": "first",
                "Quantity": "sum",
                "Purchase value": "sum",  # Garder l'original
                "Current value": "sum",   # Garder l'original
                "Purchase_value_EUR": "sum",  # 🔥 UTILISER ÇA pour les calculs !
                "Current_value_EUR": "sum",   # 🔥 UTILISER ÇA pour les calculs !
                "Compte": lambda x: ', '.join(sorted(set(x))),
                "Type": "first",
                "Secteur": "first",
                "Category": "first",
                "Units": "first"
            }).reset_index()
            
            # Ajout des données temps réel
            grouped["Prix actuel"] = grouped["Ticker"].map(lambda x: real_time_data.get(x, {}).get('current_price', 0))
            grouped["Variation jour"] = grouped["Ticker"].map(lambda x: real_time_data.get(x, {}).get('change', 0))
            grouped["Variation jour %"] = grouped["Ticker"].map(lambda x: real_time_data.get(x, {}).get('change_percent', 0))
            
            # === CALCULS AVEC EUR UNIQUEMENT ===
            grouped["Gain_EUR"] = grouped["Current_value_EUR"] - grouped["Purchase_value_EUR"]
            grouped["Gain_%"] = (grouped["Gain_EUR"] / grouped["Purchase_value_EUR"] * 100).round(1)

            # Calculer séparément pour l'affichage par devise
            eur_positions = grouped[grouped["Units"] == "EUR"]
            usd_positions = grouped[grouped["Units"] == "USD"]
            
            total_eur_original = eur_positions["Current value"].sum() if not eur_positions.empty else 0
            total_usd_original = usd_positions["Current value"].sum() if not usd_positions.empty else 0
            invested_eur = eur_positions["Purchase value"].sum() if not eur_positions.empty else 0
            invested_usd = usd_positions["Purchase value"].sum() if not usd_positions.empty else 0
            
            # TOTAL GÉNÉRAL en EUR (le seul qui compte pour les calculs)
            total_general_eur = grouped["Current_value_EUR"].sum()
            invested_general_eur = grouped["Purchase_value_EUR"].sum()
            gain_general = total_general_eur - invested_general_eur
            perf_general = (gain_general / invested_general_eur * 100) if invested_general_eur > 0 else 0
            
            # Calcul des dividendes
            df_div = st.session_state.get("df_dividendes", pd.DataFrame())
            if not df_div.empty:
                df_div["Montant net (€)"] = pd.to_numeric(df_div["Montant net (€)"], errors="coerce").fillna(0)
                div_total = df_div["Montant net (€)"].sum().round(1)
            else:
                div_total = 0

            total_global = (total_general_eur + div_total).round(1)
            total_rendement = ((total_global - invested_general_eur) / invested_general_eur * 100).round(1) if invested_general_eur > 0 else 0

            cache_manager = get_cache_manager()
            eurusd_rate = cache_manager.get_eurusd_rate()

            # === 1. PORTEFEUILLE PRINCIPAL (TOUT EN EUR) ===
            nb_tickers = len(grouped)
            st.markdown(f"### 📊 Portefeuille - {nb_tickers} titres")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💵 Montant investi", f"{invested_general_eur:,.0f} €")
            col2.metric("💰 Valeur actuelle", f"{total_general_eur:,.0f} €")
            col3.metric("🪙 Dividendes perçus", f"{div_total:,.0f} €")
            col4.metric("📈 Performance totale", f"+{(total_global - invested_general_eur):,.0f} €", 
                       delta=f"{total_rendement:.1f}%", delta_color="normal")

            # === 2. DÉTAIL PAR DEVISE (EN PLUS PETIT) ===
            with st.expander("💰 Détail par devise", expanded=False):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if not eur_positions.empty:
                        gain_eur = total_eur_original - invested_eur
                        perf_eur = (gain_eur / invested_eur * 100) if invested_eur > 0 else 0
                        st.metric(f"🇪🇺 Positions EUR ({len(eur_positions)})", f"{total_eur_original:,.0f} €", 
                                 delta=f"{gain_eur:+,.0f} € ({perf_eur:+.1f}%)")
                    else:
                        st.metric("🇪🇺 Positions EUR (0)", "0 €")
                
                with col2:
                    if not usd_positions.empty:
                        gain_usd = total_usd_original - invested_usd
                        perf_usd = (gain_usd / invested_usd * 100) if invested_usd > 0 else 0
                        st.metric(f"🇺🇸 Positions USD ({len(usd_positions)})", f"{total_usd_original:,.0f} $", 
                                 delta=f"{gain_usd:+,.0f} $ ({perf_usd:+.1f}%)")
                    else:
                        st.metric("🇺🇸 Positions USD (0)", "0 $")
                
                with col3:
                    if total_usd_original > 0:
                        st.metric(f"💱 USD→EUR (taux: {eurusd_rate:.4f})", f"{total_usd_original * eurusd_rate:,.0f} €")
                    else:
                        st.metric("💱 USD→EUR", "0 €")
                
                with col4:
                    st.metric("🌍 TOTAL GÉNÉRAL", f"{total_general_eur:,.0f} €", 
                             delta=f"{gain_general:+,.0f} € ({perf_general:+.1f}%)")

            # === 3. PERFORMANCE DU JOUR ===
            if real_time_data:
                perf_jour = []
                for ticker, data in real_time_data.items():
                    if data.get('change_percent') is not None:
                        entreprise_match = grouped[grouped['Ticker'] == ticker]
                        if not entreprise_match.empty:
                            entreprise = entreprise_match['Entreprise'].iloc[0]
                        else:
                            entreprise = ticker
                            
                        perf_jour.append({
                            'Ticker': ticker,
                            'Entreprise': entreprise,
                            'Variation %': data.get('change_percent', 0),
                            'Variation €': data.get('change', 0)
                        })
                
                if perf_jour:
                    perf_df_jour = pd.DataFrame(perf_jour).sort_values('Variation %', ascending=False)
                    
                    st.markdown("#### 🎯 Performance du jour")
                    col_top, col_flop = st.columns(2)
                    
                    with col_top:
                        st.markdown("**🟢 Top du jour**")
                        top_1 = perf_df_jour.head(1)
                        if not top_1.empty:
                            row = top_1.iloc[0]
                            st.markdown(f"**{row['Ticker']}** - {row['Entreprise'][:15]}... : **{row['Variation %']:+.1f}%** ({row['Variation €']:+.2f}€)")
                    
                    with col_flop:
                        st.markdown("**🔴 Flop du jour**")
                        bottom_1 = perf_df_jour.tail(1)
                        if not bottom_1.empty:
                            row = bottom_1.iloc[0]
                            st.markdown(f"**{row['Ticker']}** - {row['Entreprise'][:15]}... : **{row['Variation %']:+.1f}%** ({row['Variation €']:+.2f}€)")
                    
                    st.markdown("---")

            # === 4. TABLEAU DÉTAILLÉ AVEC GAIN TOTAL EUR ===
            st.markdown("### 📋 Détail du portefeuille")
            
            def highlight_perf(val):
                if isinstance(val, (int, float)):
                    if val > 0:
                        return 'color: green; font-weight: bold;'
                    elif val < 0:
                        return 'color: red; font-weight: bold;'
                return ''

            def highlight_variation(val):
                if isinstance(val, (int, float)):
                    if val > 0:
                        return 'background-color: rgba(0, 255, 0, 0.1); color: green; font-weight: bold;'
                    elif val < 0:
                        return 'background-color: rgba(255, 0, 0, 0.1); color: red; font-weight: bold;'
                return ''

            # Préparer les colonnes d'affichage
            grouped["Valeur actuelle"] = grouped.apply(
                lambda row: f"{row['Current value']:,.2f} {row['Units']}", axis=1
            )
            grouped["Gain original"] = grouped.apply(
                lambda row: f"{(row['Current value'] - row['Purchase value']):+,.2f} {row['Units']}", axis=1
            )
            # 🔥 AJOUTER LA COLONNE GAIN TOTAL EUR
            grouped["Gain total €"] = grouped["Gain_EUR"].round(1)

            display_columns = [
                "Ticker", "Entreprise", "Quantity", "Prix actuel", "Variation jour", "Variation jour %",
                "Valeur actuelle", "Gain original", "Gain total €", "Gain_%", "Compte", "Type", "Secteur", "Category"
            ]
            
            grouped_display = grouped[display_columns].round(2)
            
            styled_df = grouped_display.style.applymap(highlight_perf, subset=["Gain_%", "Gain total €"])
            styled_df = styled_df.applymap(highlight_variation, subset=["Variation jour", "Variation jour %"])
            styled_df = styled_df.format({
                "Prix actuel": "{:.2f}",
                "Variation jour": "{:+.2f}",
                "Variation jour %": "{:+.2f} %",
                "Gain_%": "{:.1f} %",
                "Gain total €": "{:+.1f} €",
                "Quantity": "{:.1f}"
            })
            
            st.dataframe(styled_df, use_container_width=True)

            # === 5. ÉVOLUTION DU RENDEMENT CUMULÉ ===
            st.markdown("### 📈 Évolution du rendement cumulé du portefeuille")
            
            # Sélecteur de période
            col_selector1, col_empty1 = st.columns([1, 3])
            with col_selector1:
                periode_perf = st.selectbox(
                    "Période d'affichage :",
                    ["Max", "6 mois", "3 mois", "1 mois"],
                    index=0,
                    key="periode_perf"
                )

            if not df.empty and "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                start_date = df["Date"].min().date()
                end_date = datetime.today().date()
                
                # Ajustement de la période selon le sélecteur
                if periode_perf == "6 mois":
                    start_date_adjusted = max(start_date, (datetime.today() - timedelta(days=180)).date())
                elif periode_perf == "3 mois":
                    start_date_adjusted = max(start_date, (datetime.today() - timedelta(days=90)).date())
                elif periode_perf == "1 mois":
                    start_date_adjusted = max(start_date, (datetime.today() - timedelta(days=30)).date())
                else:  # Max
                    start_date_adjusted = start_date
                
                # Utilisation d'une fréquence plus fine pour un graphique plus lisse
                date_range = pd.date_range(start=start_date_adjusted, end=end_date, freq="1D")

                tickers = df["Ticker"].dropna().unique()
                hist_prices = {}

                try:
                    # Récupération d'historiques plus détaillés
                    hist_df = yf.download(
                        tickers=list(tickers),
                        start=start_date_adjusted,
                        end=end_date + timedelta(days=1),
                        interval="1d",
                        group_by='ticker',
                        auto_adjust=True,
                        progress=False
                    )

                    for ticker in tickers:
                        try:
                            if isinstance(hist_df.columns, pd.MultiIndex):
                                prices = hist_df[ticker]["Close"].dropna()
                            else:
                                prices = hist_df["Close"].dropna()
                            hist_prices[ticker] = prices
                        except Exception as e:
                            st.warning(f"❌ Erreur pour {ticker} : {e}")
                except Exception as e:
                    st.error(f"Erreur lors du chargement des historiques : {e}")

                # Calcul du portefeuille avec plus de détails
                portefeuille = []
                
                for date in date_range:
                    total_value_eur = 0
                    total_cost_eur = 0
                    
                    for _, row in df.iterrows():
                        achat_date = pd.to_datetime(row["Date"])
                        if achat_date > date:
                            continue
                            
                        ticker = row["Ticker"]
                        quantity = row["Quantity"]
                        devise = row["Units"]
                        cost = row["Purchase value"]

                        try:
                            price_series = hist_prices.get(ticker)
                            if price_series is not None and len(price_series) > 0:
                                # Trouver le prix le plus proche de la date
                                valid_dates = price_series.index[price_series.index <= pd.Timestamp(date)]
                                if len(valid_dates) > 0:
                                    closest_date = valid_dates.max()
                                    price = price_series.loc[closest_date]
                                    value = price * quantity
                                    
                                    # 🔥 CONVERSION AUTOMATIQUE EN EUR pour le graphique
                                    if str(devise).upper() == "USD":
                                        cache_manager = get_cache_manager()
                                        eurusd_rate = cache_manager.get_eurusd_rate()
                                        value *= eurusd_rate
                                        cost *= eurusd_rate
                                            
                                    total_value_eur += value
                                    total_cost_eur += cost
                        except Exception:
                            continue
                    
                    if total_cost_eur > 0:
                        rendement = (total_value_eur - total_cost_eur) / total_cost_eur * 100
                        portefeuille.append({
                            "Date": date, 
                            "Rendement (%)": rendement,
                            "Valeur portefeuille": total_value_eur,
                            "Montant investi": total_cost_eur,
                            "Gain/Perte": total_value_eur - total_cost_eur
                        })

                perf_df = pd.DataFrame(portefeuille).dropna()

                if not perf_df.empty:
                    # Création du graphique
                    fig = go.Figure()

                    # Ligne principale de performance
                    fig.add_trace(go.Scatter(
                        x=perf_df["Date"],
                        y=perf_df["Rendement (%)"],
                        mode='lines+markers',
                        name='Rendement (%)',
                        line=dict(width=3, color='#1f77b4'),
                        marker=dict(size=4),
                        hovertemplate='<b>Date:</b> %{x}<br>' +
                                      '<b>Rendement:</b> %{y:.2f}%<br>' +
                                      '<b>Valeur:</b> €%{customdata[0]:,.0f}<br>' +
                                      '<b>Investi:</b> €%{customdata[1]:,.0f}<br>' +
                                      '<extra></extra>',
                        customdata=perf_df[["Valeur portefeuille", "Montant investi"]].values
                    ))

                    # Zone de remplissage
                    perf_positive = perf_df[perf_df["Rendement (%)"] >= 0].copy()
                    perf_negative = perf_df[perf_df["Rendement (%)"] < 0].copy()
                    
                    if not perf_positive.empty:
                        fig.add_trace(go.Scatter(
                            x=perf_positive["Date"],
                            y=perf_positive["Rendement (%)"],
                            fill='tozeroy',
                            fillcolor='rgba(0, 255, 0, 0.1)',
                            line=dict(width=0),
                            showlegend=False,
                            hoverinfo='skip'
                        ))
                    
                    if not perf_negative.empty:
                        fig.add_trace(go.Scatter(
                            x=perf_negative["Date"],
                            y=perf_negative["Rendement (%)"],
                            fill='tozeroy',
                            fillcolor='rgba(255, 0, 0, 0.1)',
                            line=dict(width=0),
                            showlegend=False,
                            hoverinfo='skip'
                        ))

                    # Ligne de référence à 0%
                    fig.add_hline(y=0, line_dash="dash", line_color="rgba(128, 128, 128, 0.8)", line_width=2)

                    # Statistiques pour le titre
                    rendement_actuel = perf_df["Rendement (%)"].iloc[-1]
                    rendement_max = perf_df["Rendement (%)"].max()
                    rendement_min = perf_df["Rendement (%)"].min()
                    volatilite = perf_df["Rendement (%)"].std()

                    # Configuration du layout
                    fig.update_layout(
                        title=dict(
                            text=f"📈 Performance du Portefeuille<br>" +
                                 f"<sub>Actuel: {rendement_actuel:.1f}% • Max: {rendement_max:.1f}% • Min: {rendement_min:.1f}% • Volatilité: {volatilite:.1f}%</sub>",
                            x=0.5,
                            font=dict(size=16)
                        ),
                        xaxis_title="Date",
                        yaxis_title="Rendement (%)",
                        height=600,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(size=12),
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        ),
                        hovermode='x unified'
                    )
                    
                    # Amélioration des axes
                    fig.update_xaxes(
                        showgrid=True, 
                        gridwidth=1, 
                        gridcolor='rgba(128,128,128,0.2)',
                        showline=True,
                        linewidth=1,
                        linecolor='rgba(128,128,128,0.3)',
                        tickformat='%d/%m/%Y'
                    )
                    fig.update_yaxes(
                        showgrid=True, 
                        gridwidth=1, 
                        gridcolor='rgba(128,128,128,0.2)',
                        showline=True,
                        linewidth=1,
                        linecolor='rgba(128,128,128,0.3)',
                        ticksuffix='%',
                        zeroline=True,
                        zerolinewidth=2,
                        zerolinecolor='rgba(128,128,128,0.5)'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Aucune donnée suffisante pour afficher le rendement.")

            # === 6. SUIVI MENSUEL DES INVESTISSEMENTS ===
            st.markdown("### 📅 Suivi mensuel des investissements")
            
            # Sélecteur de période pour le graphique mensuel
            col_selector2, col_empty2 = st.columns([1, 3])
            with col_selector2:
                periode_mensuel = st.selectbox(
                    "Période d'affichage :",
                    ["Max", "6 mois", "3 mois", "1 mois"],
                    index=0,
                    key="periode_mensuel"
                )

            # Extraction des données nécessaires - UTILISER LES DONNÉES EUR
            df_monthly = st.session_state.df_data.copy()
            df_monthly.columns = df_monthly.columns.str.strip()
            df_monthly["Date"] = pd.to_datetime(df_monthly["Date"], errors="coerce")
            df_monthly = df_monthly.dropna(subset=["Date", "Purchase value", "Category"])
            
            # 🔥 CONVERTIR LES MONTANTS EN EUR pour le graphique mensuel
            df_monthly = add_eur_columns(df_monthly)
            
            # Filtrage selon la période sélectionnée
            end_date_monthly = datetime.today()
            if periode_mensuel == "6 mois":
                start_date_monthly = end_date_monthly - timedelta(days=180)
            elif periode_mensuel == "3 mois":
                start_date_monthly = end_date_monthly - timedelta(days=90)
            elif periode_mensuel == "1 mois":
                start_date_monthly = end_date_monthly - timedelta(days=30)
            else:  # Max
                start_date_monthly = df_monthly["Date"].min()
            
            df_monthly = df_monthly[df_monthly["Date"] >= start_date_monthly]

            # Construction de l'étiquette temporelle
            df_monthly["Mois"] = df_monthly["Date"].dt.month
            df_monthly["Année"] = df_monthly["Date"].dt.year
            mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                       "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
            df_monthly["Mois_nom"] = df_monthly["Mois"].apply(lambda x: mois_fr[x-1])
            df_monthly["Label"] = df_monthly["Année"].astype(str) + " " + df_monthly["Mois_nom"]

            # Ordre chronologique correct
            df_monthly["Label"] = pd.Categorical(
                df_monthly["Label"],
                categories=sorted(df_monthly["Label"].unique(), key=lambda x: (int(x.split()[0]), mois_fr.index(x.split()[1]))),
                ordered=True
            )

            # 🔥 UTILISER Purchase_value_EUR pour le graphique mensuel
            df_grouped_monthly = df_monthly.groupby(["Label", "Category"])["Purchase_value_EUR"].sum().reset_index()
            df_totaux_monthly = df_grouped_monthly.groupby("Label")["Purchase_value_EUR"].sum().reset_index().rename(columns={"Purchase_value_EUR": "Total mois"})
            df_grouped_monthly = df_grouped_monthly.merge(df_totaux_monthly, on="Label", how="left")
            st.session_state.df_totaux = df_totaux_monthly

            # Moyenne mensuelle
            moyenne_mensuelle = df_totaux_monthly["Total mois"].mean().round(1)

            # Graphique
            fig_monthly = px.bar(
                df_grouped_monthly,
                x="Label",
                y="Purchase_value_EUR",
                color="Category",
                labels={"Label": "Mois", "Purchase_value_EUR": "Montant (€)", "Category": "Catégorie"},
                title=f"📊 Répartition mensuelle des investissements (Moyenne : {moyenne_mensuelle:,.0f} € / mois)"
            )

            # Ajout du texte total mensuel au-dessus
            for i, row in df_totaux_monthly.iterrows():
                fig_monthly.add_annotation(
                    x=row["Label"],
                    y=row["Total mois"],
                    text=f"{row['Total mois']:,.0f} €",
                    showarrow=False,
                    yshift=8,
                    font=dict(size=12)
                )

            fig_monthly.update_layout(barmode="stack", height=500, xaxis_tickangle=-25)
            st.plotly_chart(fig_monthly, use_container_width=True)

            # === 7. ANALYSE DES PERFORMANCES PAR TITRE ===
            st.markdown("### 📊 Analyse des performances par titre")

            col_left, col_right = st.columns(2)
            
            with col_left:
                # 🔥 UTILISER LES GAINS EUR POUR LES GRAPHIQUES
                gain_sorted = grouped.sort_values("Gain_EUR", ascending=False).copy()
                gain_sorted["Gain txt"] = gain_sorted["Gain_EUR"].map(lambda x: f"{x:,.1f} €")

                fig_gain = px.bar(
                    gain_sorted,
                    x="Gain_EUR",
                    y="Ticker",
                    orientation="h",
                    color="Gain_EUR",
                    color_continuous_scale="RdYlGn",
                    text="Gain txt",
                    title="💰 Gains/Pertes (équivalent EUR)"
                )
                fig_gain.update_layout(height=500)
                fig_gain.update_traces(textposition='outside')
                st.plotly_chart(fig_gain, use_container_width=True)

            with col_right:
                gain_pct_sorted = grouped.sort_values("Gain_%", ascending=False).copy()
                gain_pct_sorted["Gain % txt"] = gain_pct_sorted["Gain_%"].map(lambda x: f"{x:.1f} %")

                fig_gain_pct = px.bar(
                    gain_pct_sorted,
                    x="Gain_%",
                    y="Ticker",
                    orientation="h",
                    color="Gain_%",
                    color_continuous_scale="RdYlGn",
                    text="Gain % txt",
                    title="📈 Performance en pourcentage"
                )
                fig_gain_pct.update_layout(height=500)
                fig_gain_pct.update_traces(textposition='outside')
                st.plotly_chart(fig_gain_pct, use_container_width=True)
            
        else:
            st.warning("⚠️ Aucune valeur actuelle trouvée. Cliquez sur 'Actualiser les cours' pour récupérer les prix.")
    else:
        st.info("💡 Veuillez charger un fichier Excel via la sidebar.")
