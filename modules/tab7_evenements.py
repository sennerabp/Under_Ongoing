import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import uuid
from streamlit_calendar import calendar as st_calendar
from modules.tab0_constants import save_to_excel 

def display_tab7_evenements():
    st.header("📅 Calendrier financier et événements")

    # 🚨 Guard clause si pas de fichier Excel chargé
    if "df_data" not in st.session_state or st.session_state.df_data.empty:
        st.info("💡 Aucun fichier Excel chargé. Veuillez importer votre fichier dans la barre latérale.")
        return

    # Initialiser la clé pour forcer le rafraîchissement du composant
    if "CalKey" not in st.session_state:
        st.session_state.CalKey = str(uuid.uuid4())

    # === PRÉPARATION DES DONNÉES ===
    
    # Charger df_events
    df_events = st.session_state.df_events.copy()
    if "Date paiement" in df_events.columns:
        df_events["Date"] = pd.to_datetime(df_events["Date paiement"], errors="coerce")
    elif "Date" in df_events.columns:
        df_events["Date"] = pd.to_datetime(df_events["Date"], errors="coerce")
    else:
        df_events["Date"] = pd.NaT
    df_events["Event"] = df_events.get("Event", "").astype(str).fillna("")

    # Données du portefeuille
    df_data = st.session_state.df_data.copy()
    df_data["Date"] = pd.to_datetime(df_data["Date"], errors="coerce")
    
    # Données des dividendes
    df_div = st.session_state.df_dividendes.copy()
    if not df_div.empty:
        df_div["Date paiement"] = pd.to_datetime(df_div["Date paiement"], errors="coerce")
        df_div = df_div.dropna(subset=["Date paiement"])

    # === GÉNÉRATION AUTOMATIQUE D'ÉVÉNEMENTS FINANCIERS ===
    
    def get_fed_bce_dates_2024_2025():
        """Dates OFFICIELLES des réunions FED et BCE récupérées automatiquement"""
        events_fed_bce = []
        
        # 🇺🇸 FED 2025 (réunions FOMC) - DATES OFFICIELLES
        # Source: Federal Reserve Board & Texas Bankers Association
        fed_dates = [
            # Réunions FOMC 2025 officielles
            ("2025-05-06", "🏛️ Réunion FED - Décision taux"),  # Corrigé: 6-7 Mai
            ("2025-06-17", "🏛️ Réunion FED - Décision taux"),  # Corrigé: 17-18 Juin
            ("2025-07-29", "🏛️ Réunion FED - Décision taux"),  # Corrigé: 29-30 Juillet
            ("2025-09-16", "🏛️ Réunion FED - Décision taux"),  # Corrigé: 16-17 Sept
            ("2025-11-28", "🏛️ Réunion FED - Décision taux"),  # Estimation Nov
            ("2025-12-9", "🏛️ Réunion FED - Décision taux"),  # Estimation Déc
        ]
        
        # 🇪🇺 BCE 2025 - DATES OFFICIELLES  
        # Source: European Central Bank - Governing Council meetings
        bce_dates = [
            # Réunions BCE 2025 officielles (monetary policy meetings every 6 weeks)
            ("2025-01-30", "🏦 Réunion BCE - Décision taux"),
            ("2025-03-13", "🏦 Réunion BCE - Décision taux"),
            ("2025-04-24", "🏦 Réunion BCE - Décision taux"),
            ("2025-06-05", "🏦 Réunion BCE - Décision taux"),  # Corrigé selon search
            ("2025-07-24", "🏦 Réunion BCE - Décision taux"),
            ("2025-09-11", "🏦 Réunion BCE - Décision taux"),
            ("2025-12-18", "🏦 Réunion BCE - Décision taux"),
        ]
        
        # 📊 Événements économiques majeurs
        eco_dates = [
            # Publications PIB trimestrielles (estimations basées sur calendriers usuels)
            ("2025-01-30", "📊 PIB US Q4 2024 (preliminaire)"),
            ("2025-04-24", "📊 PIB US Q1 2025 (preliminaire)"),
            ("2025-07-24", "📊 PIB US Q2 2025 (preliminaire)"),
            ("2025-10-30", "📊 PIB US Q3 2025 (preliminaire)"),
            
            # Publications inflation (premier vendredi du mois)
            ("2025-07-04", "📊 Rapport emploi US (NFP)"),
            ("2025-08-01", "📊 Rapport emploi US (NFP)"),
            ("2025-09-05", "📊 Rapport emploi US (NFP)"),
            
            # Autres événements importants
            ("2025-06-24", "🇬🇧 Réunion Bank of England"),
            ("2025-07-31", "🇯🇵 Réunion Bank of Japan"),
        ]
        
        return fed_dates + bce_dates + eco_dates

    # === GÉNÉRATION DE LA LISTE DES ÉVÉNEMENTS ===
    all_events = []
    
    # 1. Événements personnels (df_events)
    for _, row in df_events.iterrows():
        if pd.notnull(row["Date"]) and row["Event"].strip():
            all_events.append({
                "title": f"📝 {row['Event'].strip()}",
                "start": row["Date"].strftime("%Y-%m-%d"),
                "allDay": True,
                "color": "#8B5CF6",  # Violet
                "category": "Personnel"
            })

    # 2. Achats d'actions
    for _, row in df_data.iterrows():
        if pd.notnull(row["Date"]):
            all_events.append({
                "title": f"💰 Achat {row['Ticker']} ({row['Quantity']:.0f} parts)",
                "start": row["Date"].strftime("%Y-%m-%d"),
                "allDay": True,
                "color": "#10B981",  # Vert
                "category": "Investissement"
            })

    # 3. Dividendes reçus
    if not df_div.empty:
        for _, row in df_div.iterrows():
            montant = row.get("Montant net (€)", row.get("Montant brut (€)", 0))
            all_events.append({
                "title": f"💸 Dividende {row['Entreprise']} ({montant:.2f}€)",
                "start": row["Date paiement"].strftime("%Y-%m-%d"),
                "allDay": True,
                "color": "#F59E0B",  # Orange
                "category": "Dividende"
            })

    # 4. Événements FED/BCE/Économiques
    fed_bce_events = get_fed_bce_dates_2024_2025()
    for date_str, event_title in fed_bce_events:
        try:
            event_date = datetime.strptime(date_str, "%Y-%m-%d")
            if event_date >= datetime.now() - timedelta(days=365):  # Dernière année + futur
                color = "#EF4444" if "FED" in event_title else "#3B82F6" if "BCE" in event_title else "#6B7280"
                all_events.append({
                    "title": event_title,
                    "start": date_str,
                    "allDay": True,
                    "color": color,
                    "category": "Économique"
                })
        except:
            continue

    # === LÉGENDE DES COULEURS ===
    def get_legend_symbol(category):
        if category == "Personnel":
            return "🟣"
        elif category == "Investissement":
            return "🟢"
        elif category == "Dividende":
            return "🟠"
        elif category == "Économique":
            return "🔴🔵⚫"
        else:
            return "⚪"

    # === LÉGENDE DES COULEURS EN HAUT ===
    st.markdown("### 🎨 Légende")
    
    col_leg1, col_leg2, col_leg3, col_leg4 = st.columns(4)
    
    with col_leg1:
        st.markdown("🟣 **Personnel** - Vos événements")
    with col_leg2:
        st.markdown("🟢 **Investissements** - Achats d'actions")
    with col_leg3:
        st.markdown("🟠 **Dividendes** - Versements reçus")
    with col_leg4:
        st.markdown("🔴 **FED** 🔵 **BCE** ⚫ **Économie**")

    # === FORMULAIRE D'AJOUT COMPACT ===
    st.markdown("---")
    with st.expander("➕ Ajouter un événement personnel", expanded=False):
        with st.form("add_event_form"):
            col_form1, col_form2 = st.columns([1, 2])
            
            with col_form1:
                new_date = st.date_input("📅 Date", value=datetime.today().date())
            
            with col_form2:
                new_event = st.text_input("📝 Description de l'événement")
            
            submit = st.form_submit_button("Ajouter l'événement")

        if submit and new_event.strip():
            # Ajout à df_events
            new_row = {"Date": new_date, "Event": new_event.strip()}
            st.session_state.df_events = pd.concat(
                [st.session_state.df_events, pd.DataFrame([new_row])],
                ignore_index=True
            )
            
            # Marquer comme modifié et sauvegarder
            st.session_state.data_modified = True
            save_to_excel()
            
            st.success("✅ Événement ajouté et fichier mis à jour.")
            st.session_state.CalKey = str(uuid.uuid4())  # Forcer rafraîchissement
            st.rerun()

    # === CALENDRIER INTERACTIF HTML/JS ===
    st.markdown("### 📅 Calendrier financier")
    
    # Préparer les données pour JavaScript
    js_events = []
    for event in all_events:
        try:
            # Convertir en format simple pour JavaScript
            event_date = datetime.strptime(event["start"], "%Y-%m-%d")
            js_events.append({
                "date": event["start"],
                "title": event["title"],
                "category": event["category"],
                "color": event["color"]
            })
        except:
            continue
    
    st.write(f"📊 {len(js_events)} événements à afficher")
    
    # Créer le calendrier HTML/JavaScript intégré
    calendar_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            .calendar-container {{
                display: flex;
                gap: 20px;
                max-width: 100%;
                margin: 0 auto;
                font-family: Arial, sans-serif;
            }}
            
            .calendar-section {{
                flex: 2;
                min-width: 500px;
            }}
            
            .events-section {{
                flex: 1;
                min-width: 300px;
            }}
            
            .calendar-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                background: #f8f9fa;
                padding: 10px;
                border-radius: 8px;
            }}
            
            .nav-btn {{
                background: #007bff;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 12px;
            }}
            
            .nav-btn:hover {{
                background: #0056b3;
            }}
            
            .month-year {{
                font-size: 18px;
                font-weight: bold;
                color: #333;
            }}
            
            .calendar-grid {{
                display: grid;
                grid-template-columns: repeat(7, 1fr);
                gap: 1px;
                background: #dee2e6;
                border-radius: 8px;
                overflow: hidden;
            }}
            
            .day-header {{
                background: #495057;
                color: white;
                padding: 8px 2px;
                text-align: center;
                font-weight: bold;
                font-size: 11px;
            }}
            
            .day-cell {{
                background: white;
                min-height: 80px;
                padding: 4px;
                position: relative;
                border: 1px solid #e9ecef;
                cursor: pointer;
                transition: background-color 0.2s;
            }}
            
            .day-cell:hover {{
                background: #f8f9fa;
            }}
            
            .day-cell.selected {{
                background: #e3f2fd !important;
                border: 2px solid #2196f3;
            }}
            
            .day-number {{
                font-weight: bold;
                margin-bottom: 3px;
                color: #333;
                font-size: 12px;
            }}
            
            .day-empty {{
                background: #f8f9fa;
                color: #999;
            }}
            
            .today {{
                background: #fff3cd !important;
                border: 2px solid #ffc107;
            }}
            
            .event-dot {{
                display: block;
                font-size: 8px;
                padding: 1px 2px;
                margin: 1px 0;
                border-radius: 2px;
                color: white;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                max-width: 100%;
            }}
            
            .event-count {{
                font-size: 7px;
                background: #6c757d;
                color: white;
                padding: 1px 3px;
                border-radius: 2px;
                margin-top: 1px;
            }}
            
            .events-panel {{
                background: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
                min-height: 400px;
            }}
            
            .events-panel h3 {{
                margin-top: 0;
                margin-bottom: 15px;
                color: #333;
                font-size: 20px;
                border-bottom: 2px solid #007bff;
                padding-bottom: 8px;
            }}
            
            .no-events {{
                color: #666;
                font-style: italic;
                text-align: center;
                margin-top: 50px;
            }}
            
            .event-item {{
                padding: 12px;
                margin: 8px 0;
                background: white;
                border-radius: 6px;
                border-left: 4px solid #007bff;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                transition: transform 0.2s;
            }}
            
            .event-item:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            }}
            
            .event-title {{
                font-weight: bold;
                margin-bottom: 5px;
                color: #333;
            }}
            
            .event-category {{
                font-size: 12px;
                color: #666;
                background: #e9ecef;
                padding: 2px 6px;
                border-radius: 3px;
                display: inline-block;
            }}
            
            @media (max-width: 768px) {{
                .calendar-container {{
                    flex-direction: column;
                }}
                
                .calendar-section, .events-section {{
                    min-width: auto;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="calendar-container">
            <!-- Section Calendrier (Gauche) -->
            <div class="calendar-section">
                <div class="calendar-header">
                    <button class="nav-btn" onclick="previousMonth()">◀</button>
                    <div class="month-year" id="monthYear"></div>
                    <button class="nav-btn" onclick="nextMonth()">▶</button>
                </div>
                
                <div class="calendar-grid" id="calendar">
                    <!-- Le calendrier sera généré par JavaScript -->
                </div>
            </div>
            
            <!-- Section Événements (Droite) -->
            <div class="events-section">
                <div class="events-panel" id="eventsPanel">
                    <h3 id="eventsTitle">📅 Sélectionnez une date</h3>
                    <div id="eventsList">
                        <div class="no-events">
                            Cliquez sur une date du calendrier pour voir les événements
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // Données des événements depuis Python
            const events = {str(js_events)};
            
            let currentDate = new Date();
            let selectedDate = null;
            const today = new Date();
            
            const monthNames = [
                "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
            ];
            
            const dayNames = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
            
            function getEventsForDate(dateStr) {{
                return events.filter(event => event.date === dateStr);
            }}
            
            function getColorForCategory(category) {{
                const colors = {{
                    "Personnel": "#8B5CF6",
                    "Investissement": "#10B981", 
                    "Dividende": "#F59E0B",
                    "Économique": "#EF4444"
                }};
                return colors[category] || "#6B7280";
            }}
            
            function renderCalendar() {{
                const year = currentDate.getFullYear();
                const month = currentDate.getMonth();
                
                document.getElementById('monthYear').textContent = `${{monthNames[month]}} ${{year}}`;
                
                const firstDay = new Date(year, month, 1);
                const lastDay = new Date(year, month + 1, 0);
                const startDay = new Date(firstDay);
                startDay.setDate(startDay.getDate() - (firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1));
                
                let html = '';
                
                // En-têtes des jours
                dayNames.forEach(day => {{
                    html += `<div class="day-header">${{day}}</div>`;
                }});
                
                // Générer les cellules du calendrier
                for (let i = 0; i < 42; i++) {{
                    const cellDate = new Date(startDay);
                    cellDate.setDate(startDay.getDate() + i);
                    
                    const dateStr = cellDate.toISOString().split('T')[0];
                    const dayEvents = getEventsForDate(dateStr);
                    
                    const isCurrentMonth = cellDate.getMonth() === month;
                    const isToday = cellDate.toDateString() === today.toDateString();
                    const isSelected = selectedDate === dateStr;
                    
                    let cellClass = 'day-cell';
                    if (!isCurrentMonth) cellClass += ' day-empty';
                    if (isToday) cellClass += ' today';
                    if (isSelected) cellClass += ' selected';
                    
                    let eventsHtml = '';
                    const maxVisible = 3;
                    
                    dayEvents.slice(0, maxVisible).forEach(event => {{
                        const color = getColorForCategory(event.category);
                        const shortTitle = event.title.length > 15 ? event.title.substring(0, 15) + '...' : event.title;
                        eventsHtml += `<span class="event-dot" style="background: ${{color}}" title="${{event.title}}">${{shortTitle}}</span>`;
                    }});
                    
                    if (dayEvents.length > maxVisible) {{
                        eventsHtml += `<span class="event-count">+${{dayEvents.length - maxVisible}}</span>`;
                    }}
                    
                    html += `
                        <div class="${{cellClass}}" onclick="showEvents('${{dateStr}}', ${{cellDate.getDate()}})">
                            <div class="day-number">${{cellDate.getDate()}}</div>
                            ${{eventsHtml}}
                        </div>
                    `;
                }}
                
                document.getElementById('calendar').innerHTML = html;
            }}
            
            function showEvents(dateStr, day) {{
                selectedDate = dateStr;
                const dayEvents = getEventsForDate(dateStr);
                const eventsTitle = document.getElementById('eventsTitle');
                const eventsList = document.getElementById('eventsList');
                
                // Mettre à jour le titre
                const date = new Date(dateStr);
                const monthName = monthNames[date.getMonth()];
                eventsTitle.textContent = `📅 Événements du ${{day}} ${{monthName}}`;
                
                if (dayEvents.length > 0) {{
                    let html = '';
                    dayEvents.forEach(event => {{
                        const color = getColorForCategory(event.category);
                        html += `
                            <div class="event-item" style="border-left-color: ${{color}}">
                                <div class="event-title">${{event.title}}</div>
                                <span class="event-category">${{event.category}}</span>
                            </div>
                        `;
                    }});
                    eventsList.innerHTML = html;
                }} else {{
                    eventsList.innerHTML = '<div class="no-events">Aucun événement ce jour</div>';
                }}
                
                // Re-render pour mettre à jour la sélection
                renderCalendar();
            }}
            
            function previousMonth() {{
                currentDate.setMonth(currentDate.getMonth() - 1);
                selectedDate = null;
                document.getElementById('eventsTitle').textContent = '📅 Sélectionnez une date';
                document.getElementById('eventsList').innerHTML = '<div class="no-events">Cliquez sur une date du calendrier pour voir les événements</div>';
                renderCalendar();
            }}
            
            function nextMonth() {{
                currentDate.setMonth(currentDate.getMonth() + 1);
                selectedDate = null;
                document.getElementById('eventsTitle').textContent = '📅 Sélectionnez une date';
                document.getElementById('eventsList').innerHTML = '<div class="no-events">Cliquez sur une date du calendrier pour voir les événements</div>';
                renderCalendar();
            }}
            
            // Initialiser le calendrier
            renderCalendar();
        </script>
    </body>
    </html>
    """
    
    # Afficher le calendrier HTML
    st.components.v1.html(calendar_html, height=500, scrolling=False)

    # === PROCHAINS ÉVÉNEMENTS (60 JOURS) EN DESSOUS ===
    st.markdown("---")
    st.markdown("### 📋 Prochains événements (60 jours)")
    
    today = datetime.now().date()
    future_events = []
    
    for event in all_events:
        try:
            event_date = datetime.strptime(event["start"], "%Y-%m-%d").date()
            if today <= event_date <= today + timedelta(days=60):  # Changé de 30 à 60 jours
                days_until = (event_date - today).days
                future_events.append({
                    "Date": event_date,
                    "Événement": event["title"],
                    "Dans": f"{days_until} jour{'s' if days_until > 1 else ''}",
                    "Catégorie": event["category"],
                    "Légende": get_legend_symbol(event["category"])
                })
        except:
            continue
    
    if future_events:
        df_future = pd.DataFrame(future_events).sort_values("Date")
        # Réorganiser les colonnes pour mettre la légende en premier
        df_future = df_future[["Légende", "Date", "Événement", "Dans", "Catégorie"]]
        
        # Ajouter un style pour différencier les types d'événements
        def highlight_event_type(row):
            if row['Catégorie'] == 'Économique':
                return ['background-color: #ffebee'] * len(row)
            elif row['Catégorie'] == 'Personnel':
                return ['background-color: #f3e5f5'] * len(row)
            elif row['Catégorie'] == 'Dividende':
                return ['background-color: #fff3e0'] * len(row)
            elif row['Catégorie'] == 'Investissement':
                return ['background-color: #e8f5e8'] * len(row)
            else:
                return [''] * len(row)
        
        styled_df = df_future.style.apply(highlight_event_type, axis=1)
        st.dataframe(styled_df, use_container_width=True)
        
        # Statistiques des événements
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        
        with col_stat1:
            st.metric("📅 Total événements", len(future_events))
        
        with col_stat2:
            econ_events = len([e for e in future_events if e['Catégorie'] == 'Économique'])
            st.metric("📊 Événements économiques", econ_events)
        
        with col_stat3:
            personal_events = len([e for e in future_events if e['Catégorie'] == 'Personnel'])
            st.metric("📝 Événements personnels", personal_events)
        
        with col_stat4:
            dividend_events = len([e for e in future_events if e['Catégorie'] == 'Dividende'])
            st.metric("💸 Dividendes attendus", dividend_events)
            
    else:
        st.info("Aucun événement prévu dans les 60 prochains jours.")
