import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np

def display_tab_projections():
    st.markdown("## 📈 Projections du Portefeuille")

    # 🚨 Guard clause si pas de fichier Excel chargé
    if "df_data" not in st.session_state or st.session_state.df_data.empty:
        st.info("💡 Aucun fichier Excel chargé. Veuillez importer votre fichier dans la barre latérale.")
        return

    # === AVERTISSEMENTS ===
    st.warning("""
    ⚠️ **AVERTISSEMENT IMPORTANT**
    
    Ces projections sont des **estimations** basées sur des hypothèses et ne représentent en rien des résultats garantis.
    
    • L'investissement comporte des **risques** de perte en capital
    • Les performances passées ne préjugent pas des performances futures
    • Les dividendes peuvent être **réduits ou supprimés** par les entreprises
    • Les conditions de marché peuvent **évoluer défavorablement**
    
    Ces calculs sont fournis à titre **informatif uniquement** et ne constituent pas un conseil en investissement.
    """)

    # === CALCULS DE BASE ===
    df = st.session_state.df_data.copy()
    df.columns = df.columns.map(lambda x: str(x).strip())
    df["Date"] = pd.to_datetime(df.get("Date", []), errors="coerce")
    df = df.dropna(subset=["Date", "Purchase value"])
    
    valeur_actuelle_totale = df["Current value"].sum() if "Current value" in df.columns else df["Purchase value"].sum()
    montant_total_investi = df["Purchase value"].sum()
    duree_investissement = (datetime.now() - df["Date"].min()).days / 365.25
    
    # Calculs dividendes
    df_div = st.session_state.df_dividendes.copy()
    dividendes_total = 0
    dividendes_12_mois = 0
    
    if not df_div.empty:
        df_div["Date paiement"] = pd.to_datetime(df_div["Date paiement"], errors='coerce')
        df_div = df_div.dropna(subset=["Date paiement"])
        df_div["Montant net (€)"] = pd.to_numeric(df_div["Montant net (€)"], errors="coerce").fillna(0)
        
        dividendes_total = df_div["Montant net (€)"].sum()
        dividendes_12_mois = df_div[df_div["Date paiement"] >= datetime.now() - timedelta(days=365)]["Montant net (€)"].sum()
    
    rendement_dividende = (dividendes_12_mois / valeur_actuelle_totale * 100) if valeur_actuelle_totale > 0 else 0

    # Calcul investissement mensuel moyen
    df["Année-Mois"] = df["Date"].dt.to_period("M")
    investissements_mensuels = df.groupby("Année-Mois")["Purchase value"].sum()
    investissement_moyen = investissements_mensuels.mean() if len(investissements_mensuels) > 0 else 0

    # === VÉRIFICATION DE L'ANCIENNETÉ ===
    st.markdown("### ⚙️ Paramètres de projection")
    
    if duree_investissement < 1:
        st.warning("⚠️ Ancienneté insuffisante pour projection fiable (< 1 an d'historique)")
        st.info("💡 Les projections seront basées sur des données estimées et moyennes du marché.")

    # Calculer le rendement réel du portefeuille depuis Tab1
    rendement_reel_capital = 0
    if "df_data" in st.session_state and not st.session_state.df_data.empty:
        df_perf = st.session_state.df_data.copy()
        if "Current value" in df_perf.columns and "Purchase value" in df_perf.columns:
            total_current = df_perf["Current value"].sum()
            total_purchase = df_perf["Purchase value"].sum()
            if total_purchase > 0 and duree_investissement >= 1:
                # Seulement calculer si on a au moins 1 an d'historique
                rendement_reel_capital = ((total_current - total_purchase) / total_purchase) * 100 / duree_investissement
    
    # Calculer le rendement dividende réel observé ou utiliser une estimation
    rendement_dividende_reel = rendement_dividende if duree_investissement >= 1 else 2.5  # 2.5% par défaut si pas assez de données
    
    # Si pas assez d'ancienneté, utiliser des valeurs moyennes du marché
    if duree_investissement < 1 or rendement_reel_capital == 0:
        rendement_reel_capital = 7.0  # Rendement moyen du marché

    # Affichage des métriques réelles ou estimées
    st.markdown("#### 📊 Performances observées/estimées (base de projection)")
    
    col_real1, col_real2, col_real3 = st.columns(3)
    
    with col_real1:
        label_capital = "📈 Rendement capital annuel"
        help_capital = "Basé sur la performance réelle de votre portefeuille" if duree_investissement >= 1 else "Estimation basée sur les moyennes du marché (7%/an)"
        st.metric(
            label_capital,
            f"{rendement_reel_capital:.1f}%",
            help=help_capital
        )
    
    with col_real2:
        label_div = "💸 Rendement dividende annuel"
        help_div = "Basé sur vos dividendes des 12 derniers mois" if duree_investissement >= 1 else "Estimation moyenne du marché (2.5%/an)"
        st.metric(
            label_div,
            f"{rendement_dividende_reel:.2f}%",
            help=help_div
        )
    
    with col_real3:
        st.metric(
            "📅 Ancienneté du portefeuille",
            f"{duree_investissement:.1f} ans",
            help="Période sur laquelle sont basées les projections"
        )

    # Paramètre unique : investissement futur
    st.markdown("#### ⚙️ Paramètre de projection")
    
    col_param1, col_param2 = st.columns([1, 1])
    
    with col_param1:
        investissement_futur = st.number_input(
            "Investissement mensuel futur (€)",
            min_value=0.0, max_value=10000.0,
            value=float(max(100, investissement_moyen)),
            step=50.0,
            help="Montant que vous prévoyez d'investir chaque mois"
        )

    # Utiliser les valeurs réelles pour les projections
    rendement_annuel = rendement_reel_capital

    # === SITUATION ACTUELLE ===
    st.markdown("---")
    st.markdown("### 📊 Situation actuelle du portefeuille")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("💰 Valeur portefeuille", f"{valeur_actuelle_totale:,.0f} €")
    
    with col2:
        rendement_global = ((valeur_actuelle_totale - montant_total_investi) / montant_total_investi * 100) if montant_total_investi > 0 else 0
        st.metric("📈 Performance capital", f"{rendement_global:+.1f}%")
    
    with col3:
        st.metric("💸 Dividendes/an", f"{dividendes_12_mois:,.0f} €")
    
    with col4:
        total_global = valeur_actuelle_totale + dividendes_total
        st.metric("🧮 Total capital + dividendes", f"{total_global:,.0f} €")
    
    with col5:
        total_rendement = ((total_global - montant_total_investi) / montant_total_investi * 100) if montant_total_investi > 0 else 0
        st.metric("📈 Performance totale", f"{total_rendement:+.1f}%")

    # === PROJECTIONS BASÉES SUR LES DONNÉES RÉELLES OU ESTIMÉES ===
    st.markdown("---")
    st.markdown("### 📈 Projections sur 10 ans")
    
    annees = list(range(1, 11))
    
    # Projection unique basée sur les données réelles
    capital_investi = []
    capital_total = []
    dividendes_annuels = []
    dividendes_cumules = []
    
    capital_actuel = valeur_actuelle_totale
    dividendes_cumules_actuel = dividendes_total
    
    for annee in annees:
        # Capital investi cumulé
        capital_inv_cumul = montant_total_investi + (investissement_futur * 12 * annee)
        capital_investi.append(capital_inv_cumul)
        
        # Croissance du capital basée sur le rendement observé
        apports_annuels = investissement_futur * 12
        capital_actuel = capital_actuel * (1 + rendement_annuel/100) + apports_annuels
        capital_total.append(capital_actuel)
        
        # Dividendes basés sur le rendement dividende observé
        dividendes_annuels_val = capital_actuel * rendement_dividende_reel / 100
        dividendes_annuels.append(dividendes_annuels_val)
        
        # Dividendes cumulés
        dividendes_cumules_actuel += dividendes_annuels_val
        dividendes_cumules.append(dividendes_cumules_actuel)
    
    # Créer un scénario conservateur (-20%) et optimiste (+20%) pour donner une fourchette
    capital_total_conservateur = []
    capital_total_optimiste = []
    dividendes_conservateur = []
    dividendes_optimiste = []
    
    capital_actuel_cons = valeur_actuelle_totale
    capital_actuel_opt = valeur_actuelle_totale
    
    for annee in annees:
        apports_annuels = investissement_futur * 12
        
        # Scénario conservateur (-20%)
        capital_actuel_cons = capital_actuel_cons * (1 + (rendement_annuel * 0.8)/100) + apports_annuels
        capital_total_conservateur.append(capital_actuel_cons)
        dividendes_conservateur.append(capital_actuel_cons * (rendement_dividende_reel * 0.8) / 100)
        
        # Scénario optimiste (+20%)
        capital_actuel_opt = capital_actuel_opt * (1 + (rendement_annuel * 1.2)/100) + apports_annuels
        capital_total_optimiste.append(capital_actuel_opt)
        dividendes_optimiste.append(capital_actuel_opt * (rendement_dividende_reel * 1.2) / 100)

    # === GRAPHIQUES DE PROJECTIONS ===
    
    # Sélecteur de type de graphique
    st.markdown("#### 📊 Visualisations des projections")
    
    col_select1, col_select2 = st.columns(2)
    
    with col_select1:
        graph_type = st.selectbox(
            "Type de visualisation",
            ["Capital total", "Dividendes annuels", "Vue combinée"],
            key="projection_graph_type"
        )
    
    with col_select2:
        show_scenarios = st.checkbox(
            "Afficher les scénarios (±20%)",
            value=True,
            key="show_scenarios"
        )

    if graph_type == "Capital total":
        # === GRAPHIQUE CAPITAL ===
        fig_capital = go.Figure()
        
        # Capital investi (base)
        fig_capital.add_trace(go.Bar(
            x=annees,
            y=capital_investi,
            name="Capital investi",
            marker_color="#94a3b8",
            hovertemplate='<b>Année %{x}</b><br>Capital investi: %{y:,.0f}€<extra></extra>'
        ))
        
        # Plus-values (empilé) - scénario médian
        plus_values = [total - investi for total, investi in zip(capital_total, capital_investi)]
        fig_capital.add_trace(go.Bar(
            x=annees,
            y=plus_values,
            name="Plus-values (observé)",
            marker_color="#3b82f6",
            hovertemplate='<b>Année %{x}</b><br>Plus-values: %{y:,.0f}€<extra></extra>'
        ))
        
        if show_scenarios:
            # Fourchettes (traits)
            fig_capital.add_trace(go.Scatter(
                x=annees,
                y=capital_total_conservateur,
                mode='markers+lines',
                name="Scénario conservateur (-20%)",
                marker=dict(color="orange", symbol="triangle-down"),
                line=dict(dash='dash'),
                hovertemplate='<b>Année %{x}</b><br>Capital conservateur: %{y:,.0f}€<extra></extra>'
            ))
            
            fig_capital.add_trace(go.Scatter(
                x=annees,
                y=capital_total_optimiste,
                mode='markers+lines',
                name="Scénario optimiste (+20%)", 
                marker=dict(color="green", symbol="triangle-up"),
                line=dict(dash='dash'),
                hovertemplate='<b>Année %{x}</b><br>Capital optimiste: %{y:,.0f}€<extra></extra>'
            ))
        
        fig_capital.update_layout(
            title=f"💰 Évolution du capital (Rendement: {rendement_annuel:.1f}% {'observé' if duree_investissement >= 1 else 'estimé'})",
            xaxis_title="Années",
            yaxis_title="Montant (€)",
            barmode='stack',
            height=500,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_capital, use_container_width=True)

    elif graph_type == "Dividendes annuels":
        # === GRAPHIQUE DIVIDENDES ===
        fig_div = go.Figure()
        
        fig_div.add_trace(go.Bar(
            x=annees,
            y=dividendes_annuels,
            name=f"Dividendes projetés ({rendement_dividende_reel:.2f}%)",
            marker_color="#22c55e",
            hovertemplate='<b>Année %{x}</b><br>Dividendes: %{y:,.0f}€<extra></extra>'
        ))
        
        if show_scenarios:
            # Fourchettes de dividendes
            fig_div.add_trace(go.Scatter(
                x=annees,
                y=dividendes_conservateur,
                mode='markers+lines',
                name="Conservateur (-20%)",
                marker=dict(color="orange", symbol="triangle-down"),
                line=dict(dash='dash'),
                hovertemplate='<b>Année %{x}</b><br>Dividendes conservateurs: %{y:,.0f}€<extra></extra>'
            ))
            
            fig_div.add_trace(go.Scatter(
                x=annees,
                y=dividendes_optimiste,
                mode='markers+lines',
                name="Optimiste (+20%)",
                marker=dict(color="darkgreen", symbol="triangle-up"),
                line=dict(dash='dash'),
                hovertemplate='<b>Année %{x}</b><br>Dividendes optimistes: %{y:,.0f}€<extra></extra>'
            ))
        
        fig_div.update_layout(
            title=f"💸 Dividendes annuels projetés",
            xaxis_title="Années",
            yaxis_title="Dividendes (€)",
            height=500,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_div, use_container_width=True)

    else:  # Vue combinée
        # === GRAPHIQUE COMBINÉ ===
        fig_combined = go.Figure()
        
        # Capital total
        fig_combined.add_trace(go.Scatter(
            x=annees,
            y=capital_total,
            mode='lines+markers',
            name='Capital total',
            line=dict(color='#3b82f6', width=3),
            marker=dict(size=8),
            yaxis='y',
            hovertemplate='<b>Année %{x}</b><br>Capital: %{y:,.0f}€<extra></extra>'
        ))
        
        # Dividendes cumulés
        fig_combined.add_trace(go.Scatter(
            x=annees,
            y=dividendes_cumules,
            mode='lines+markers',
            name='Dividendes cumulés',
            line=dict(color='#22c55e', width=3),
            marker=dict(size=8),
            yaxis='y',
            hovertemplate='<b>Année %{x}</b><br>Dividendes cumulés: %{y:,.0f}€<extra></extra>'
        ))
        
        # Total combiné (capital + dividendes)
        total_combine = [cap + div for cap, div in zip(capital_total, dividendes_cumules)]
        fig_combined.add_trace(go.Scatter(
            x=annees,
            y=total_combine,
            mode='lines+markers',
            name='Total (Capital + Dividendes)',
            line=dict(color='#8b5cf6', width=4, dash='dot'),
            marker=dict(size=10),
            yaxis='y',
            hovertemplate='<b>Année %{x}</b><br>Total: %{y:,.0f}€<extra></extra>'
        ))
        
        # Dividendes annuels (axe secondaire)
        fig_combined.add_trace(go.Bar(
            x=annees,
            y=dividendes_annuels,
            name='Dividendes annuels',
            marker_color='rgba(34, 197, 94, 0.3)',
            yaxis='y2',
            hovertemplate='<b>Année %{x}</b><br>Dividendes annuels: %{y:,.0f}€<extra></extra>'
        ))
        
        fig_combined.update_layout(
            title="📊 Vue d'ensemble : Capital et Dividendes",
            xaxis_title="Années",
            height=600,
            hovermode='x unified',
            yaxis=dict(
                title="Montant cumulé (€)",
                side="left"
            ),
            yaxis2=dict(
                title="Dividendes annuels (€)",
                side="right",
                overlaying="y",
                showgrid=False
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig_combined, use_container_width=True)

    # === TABLEAU RÉCAPITULATIF ===
    st.markdown("### 📊 Tableau récapitulatif des projections")
    
    # Calculer les totaux (capital + dividendes cumulés)
    total_conservateur = [cap + div_cum for cap, div_cum in zip(capital_total_conservateur, [sum(dividendes_conservateur[:i+1]) + dividendes_total for i in range(len(dividendes_conservateur))])]
    total_median = [cap + div_cum for cap, div_cum in zip(capital_total, dividendes_cumules)]
    total_optimiste = [cap + div_cum for cap, div_cum in zip(capital_total_optimiste, [sum(dividendes_optimiste[:i+1]) + dividendes_total for i in range(len(dividendes_optimiste))])]
    
    df_recap = pd.DataFrame({
        "Année": annees,
        "Capital investi (€)": [f"{x:,.0f}" for x in capital_investi],
        "Capital - Conservateur (€)": [f"{x:,.0f}" for x in capital_total_conservateur],
        "Capital - Médian (€)": [f"{x:,.0f}" for x in capital_total],
        "Capital - Optimiste (€)": [f"{x:,.0f}" for x in capital_total_optimiste],
        "Dividendes annuels (€)": [f"{x:,.0f}" for x in dividendes_annuels],
        "Total (Capital + Div.) (€)": [f"{x:,.0f}" for x in total_median]
    })
    
    st.dataframe(df_recap, use_container_width=True, hide_index=True)

    # === OBJECTIFS ET MILESTONES ===
    st.markdown("---")
    st.markdown("### 🎯 Objectifs et milestones")
    
    col_obj1, col_obj2 = st.columns(2)
    
    with col_obj1:
        st.markdown("#### 💰 Objectifs de capital")
        
        # Calculer quand certains objectifs seront atteints
        objectifs_capital = [100000, 250000, 500000, 1000000]
        
        for objectif in objectifs_capital:
            # Trouver l'année où l'objectif est atteint
            annee_objectif = None
            for i, montant in enumerate(capital_total):
                if montant >= objectif:
                    annee_objectif = i + 1
                    break
            
            if annee_objectif:
                st.success(f"🎯 **{objectif:,.0f}€** atteint en **année {annee_objectif}** ({datetime.now().year + annee_objectif})")
            else:
                st.info(f"🎯 **{objectif:,.0f}€** non atteint dans les 10 ans projetées")
    
    with col_obj2:
        st.markdown("#### 💸 Objectifs de dividendes mensuels")
        
        # Calculer les dividendes mensuels équivalents
        objectifs_div_mensuels = [500, 1000, 2000, 5000]
        
        for objectif_mensuel in objectifs_div_mensuels:
            objectif_annuel = objectif_mensuel * 12
            # Trouver l'année où l'objectif est atteint
            annee_objectif = None
            for i, dividendes in enumerate(dividendes_annuels):
                if dividendes >= objectif_annuel:
                    annee_objectif = i + 1
                    break
            
            if annee_objectif:
                st.success(f"💸 **{objectif_mensuel:,.0f}€/mois** atteint en **année {annee_objectif}** ({datetime.now().year + annee_objectif})")
            else:
                st.info(f"💸 **{objectif_mensuel:,.0f}€/mois** non atteint dans les 10 ans projetées")

    # === INFORMATIONS SUR LA PROJECTION ===
    st.markdown("---")
    
    if duree_investissement >= 1:
        st.info(f"""
        **📋 Base des projections :**
        
        • **Rendement capital :** {rendement_annuel:.1f}%/an (performance observée sur {duree_investissement:.1f} ans)
        • **Rendement dividende :** {rendement_dividende_reel:.2f}%/an (basé sur les 12 derniers mois)
        • **Investissement mensuel :** {investissement_futur:,.0f}€ (paramétrable)
        • **Scénarios :** Conservateur (-20%), Médian (observé), Optimiste (+20%)
        
        ⚠️ Ces projections sont basées sur vos performances passées et ne garantissent pas les résultats futurs.
        """)
    else:
        st.warning(f"""
        **📋 Base des projections (données insuffisantes) :**
        
        • **Rendement capital :** {rendement_annuel:.1f}%/an (estimation moyenne du marché)
        • **Rendement dividende :** {rendement_dividende_reel:.2f}%/an (estimation moyenne du marché)
        • **Investissement mensuel :** {investissement_futur:,.0f}€ (paramétrable)
        • **Ancienneté :** {duree_investissement:.1f} ans (< 1 an requis pour fiabilité)
        
        ⚠️ Ces projections sont basées sur des moyennes du marché et non sur vos performances réelles.
        Attendez d'avoir au moins 1 an d'historique pour des projections plus fiables.
        """)
