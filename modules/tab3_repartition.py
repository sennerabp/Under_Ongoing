import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
import plotly.express as px
from modules.tab0_constants import SECTEUR_PAR_TYPE, CATEGORY_LIST, SECTOR_COLORS

def add_eur_columns_tab3(df):
    """
    🔥 Ajouter les colonnes EUR converties pour tab3
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

def display_tab3_repartition():
    st.header("📊 Répartition actuelle du portefeuille")

    # 🚨 Guard clause si pas de fichier Excel chargé
    if "df_data" not in st.session_state or st.session_state.df_data.empty:
        st.info("💡 Aucun fichier Excel chargé. Veuillez importer votre fichier dans la barre latérale.")
        return

    # 🔧 Nom de fichier propre
    input_path = st.session_state.get("input_file_path", "")
    if input_path:
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        base_name = re.sub(r"_\d{8}$", "", base_name)
        today_str = datetime.today().strftime("%Y%m%d")
        output_name = f"{base_name}_{today_str}.xlsx"
    else:
        base_name = "export"
        output_name = f"{base_name}_{datetime.today().strftime('%Y%m%d')}.xlsx"

    if "df_data" in st.session_state and not st.session_state.df_data.empty:
        df = st.session_state.df_data.copy()
        df.columns = df.columns.str.strip()

        if "Current value" not in df.columns:
            st.warning("⚠️ Veuillez d'abord exécuter l'onglet Tab1 pour récupérer les valeurs actuelles.")
            return

        if df["Current value"].isna().all():
            st.warning("⚠️ Aucune valeur actuelle disponible. Exécutez Tab1 pour mettre à jour les cours.")
            return

        # 🔥 AJOUTER LES COLONNES EUR CONVERTIES
        df = add_eur_columns_tab3(df)

        # 🔥 UTILISER Current_value_EUR pour les calculs !
        grouped = df.groupby(
            ["Type", "Secteur", "Category", "Entreprise"],
            as_index=False
        )["Current_value_EUR"].sum()
        
        # Renommer pour compatibilité avec le reste du code
        grouped.rename(columns={"Current_value_EUR": "Current value"}, inplace=True)
        
        total = grouped["Current value"].sum()
        grouped["Pourcentage"] = (grouped["Current value"] / total * 100).round(2)
        grouped["Source"] = "Portefeuille"

        # Affichage de la répartition actuelle
        st.subheader("📈 Répartition actuelle du portefeuille")
        
        # Sunburst principal
        fig1 = px.sunburst(
            grouped,
            path=["Type", "Secteur", "Category", "Entreprise"],
            values="Current value",
            color="Secteur",
            color_discrete_map=SECTOR_COLORS,
            custom_data=["Current value", "Pourcentage"],
            title="Répartition par Type ➔ Secteur ➔ Catégorie ➔ Entreprise (Tout en EUR)"
        )
        fig1.update_traces(
            insidetextorientation='radial',
            textinfo="label+percent entry",
            hovertemplate="<b>%{label}</b><br>%{customdata[0]:,.0f} €<br>%{customdata[1]}%<extra></extra>"
        )
        fig1.update_layout(height=800)
        st.plotly_chart(fig1, use_container_width=True)

        # --- SECTION SIMULATION ---
        st.markdown("---")
        st.subheader("🔬 Simulateur d'investissement")
        
        # Initialisation des inputs de simulation
        if "sim_inputs" not in st.session_state:
            st.session_state.sim_inputs = {}

        # Interface de saisie des simulations en colonnes
        st.markdown("##### ➕ Ajout de nouvelles positions")
        
        # Colonnes pour les champs de saisie
        col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 1.5, 1.5, 1])
        
        with col1:
            type_sim = st.selectbox(
                "Type d'actif",
                list(SECTEUR_PAR_TYPE.keys()),
                key="sim_type_input"
            )
        
        with col2:
            secteur_sim = st.selectbox(
                "Secteur",
                SECTEUR_PAR_TYPE[type_sim],
                key="sim_secteur_input"
            )
        
        with col3:
            categorie_sim = st.selectbox(
                "Catégorie",
                CATEGORY_LIST.get(secteur_sim, []),
                key="sim_categorie_input"
            )
        
        with col4:
            # 🔥 NOUVELLE COLONNE DEVISE
            devise_sim = st.selectbox(
                "Devise",
                ["EUR", "USD"],
                key="sim_devise_input"
            )
        
        with col5:
            montant_sim = st.number_input(
                f"Montant ({devise_sim})",
                min_value=0.0,
                step=100.0,
                key="sim_montant_input",
                format="%.0f"
            )
        
        with col6:
            st.markdown("<br>", unsafe_allow_html=True)  # Espacement pour aligner le bouton
            if st.button("➕ Ajouter", key="add_simulation", type="primary"):
                if montant_sim > 0:
                    # 🔥 CONVERSION USD → EUR si nécessaire
                    from modules.yfinance_cache_manager import get_cache_manager
                    
                    montant_eur = montant_sim
                    if devise_sim == "USD":
                        cache_manager = get_cache_manager()
                        eurusd_rate = cache_manager.get_eurusd_rate()
                        montant_eur = montant_sim * eurusd_rate
                        st.info(f"💱 Conversion: {montant_sim:,.0f} USD → {montant_eur:,.0f} EUR (taux: {eurusd_rate:.4f})")
                    
                    # Créer une clé unique pour cette simulation
                    sim_key = f"{type_sim}_{secteur_sim}_{categorie_sim}_{devise_sim}"
                    if sim_key in st.session_state.sim_inputs:
                        st.session_state.sim_inputs[sim_key]["montant_eur"] += montant_eur
                        st.session_state.sim_inputs[sim_key]["montant_original"] += montant_sim
                    else:
                        st.session_state.sim_inputs[sim_key] = {
                            "Type": type_sim,
                            "Secteur": secteur_sim,
                            "Category": categorie_sim,
                            "devise": devise_sim,
                            "montant_original": montant_sim,
                            "montant_eur": montant_eur  # 🔥 TOUJOURS stocker en EUR !
                        }
                    st.rerun()
                else:
                    st.warning("Veuillez saisir un montant supérieur à 0")

        # Affichage des simulations ajoutées
        if st.session_state.sim_inputs:
            st.markdown("##### 📋 Simulations ajoutées")
            
            # Bouton reset
            col_reset, col_empty = st.columns([1, 4])
            with col_reset:
                if st.button("🔄 Tout effacer", key="reset_all_sims"):
                    st.session_state.sim_inputs = {}
                    st.rerun()
            
            # Affichage des simulations sous forme de liste
            for sim_key, sim_data in st.session_state.sim_inputs.items():
                col_info, col_montant, col_eur, col_delete = st.columns([3, 1, 1, 0.5])
                with col_info:
                    st.write(f"**{sim_data['Type']}** → {sim_data['Secteur']} → {sim_data['Category']}")
                with col_montant:
                    st.write(f"{sim_data['montant_original']:,.0f} {sim_data['devise']}")
                with col_eur:
                    if sim_data['devise'] == 'USD':
                        st.write(f"≈ {sim_data['montant_eur']:,.0f} €")
                    else:
                        st.write(f"{sim_data['montant_eur']:,.0f} €")
                with col_delete:
                    if st.button("🗑️", key=f"delete_{sim_key}"):
                        del st.session_state.sim_inputs[sim_key]
                        st.rerun()
            
            # Préparation des données pour la simulation
            simulations_valides = []
            total_simulation = 0
            for i, (sim_key, sim_data) in enumerate(st.session_state.sim_inputs.items()):
                simulations_valides.append({
                    "Type": sim_data["Type"],
                    "Secteur": sim_data["Secteur"],
                    "Category": sim_data["Category"],
                    "Entreprise": f"⭐ Simulation {i+1}",
                    "Current value": sim_data["montant_eur"],  # 🔥 UTILISER montant_eur !
                    "Source": "Simulation"
                })
                total_simulation += sim_data["montant_eur"]  # 🔥 SOMMER en EUR !
            
            # Affichage du total
            st.success(f"💰 **Total des simulations**: {total_simulation:,.0f} €")

            # COMPARAISON AVANT/APRÈS SIMULATION
            st.markdown("---")
            st.markdown("### 📊 Comparaison AVANT / APRÈS simulation")
            
            # Préparer les données combinées
            df_combined = pd.concat([
                grouped,
                pd.DataFrame(simulations_valides)
            ], ignore_index=True)
            
            total_combined = df_combined["Current value"].sum()
            df_combined["Pourcentage"] = (df_combined["Current value"] / total_combined * 100).round(2)

            # Layout en deux colonnes pour AVANT/APRÈS
            col_avant, col_apres = st.columns(2)
            
            with col_avant:
                st.markdown("#### 📈 AVANT Simulation")
                st.markdown(f"**Total**: {total:,.0f} €")
                
                fig_avant = px.sunburst(
                    grouped,
                    path=["Type", "Secteur", "Category", "Entreprise"],
                    values="Current value",
                    color="Secteur",
                    color_discrete_map=SECTOR_COLORS,
                    custom_data=["Current value", "Pourcentage"],
                    title=""
                )
                fig_avant.update_traces(
                    insidetextorientation='radial',
                    textinfo="label+percent entry",
                    hovertemplate="<b>%{label}</b><br>%{customdata[0]:,.0f} €<br>%{customdata[1]}%<extra></extra>"
                )
                fig_avant.update_layout(height=600, showlegend=False)
                st.plotly_chart(fig_avant, use_container_width=True)
            
            with col_apres:
                st.markdown("#### 🚀 APRÈS Simulation")
                st.markdown(f"**Total**: {total_combined:,.0f} € (+{total_simulation:,.0f} €)")
                
                fig_apres = px.sunburst(
                    df_combined,
                    path=["Type", "Secteur", "Category", "Entreprise"],
                    values="Current value",
                    color="Secteur",
                    color_discrete_map=SECTOR_COLORS,
                    custom_data=["Current value", "Pourcentage", "Source"],
                    title=""
                )
                fig_apres.update_traces(
                    insidetextorientation='radial',
                    textinfo="label+percent entry",
                    hovertemplate="<b>%{label}</b><br>%{customdata[0]:,.0f} €<br>%{customdata[1]}%<br><i>%{customdata[2]}</i><extra></extra>"
                )
                fig_apres.update_layout(height=600, showlegend=False)
                st.plotly_chart(fig_apres, use_container_width=True)

            # TABLEAU RÉSUMÉ JUSTE EN DESSOUS
            st.markdown("#### 📋 Tableau de comparaison détaillé")
            
            # Calculer les répartitions par secteur
            repartition_avant = grouped.groupby("Secteur").agg({
                "Current value": "sum",
                "Pourcentage": "sum"
            }).round(2)
            
            repartition_apres = df_combined.groupby("Secteur").agg({
                "Current value": "sum", 
                "Pourcentage": "sum"
            }).round(2)
            
            # Créer le tableau de comparaison
            all_secteurs = set(repartition_avant.index) | set(repartition_apres.index)
            comparison_data = []
            
            for secteur in sorted(all_secteurs):
                avant_val = repartition_avant.loc[secteur, "Current value"] if secteur in repartition_avant.index else 0
                avant_pct = repartition_avant.loc[secteur, "Pourcentage"] if secteur in repartition_avant.index else 0
                apres_val = repartition_apres.loc[secteur, "Current value"] if secteur in repartition_apres.index else 0
                apres_pct = repartition_apres.loc[secteur, "Pourcentage"] if secteur in repartition_apres.index else 0
                
                comparison_data.append({
                    "Secteur": secteur,
                    "Avant - Montant (€)": avant_val,
                    "Avant - % ": avant_pct,
                    "Après - Montant (€)": apres_val,
                    "Après - %": apres_pct,
                    "Différence (€)": apres_val - avant_val,
                    "Différence (%)": apres_pct - avant_pct
                })
            
            df_comparison = pd.DataFrame(comparison_data)
            
            # Styling du tableau avec formatage
            def highlight_changes(row):
                styles = [''] * len(row)
                if row['Différence (€)'] > 0:
                    styles[-2] = 'background-color: lightgreen'  # Différence €
                    styles[-1] = 'background-color: lightgreen'  # Différence %
                elif row['Différence (€)'] < 0:
                    styles[-2] = 'background-color: lightcoral'
                    styles[-1] = 'background-color: lightcoral'
                return styles
            
            styled_df = df_comparison.style.format({
                "Avant - Montant (€)": "{:,.0f}",
                "Avant - % ": "{:.2f}%",
                "Après - Montant (€)": "{:,.0f}",
                "Après - %": "{:.2f}%",
                "Différence (€)": "{:+,.0f}",
                "Différence (%)": "{:+.2f}%"
            }).apply(highlight_changes, axis=1)
            
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

    else:
        st.info("💡 Veuillez charger un fichier Excel via la sidebar.")
