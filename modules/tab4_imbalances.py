import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from modules.tab0_constants import SECTOR_COLORS, SECTEUR_PAR_TYPE, CATEGORY_LIST

def add_eur_columns_tab4(df):
    """
    🔥 Ajouter les colonnes EUR converties pour tab4
    """
    from modules.yfinance_cache_manager import get_cache_manager
    
    cache_manager = get_cache_manager()
    eurusd_rate = cache_manager.get_eurusd_rate()
    
    df = df.copy()
    
    # S'assurer que Units existe
    if "Units" not in df.columns:
        df["Units"] = "EUR"
    df["Units"] = df["Units"].fillna("EUR").astype(str)
    
    # 🔥 CRÉER LES COLONNES EUR POUR TOUT
    df["Current_value_EUR"] = df["Current value"].copy()
    
    # Convertir SEULEMENT les lignes USD
    for idx, row in df.iterrows():
        if str(row["Units"]).upper() == "USD":
            if pd.notnull(row["Current value"]):
                df.loc[idx, "Current_value_EUR"] = row["Current value"] * eurusd_rate
    
    return df

def display_tab4_imbalances():
    st.header("🎯 Analyse des déséquilibres et risques du portefeuille")
    
    # 🚨 Guard clause si pas de fichier Excel chargé
    if "df_data" not in st.session_state or st.session_state.df_data.empty:
        st.info("💡 Aucun fichier Excel chargé. Veuillez importer votre fichier dans la barre latérale.")
        return

    df = st.session_state.df_data.copy()
    df.columns = df.columns.map(lambda x: str(x).strip())

    # Vérifier que la colonne Current value existe
    if "Current value" not in df.columns:
        st.warning("⚠️ Exécutez d'abord l'onglet 'Portefeuille' pour récupérer les valeurs actuelles.")
        return

    # 🔥 AJOUTER LES COLONNES EUR CONVERTIES
    df = add_eur_columns_tab4(df)

    # 🔥 UTILISER Current_value_EUR pour TOUS LES CALCULS !
    df["Current value"] = df["Current_value_EUR"]  # Remplacer pour le reste du code

    # Normalisation de la colonne
    df["Current value"] = pd.to_numeric(df["Current value"], errors="coerce").fillna(0)
    total_value = df["Current value"].sum()

    if total_value <= 0:
        st.error("❌ Aucune valeur de portefeuille détectée.")
        return

    limits = st.session_state.df_limits.copy()
    limits.columns = limits.columns.str.strip()

    # Préparation des données de base
    actions_only = df[df["Type"] == "Actions"].copy()
    etf_only = df[df["Type"] == "ETF"].copy()
    actions_total = actions_only["Current value"].sum()
    etf_total = etf_only["Current value"].sum()

    # === 1) 🚨 ALERTES CRITIQUES ===
    st.markdown("### 🚨 Alertes critiques")
    st.info("💱 **Analyse basée sur les valeurs converties en EUR** (USD automatiquement converti)")
    
    alerts = []
    urgent_actions = []
    
    # Concentration par entreprise Actions (>10% du PORTEFEUILLE TOTAL)
    if actions_total > 0:
        df_companies_actions = actions_only.groupby("Entreprise")["Current value"].sum().reset_index()
        df_companies_actions["% portefeuille total"] = (df_companies_actions["Current value"] / total_value * 100).round(2)
        overweight_companies = df_companies_actions[df_companies_actions["% portefeuille total"] > 10]
        
        if not overweight_companies.empty:
            for _, company in overweight_companies.iterrows():
                excess_pct = company['% portefeuille total'] - 10
                excess_amount = (excess_pct / 100) * total_value
                alerts.append({
                    "type": "🔴 RISQUE ÉLEVÉ", 
                    "message": f"**{company['Entreprise']}** représente {company['% portefeuille total']:.1f}% du portefeuille total (>10%)",
                    "severity": "error"
                })
                urgent_actions.append(f"Réduire {company['Entreprise']} : {company['% portefeuille total']:.1f}% → ≤10% (Vendre ~{excess_amount:,.0f}€)")
    
    # ETF avec limites depuis df_limits
    if not etf_only.empty and not limits.empty:
        df_etf_categories = etf_only.groupby("Category")["Current value"].sum().reset_index()
        df_etf_categories["% des ETF"] = (df_etf_categories["Current value"] / etf_total * 100).round(2)
        
        etf_limits = limits.query("Variable1=='Category' and Variable2 in ['S&P500', 'Euro STOXX50', 'NASDAQ 100']")
        
        if not etf_limits.empty:
            for _, limit_row in etf_limits.iterrows():
                category = limit_row['Variable2']
                seuil = limit_row['Valeur seuils']
                
                etf_cat_data = df_etf_categories[df_etf_categories['Category'] == category]
                if not etf_cat_data.empty:
                    current_pct = etf_cat_data['% des ETF'].iloc[0]
                    if current_pct > seuil:
                        excess_pct = current_pct - seuil
                        excess_amount = (excess_pct / 100) * etf_total
                        alerts.append({
                            "type": "🟠 ETF SURPONDÉRÉ",
                            "message": f"**{category}** représente {current_pct:.1f}% des ETF (limite: {seuil}%)",
                            "severity": "warning"
                        })
                        urgent_actions.append(f"Réduire {category} ETF : {current_pct:.1f}% → ≤{seuil}% (Rééquilibrer ~{excess_amount:,.0f}€)")
    
    # Déséquilibres majeurs Types d'actifs
    if not limits.empty:
        df_type = df.groupby("Type")["Current value"].sum().reset_index()
        df_type["% portefeuille"] = df_type["Current value"] / total_value * 100
        
        exp_type = limits.query("Variable1=='Type'")[["Variable2", "Valeur seuils"]]
        exp_type.columns = ["Type", "Valeur seuils"]
        full_type = exp_type.merge(df_type, on="Type", how="left").fillna(0)
        
        for _, row in full_type.iterrows():
            ecart = row["% portefeuille"] - row["Valeur seuils"]
            if abs(ecart) > 15:
                severity = "🟠 ATTENTION" if abs(ecart) < 25 else "🔴 CRITIQUE"
                alerts.append({
                    "type": severity,
                    "message": f"**{row['Type']}** : {ecart:+.1f}% vs objectif ({row['% portefeuille']:.1f}% vs {row['Valeur seuils']:.1f}%)",
                    "severity": "warning" if abs(ecart) < 25 else "error"
                })
                
                amount_to_adjust = abs(ecart / 100) * total_value
                if ecart > 15:
                    urgent_actions.append(f"Réduire {row['Type']} : {row['% portefeuille']:.1f}% → {row['Valeur seuils']:.1f}% (Réduire ~{amount_to_adjust:,.0f}€)")
                elif ecart < -15:
                    urgent_actions.append(f"Renforcer {row['Type']} : {row['% portefeuille']:.1f}% → {row['Valeur seuils']:.1f}% (Ajouter ~{amount_to_adjust:,.0f}€)")
    
    # Affichage des alertes
    if alerts:
        for alert in alerts:
            if alert["severity"] == "error":
                st.error(f"{alert['type']} : {alert['message']}")
            else:
                st.warning(f"{alert['type']} : {alert['message']}")
    else:
        st.success("✅ Aucune alerte critique détectée - Portefeuille bien équilibré")

    # === 2) 🔴 ACTIONS URGENTES À RÉALISER ===
    st.markdown("---")
    st.markdown("### 🔴 Actions urgentes à réaliser")
    
    # Créer des actions simplifiées sans prix
    urgent_actions_simple = []
    if actions_total > 0 and 'overweight_companies' in locals():
        if not overweight_companies.empty:
            for _, company in overweight_companies.iterrows():
                urgent_actions_simple.append(f"Réduire {company['Entreprise']} : {company['% portefeuille total']:.1f}% → ≤10%")
    
    if not etf_only.empty and not limits.empty and 'df_etf_categories' in locals():
        etf_limits = limits.query("Variable1=='Category' and Variable2 in ['S&P500', 'Euro STOXX50', 'NASDAQ 100']")
        if not etf_limits.empty:
            for _, limit_row in etf_limits.iterrows():
                category = limit_row['Variable2']
                seuil = limit_row['Valeur seuils']
                etf_cat_data = df_etf_categories[df_etf_categories['Category'] == category]
                if not etf_cat_data.empty:
                    current_pct = etf_cat_data['% des ETF'].iloc[0]
                    if current_pct > seuil:
                        urgent_actions_simple.append(f"Réduire {category} ETF : {current_pct:.1f}% → ≤{seuil}%")
    
    if not limits.empty and 'full_type' in locals():
        for _, row in full_type.iterrows():
            ecart = row["% portefeuille"] - row["Valeur seuils"]
            if abs(ecart) > 15:
                if ecart > 15:
                    urgent_actions_simple.append(f"Réduire {row['Type']} : {row['% portefeuille']:.1f}% → {row['Valeur seuils']:.1f}%")
                elif ecart < -15:
                    urgent_actions_simple.append(f"Renforcer {row['Type']} : {row['% portefeuille']:.1f}% → {row['Valeur seuils']:.1f}%")
    
    if urgent_actions_simple:
        for i, action in enumerate(urgent_actions_simple, 1):
            st.error(f"**{i}.** {action}")
    else:
        st.success("🎉 Aucune action urgente nécessaire - Portefeuille équilibré")

    # === 3) 📊 ETF vs ACTIONS : GRAPHIQUE AMÉLIORÉ ===
    st.markdown("---")
    st.markdown("### 📊 ETF vs Actions : Répartition et objectifs")
    
    if actions_total > 0 and etf_total > 0:
        # Récupérer les objectifs depuis df_limits
        target_pcts = [50, 50]  # Valeurs par défaut
        if not limits.empty:
            type_limits = limits.query("Variable1=='Type'")
            for _, limit_row in type_limits.iterrows():
                type_name = limit_row['Variable2']
                target_pct = limit_row['Valeur seuils']
                if type_name == 'Actions':
                    target_pcts[0] = target_pct
                elif type_name == 'ETF':
                    target_pcts[1] = target_pct
        
        # Calculer les pourcentages actuels
        actions_pct = actions_total/total_value*100
        etf_pct = etf_total/total_value*100
        
        # Calculer les différences
        actions_diff = actions_pct - target_pcts[0]
        etf_diff = etf_pct - target_pcts[1]
        
        # Créer le graphique barplot cumulé
        fig_cumulative = go.Figure()
        
        # === BARRES ACTUELLES CUMULÉES ===
        # Actions (base)
        fig_cumulative.add_trace(go.Bar(
            name='Actions (Actuel)',
            x=['Répartition Actuelle'],
            y=[actions_pct],
            text=f'{actions_pct:.1f}%',
            textposition='inside',
            marker_color='#3b82f6',
            width=0.4,
            hovertemplate='<b>Actions</b><br>Actuel: %{y:.1f}%<extra></extra>'
        ))
        
        # ETF (empilé sur Actions)
        fig_cumulative.add_trace(go.Bar(
            name='ETF (Actuel)',
            x=['Répartition Actuelle'],
            y=[etf_pct],
            text=f'{etf_pct:.1f}%',
            textposition='inside',
            marker_color='#22c55e',
            width=0.4,
            hovertemplate='<b>ETF</b><br>Actuel: %{y:.1f}%<extra></extra>'
        ))
        
        # === BARRES OBJECTIFS CUMULÉES ===
        # Actions objectif (base)
        fig_cumulative.add_trace(go.Bar(
            name='Actions (Objectif)',
            x=['Objectif'],
            y=[target_pcts[0]],
            text=f'{target_pcts[0]:.1f}%',
            textposition='inside',
            marker_color='rgba(59, 130, 246, 0.5)',
            width=0.4,
            hovertemplate='<b>Actions Objectif</b><br>Cible: %{y:.1f}%<extra></extra>'
        ))
        
        # ETF objectif (empilé)
        fig_cumulative.add_trace(go.Bar(
            name='ETF (Objectif)',
            x=['Objectif'],
            y=[target_pcts[1]],
            text=f'{target_pcts[1]:.1f}%',
            textposition='inside',
            marker_color='rgba(34, 197, 94, 0.5)',
            width=0.4,
            hovertemplate='<b>ETF Objectif</b><br>Cible: %{y:.1f}%<extra></extra>'
        ))
        
        fig_cumulative.update_layout(
            title="📊 ETF vs Actions : Répartition Cumulée (Actuel vs Objectif) - Tout en EUR",
            yaxis_title="Pourcentage cumulé (%)",
            height=500,
            barmode='stack',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Ligne à 100%
        fig_cumulative.add_hline(
            y=100,
            line_dash="dot",
            line_color="gray",
            annotation_text="100%",
            annotation_position="right"
        )
        
        st.plotly_chart(fig_cumulative, use_container_width=True)
        
        # === TABLEAU DES DIFFÉRENCES ===
        st.markdown("#### 📋 Analyse des écarts")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**📊 Actions**")
            if abs(actions_diff) <= 5:
                st.success(f"✅ {actions_pct:.1f}% (Écart: {actions_diff:+.1f}%)")
            elif abs(actions_diff) <= 10:
                st.warning(f"⚠️ {actions_pct:.1f}% (Écart: {actions_diff:+.1f}%)")
            else:
                st.error(f"🚨 {actions_pct:.1f}% (Écart: {actions_diff:+.1f}%)")
        
        with col2:
            st.markdown("**📈 ETF**")
            if abs(etf_diff) <= 5:
                st.success(f"✅ {etf_pct:.1f}% (Écart: {etf_diff:+.1f}%)")
            elif abs(etf_diff) <= 10:
                st.warning(f"⚠️ {etf_pct:.1f}% (Écart: {etf_diff:+.1f}%)")
            else:
                st.error(f"🚨 {etf_pct:.1f}% (Écart: {etf_diff:+.1f}%)")
        
        with col3:
            st.markdown("**🎯 Action suggérée**")
            if abs(actions_diff) > 5:
                if actions_diff > 0:
                    st.write(f"📉 Réduire Actions de {abs(actions_diff):.1f}%")
                else:
                    st.write(f"📈 Augmenter Actions de {abs(actions_diff):.1f}%")
            elif abs(etf_diff) > 5:
                if etf_diff > 0:
                    st.write(f"📉 Réduire ETF de {abs(etf_diff):.1f}%")
                else:
                    st.write(f"📈 Augmenter ETF de {abs(etf_diff):.1f}%")
            else:
                st.success("✅ Équilibrage optimal")

    # === 5) CONCENTRATION PAR ENTREPRISE ===
    st.markdown("---")
    st.markdown("### 🏢 Concentration par entreprise")
    
    # Actions avec % sur portefeuille total
    if actions_total > 0:
        st.markdown("#### 📊 Actions (règle des 10% appliquée sur portefeuille total)")
        top_actions = df_companies_actions.nlargest(10, "% portefeuille total")
        
        fig_actions = px.bar(
            top_actions,
            x="% portefeuille total",
            y="Entreprise",
            orientation="h",
            color="% portefeuille total",
            color_continuous_scale=["green", "orange", "red"],
            text=top_actions["% portefeuille total"].round(1).astype(str) + "%",
            title="🎯 Top 10 des positions Actions (% du portefeuille total en EUR)"
        )
        
        # Ligne de seuil à 10% du portefeuille total
        fig_actions.add_vline(
            x=10, 
            line_dash="dash", 
            line_color="red",
            annotation_text="Seuil de risque (10% du portefeuille)",
            annotation_position="top"
        )
        
        fig_actions.update_layout(height=400, showlegend=False)
        fig_actions.update_traces(textposition='outside')
        st.plotly_chart(fig_actions, use_container_width=True)
    
    # ETF avec limites depuis df_limits
    if not etf_only.empty:
        st.markdown("#### 📊 ETF (avec limites par catégorie)")
        
        # S'assurer que df_etf_categories existe
        if 'df_etf_categories' not in locals():
            df_etf_categories = etf_only.groupby("Category")["Current value"].sum().reset_index()
            df_etf_categories["% des ETF"] = (df_etf_categories["Current value"] / etf_total * 100).round(2)
        
        fig_etf = px.bar(
            df_etf_categories,
            x="% des ETF",
            y="Category",
            orientation="h",
            color="% des ETF",
            color_continuous_scale=["lightblue", "blue", "darkblue"],
            text=df_etf_categories["% des ETF"].round(1).astype(str) + "%",
            title="📈 Répartition des ETF par catégorie (% des ETF en EUR)"
        )
        
        # Ajouter les lignes de seuil depuis df_limits
        if not limits.empty:
            etf_limits = limits.query("Variable1=='Category' and Variable2 in ['S&P500', 'Euro STOXX50', 'NASDAQ 100']")
            if not etf_limits.empty:
                for _, limit_row in etf_limits.iterrows():
                    seuil = limit_row['Valeur seuils']
                    category = limit_row['Variable2']
                    
                    # Vérifier si cette catégorie existe dans nos données
                    if category in df_etf_categories['Category'].values:
                        fig_etf.add_vline(
                            x=seuil, 
                            line_dash="dash", 
                            line_color="red",
                            line_width=2,
                            annotation_text=f"Limite {category}: {seuil}%",
                            annotation_position="top",
                            annotation_bgcolor="white",
                            annotation_bordercolor="red"
                        )
        
        fig_etf.update_layout(height=300, showlegend=False)
        fig_etf.update_traces(textposition='outside')
        st.plotly_chart(fig_etf, use_container_width=True)

    # === FONCTIONS D'ANALYSE DES ÉCARTS ===
    def analyse_ecarts_smart(df_full, label_col, value_col):
        conseils = []
        actions = []
        
        for _, row in df_full.iterrows():
            ecart = row[value_col] - row["Valeur seuils"]
            label = row[label_col]
            
            if ecart > 5:
                if ecart > 15:
                    conseils.append(f"🔴 **{label}** : TRÈS surpondéré (+{ecart:.1f}%)")
                    actions.append(f"💡 Réduire drastiquement {label}")
                else:
                    conseils.append(f"🟠 **{label}** : Surpondéré (+{ecart:.1f}%)")
                    actions.append(f"💡 Réduire légèrement {label}")
                    
            elif ecart < -5:
                if ecart < -15:
                    conseils.append(f"🔵 **{label}** : TRÈS sous-pondéré ({ecart:.1f}%)")
                    actions.append(f"💡 Renforcer significativement {label}")
                else:
                    conseils.append(f"🟡 **{label}** : Sous-pondéré ({ecart:.1f}%)")
                    actions.append(f"💡 Augmenter {label}")
            else:
                conseils.append(f"✅ **{label}** : Équilibré ({ecart:+.1f}%)")
                
        return conseils, actions

    def plot_ecart_enhanced(df_in, label, val, target, title):
        d = df_in.copy()
        d["Écart"] = (d[val] - d[target]).round(2)
        d = d.sort_values("Écart")
        
        # Couleurs selon la gravité
        colors = []
        for ecart in d["Écart"]:
            if ecart > 15:
                colors.append("#FF4444")  # Rouge foncé
            elif ecart > 5:
                colors.append("#FF8800")  # Orange
            elif ecart < -15:
                colors.append("#4444FF")  # Bleu foncé
            elif ecart < -5:
                colors.append("#FFAA00")  # Jaune
            else:
                colors.append("#00AA44")  # Vert
        
        fig = go.Figure(data=[
            go.Bar(
                x=d["Écart"],
                y=d[label],
                orientation='h',
                text=d["Écart"].round(1).astype(str) + "%",
                textposition='outside',
                marker_color=colors
            )
        ])
        
        # Zones de tolérance
        fig.add_vline(x=-5, line_dash="dot", line_color="gray", opacity=0.5)
        fig.add_vline(x=5, line_dash="dot", line_color="gray", opacity=0.5)
        fig.add_vline(x=0, line_color="black", line_width=2)
        
        fig.update_layout(
            title=title,
            xaxis_title="Écart vs objectif (%)",
            height=300,
            showlegend=False
        )
        
        return fig

    # === ANALYSE PAR TYPE D'ACTIF ===
    st.markdown("---")
    st.markdown("### 🎯 Analyse par type d'actif")
    
    if not limits.empty and 'full_type' in locals():
        conseils_type, actions_type = analyse_ecarts_smart(full_type, "Type", "% portefeuille")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.plotly_chart(
                plot_ecart_enhanced(full_type, "Type", "% portefeuille", "Valeur seuils", "📊 Écarts vs objectifs - Types d'actifs (EUR)"),
                use_container_width=True
            )
        
        with col2:
            st.markdown("**💡 Actions recommandées:**")
            for action in actions_type[:3]:  # Top 3 actions
                st.write(f"• {action}")

        with st.expander("📋 Analyse détaillée par type", expanded=False):
            for conseil in conseils_type:
                st.markdown(conseil)

    # === ANALYSE PAR SECTEUR ===
    st.markdown("### 🏭 Analyse par secteur")
    
    actions_df = df[df["Type"] == "Actions"].copy()
    if not actions_df.empty and not limits.empty:
        actions_total_sect = actions_df["Current value"].sum()
        df_sect = actions_df.groupby("Secteur")["Current value"].sum().reset_index()
        df_sect["% dans Actions"] = df_sect["Current value"] / actions_total_sect * 100

        exp_sect = limits.query("Variable1=='Secteur'")[["Variable2", "Valeur seuils"]]
        exp_sect.columns = ["Secteur", "Valeur seuils"]
        full_sect = exp_sect.merge(df_sect, on="Secteur", how="left").fillna(0)

        conseils_sect, actions_sect = analyse_ecarts_smart(full_sect, "Secteur", "% dans Actions")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.plotly_chart(
                plot_ecart_enhanced(full_sect, "Secteur", "% dans Actions", "Valeur seuils", "📊 Écarts vs objectifs - Secteurs (EUR)"),
                use_container_width=True
            )
        
        with col2:
            st.markdown("**💡 Actions recommandées:**")
            for action in actions_sect[:3]:
                st.write(f"• {action}")

        with st.expander("📋 Analyse détaillée par secteur", expanded=False):
            for conseil in conseils_sect:
                st.markdown(conseil)

    # === DONNÉES DÉTAILLÉES ===
    st.markdown("---")
    with st.expander("📊 Données détaillées du portefeuille (EUR)", expanded=False):
        if actions_total > 0 and 'df_companies_actions' in locals():
            st.markdown("**Répartition des Actions par entreprise (% portefeuille total en EUR):**")
            st.dataframe(
                df_companies_actions.sort_values("% portefeuille total", ascending=False).style.format({
                    "Current value": "{:,.0f} €",
                    "% portefeuille total": "{:.2f}%"
                }),
                use_container_width=True
            )
        
        if not etf_only.empty and 'df_etf_categories' in locals():
            st.markdown("**Répartition des ETF par catégorie (EUR):**")
            st.dataframe(
                df_etf_categories.sort_values("% des ETF", ascending=False).style.format({
                    "Current value": "{:,.0f} €",
                    "% des ETF": "{:.2f}%"
                }),
                use_container_width=True
            )
