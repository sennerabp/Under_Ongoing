import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
from modules.tab0_constants import save_to_excel 

def display_tab5_commentaires():
    st.markdown("📝 Commentaires et Actions associées", unsafe_allow_html=True)
    
    # CSS personnalisé pour élargir la zone de commentaire et centrer le contenu
    st.markdown("""
        <style>
        .comment-container {
            max-width: 900px;
            margin: auto;
            padding: 1.5rem 2rem;
            background-color: #fefefe;
            border-radius: 12px;
            border: 1px solid #ddd;
        }
        .stTextArea textarea {
            min-height: 200px !important;
            font-size: 1rem;
        }
        .stButton button {
            display: block;
            margin: 1rem auto;
        }
        </style>
    """, unsafe_allow_html=True)
    

    # 🚨 Guard clause si pas de fichier Excel chargé
    if "df_data" not in st.session_state or st.session_state.df_data.empty:
        st.info("💡 Aucun fichier Excel chargé. Veuillez importer votre fichier dans la barre latérale.")
        return

    # Prépare les commentaires existants
    if "df_comments" not in st.session_state:
        st.session_state.df_comments = pd.DataFrame(columns=[
            "Date", "Commentaire", "Date action", "Actions"
        ])
    df_comments = st.session_state.df_comments.copy()

    # --- Zone d'ajout de commentaire ---
    st.markdown("---")
    st.markdown("### ✍️ Ajouter un commentaire")
    comment_date = st.date_input("📅 Date", value=datetime.today().date(), key="comment_date")
    commentaire = st.text_area("💬 Commentaire", key="comment_text")

    if st.button("💾 Ajouter le commentaire", key="add_comment_btn"):
        if commentaire.strip():
            new_row = {
                "Date": pd.to_datetime(comment_date),
                "Commentaire": commentaire.strip(),
                "Date action": pd.NaT,
                "Actions": ""
            }
            
            # Ajouter au session_state
            st.session_state.df_comments = pd.concat(
                [st.session_state.df_comments, pd.DataFrame([new_row])],
                ignore_index=True
            )
            
            # Marquer comme modifié
            st.session_state.data_modified = True
            
            # Sauvegarder immédiatement
            try:
                success = save_to_excel()
                if success:
                    st.success("✅ Commentaire ajouté et fichier Excel mis à jour.")
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la sauvegarde du commentaire")
            except Exception as e:
                st.error(f"❌ Erreur lors de l'ajout du commentaire : {e}")
        else:
            st.warning("Merci d'écrire un commentaire avant de soumettre.")

    # --- Historique des commentaires et actions associées ---
    if not st.session_state.df_comments.empty:
        st.markdown("---")
        st.subheader("📜 Historique et réponses")
        for idx, row in st.session_state.df_comments.sort_values("Date", ascending=False).iterrows():
            with st.expander(f"🗓️ {row['Date'].date()} — {row['Commentaire']}"):
                # Saisie de la date d'action
                action_date = st.date_input(
                    "📆 Date de l'action",
                    value=row["Date action"] if pd.notnull(row["Date action"]) else datetime.today().date(),
                    key=f"action_date_{idx}"
                )
                # Saisie du texte de l'action
                action_text = st.text_area(
                    "🛠️ Action réalisée",
                    value=row["Actions"],
                    key=f"action_text_{idx}"
                )
                if st.button("✔️ Enregistrer l'action", key=f"save_action_{idx}"):
                    # Mettre à jour le session state
                    st.session_state.df_comments.at[idx, "Date action"] = pd.to_datetime(action_date)
                    st.session_state.df_comments.at[idx, "Actions"] = action_text
                    
                    # Marquer comme modifié
                    st.session_state.data_modified = True
                    
                    # Sauvegarder
                    try:
                        success = save_to_excel()
                        if success:
                            st.success("✅ Action enregistrée et fichier Excel mis à jour.")
                            st.rerun()
                        else:
                            st.error("❌ Erreur lors de la sauvegarde de l'action")
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'enregistrement : {e}")
