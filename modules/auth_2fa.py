# modules/auth_2fa.py
# Module d'authentification 2FA pour TLB INVESTOR

import streamlit as st
import smtplib
import random
import string
import time
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Tuple, Optional

class TLBAuthenticator2FA:
    """
    Système 2FA pour TLB INVESTOR
    Gestion complète de l'authentification à double facteur par email
    """
    
    def __init__(self):
        self.codes_file = ".temp/2fa_codes.json"
        self.code_expiry = 5 * 60  # 5 minutes en secondes
        
        # 📧 CONFIGURATION EMAIL GMAIL
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = "pierre.barennes@gmail.com"
        self.sender_password = "yzzv lozh txvk alyv"
        self.support_email = "pierre.barennes@gmail.com"  # Contact en cas de problème
    
    def is_2fa_required(self, username: str, config: Dict) -> bool:
        """
        Vérifier si l'utilisateur nécessite la 2FA
        
        Args:
            username: nom d'utilisateur
            config: configuration YAML chargée
            
        Returns:
            bool: True si 2FA requis, False sinon
        """
        try:
            user_info = config['credentials']['usernames'].get(username, {})
            
            # Vérifier si l'utilisateur est explicitement exclu de la 2FA
            # AJOUT : Nouveau champ dans config.yaml
            skip_2fa = user_info.get('skip_2fa', False)
            
            if skip_2fa:
                return False
                
            # Par défaut, tous les utilisateurs ont besoin de la 2FA
            return True
            
        except Exception as e:
            st.error(f"Erreur vérification 2FA pour {username}: {e}")
            # En cas d'erreur, on active la 2FA par sécurité
            return True
    
    def generate_code(self) -> str:
        """Générer un code aléatoire de 6 chiffres"""
        return ''.join(random.choices(string.digits, k=6))
    
    def send_code_by_email(self, username: str, user_email: str, user_name: str = "") -> Tuple[bool, str, str]:
        """
        Envoyer le code de 6 chiffres par email avec template TLB INVESTOR
        
        Args:
            username: nom d'utilisateur
            user_email: email de destination
            user_name: nom complet de l'utilisateur (optionnel)
            
        Returns:
            Tuple[bool, str, str]: (success, code, error_message)
        """
        try:
            # Générer le code
            code = self.generate_code()
            
            # Sauvegarder le code avec timestamp
            codes_data = self._load_codes()
            codes_data[username] = {
                'code': code,
                'timestamp': time.time(),
                'email': user_email,
                'attempts': 0  # Compteur de tentatives
            }
            self._save_codes(codes_data)
            
            # Préparer l'email avec template TLB INVESTOR
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = user_email
            msg['Subject'] = "🔐 Code de connexion TLB INVESTOR Portfolio"
            
            # Déterminer le nom d'affichage
            display_name = user_name if user_name else username
            
            # Version texte
            text_body = f"""
Bonjour {display_name},

Voici votre code de connexion sécurisé pour TLB INVESTOR Portfolio :

    {code}

⏰ Ce code expire dans 5 minutes pour votre sécurité.

Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.

En cas de problème, contactez : {self.support_email}

Cordialement,
L'équipe TLB INVESTOR
            """
            
            # Version HTML avec design TLB INVESTOR
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
                    .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center; }}
                    .header h1 {{ margin: 0; font-size: 28px; font-weight: bold; }}
                    .header p {{ margin: 10px 0 0 0; font-size: 16px; opacity: 0.9; }}
                    .content {{ padding: 40px 30px; }}
                    .greeting {{ font-size: 18px; color: #333; margin-bottom: 20px; }}
                    .code-container {{ background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border: 3px dashed #6c63ff; border-radius: 12px; padding: 30px; text-align: center; margin: 25px 0; }}
                    .code {{ font-size: 48px; font-weight: bold; color: #6c63ff; letter-spacing: 8px; font-family: 'Courier New', monospace; margin: 10px 0; }}
                    .code-label {{ font-size: 14px; color: #6c757d; text-transform: uppercase; letter-spacing: 1px; }}
                    .warning {{ background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 20px; margin: 25px 0; border-radius: 6px; }}
                    .warning-title {{ font-weight: bold; color: #856404; margin-bottom: 8px; }}
                    .warning-text {{ color: #856404; }}
                    .support {{ background-color: #e3f2fd; border-left: 5px solid #2196f3; padding: 20px; margin: 25px 0; border-radius: 6px; }}
                    .support-title {{ font-weight: bold; color: #1565c0; margin-bottom: 8px; }}
                    .support-text {{ color: #1565c0; }}
                    .footer {{ background-color: #f8f9fa; padding: 25px; text-align: center; }}
                    .footer-text {{ font-size: 12px; color: #6c757d; margin: 5px 0; }}
                    .brand {{ color: #6c63ff; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔐 TLB INVESTOR</h1>
                        <p>Portfolio Tracking - Authentification sécurisée</p>
                    </div>
                    <div class="content">
                        <div class="greeting">Bonjour <strong>{display_name}</strong>,</div>
                        
                        <p>Voici votre code de connexion sécurisé pour accéder à votre portfolio TLB INVESTOR :</p>
                        
                        <div class="code-container">
                            <div class="code-label">Code de vérification</div>
                            <div class="code">{code}</div>
                        </div>
                        
                        <div class="warning">
                            <div class="warning-title">⏰ Sécurité - Code temporaire</div>
                            <div class="warning-text">Ce code expire automatiquement dans <strong>5 minutes</strong> pour protéger votre compte.</div>
                        </div>
                        
                        <div class="support">
                            <div class="support-title">💬 Besoin d'aide ?</div>
                            <div class="support-text">En cas de problème avec ce code, contactez notre support : <strong>{self.support_email}</strong></div>
                        </div>
                        
                        <p style="margin-top: 30px; color: #6c757d;">Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email en toute sécurité.</p>
                        
                        <p style="margin-top: 20px;">Cordialement,<br><span class="brand">L'équipe TLB INVESTOR</span></p>
                    </div>
                    <div class="footer">
                        <div class="footer-text">© 2025 TLB INVESTOR - Portfolio Tracking System</div>
                        <div class="footer-text">Authentification sécurisée par email - Ne partagez jamais vos codes</div>
                        <div class="footer-text">Ce message est généré automatiquement</div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Créer les parties texte et HTML
            part1 = MIMEText(text_body, 'plain', 'utf-8')
            part2 = MIMEText(html_body, 'html', 'utf-8')
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Envoyer via Gmail
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            return True, code, ""
            
        except Exception as e:
            error_msg = f"Erreur envoi email : {str(e)}"
            return False, "", error_msg
    
    def verify_code(self, username: str, entered_code: str) -> Dict:
        """
        Vérifier le code saisi par l'utilisateur
        
        Args:
            username: nom d'utilisateur
            entered_code: code saisi
            
        Returns:
            dict: résultat de la vérification
        """
        codes_data = self._load_codes()
        
        if username not in codes_data:
            return {
                'success': False, 
                'reason': 'no_code', 
                'message': "Aucun code généré. Demandez un nouveau code."
            }
        
        user_data = codes_data[username]
        current_time = time.time()
        
        # Vérifier l'expiration (5 minutes)
        if current_time - user_data['timestamp'] > self.code_expiry:
            del codes_data[username]
            self._save_codes(codes_data)
            return {
                'success': False, 
                'reason': 'expired', 
                'message': "Code expiré (5 min). Demandez un nouveau code."
            }
        
        # Incrémenter le compteur de tentatives
        user_data['attempts'] = user_data.get('attempts', 0) + 1
        codes_data[username] = user_data
        self._save_codes(codes_data)
        
        # Limiter les tentatives (sécurité)
        if user_data['attempts'] > 5:
            del codes_data[username]
            self._save_codes(codes_data)
            return {
                'success': False, 
                'reason': 'too_many_attempts', 
                'message': "Trop de tentatives incorrectes. Demandez un nouveau code."
            }
        
        # Vérifier le code
        if entered_code.strip() == user_data['code']:
            del codes_data[username]
            self._save_codes(codes_data)
            return {
                'success': True, 
                'message': "Code vérifié ! Accès autorisé à votre portfolio."
            }
        else:
            remaining_attempts = 5 - user_data['attempts']
            return {
                'success': False, 
                'reason': 'wrong_code', 
                'message': f"Code incorrect. {remaining_attempts} tentative(s) restante(s)."
            }
    
    def cleanup_expired_codes(self):
        """Nettoyer les codes expirés (maintenance)"""
        try:
            codes_data = self._load_codes()
            current_time = time.time()
            
            expired_users = []
            for username, data in codes_data.items():
                if current_time - data['timestamp'] > self.code_expiry:
                    expired_users.append(username)
            
            for username in expired_users:
                del codes_data[username]
            
            if expired_users:
                self._save_codes(codes_data)
                
        except Exception:
            pass  # Silencieux pour la maintenance
    
    def _load_codes(self) -> Dict:
        """Charger les codes depuis le fichier JSON"""
        try:
            if os.path.exists(self.codes_file):
                with open(self.codes_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception:
            return {}
    
    def _save_codes(self, codes_data: Dict):
        """Sauvegarder les codes dans le fichier JSON"""
        try:
            os.makedirs(".temp", exist_ok=True)
            with open(self.codes_file, 'w') as f:
                json.dump(codes_data, f, indent=2)
        except Exception:
            pass

def display_2fa_page(username: str, user_email: str, user_name: str, config: Dict) -> bool:
    """
    Page complète d'authentification 2FA pour TLB INVESTOR - VERSION ANTI-DOUBLON
    
    Args:
        username: nom d'utilisateur
        user_email: email de l'utilisateur
        user_name: nom complet
        config: configuration YAML
        
    Returns:
        bool: True si 2FA validé, False sinon
    """
    
    # Initialiser le gestionnaire 2FA
    if 'tlb_2fa_manager' not in st.session_state:
        st.session_state.tlb_2fa_manager = TLBAuthenticator2FA()
    
    tfa_manager = st.session_state.tlb_2fa_manager
    
    # Nettoyage automatique des codes expirés
    tfa_manager.cleanup_expired_codes()
    
    # === SOLUTION ANTI-DOUBLON : CLÉ BASÉE SUR L'UTILISATEUR + TIMESTAMP DE CONNEXION ===
    # Créer une clé unique pour cette session de connexion 2FA
    session_2fa_key = f"tlb_2fa_session_{username}"
    
    # Vérifier si on a déjà une session 2FA active pour cet utilisateur
    if session_2fa_key not in st.session_state:
        # Première fois - créer la session avec timestamp
        import time
        connection_timestamp = int(time.time())
        st.session_state[session_2fa_key] = {
            'connection_time': connection_timestamp,
            'code_sent': False,
            'code_sent_time': None
        }
    
    session_2fa_data = st.session_state[session_2fa_key]
    
    # Interface utilisateur COMPACTE
    st.markdown("## 🔐 Authentification sécurisée")
    st.markdown(f"**Bonjour {user_name}** - Accès à votre portfolio TLB INVESTOR")
    
    # === ENVOI AUTOMATIQUE DU CODE (UNE SEULE FOIS PAR SESSION DE CONNEXION) ===
    if not session_2fa_data['code_sent']:
        with st.spinner("📤 Envoi du code de sécurité..."):
            success, code, error = tfa_manager.send_code_by_email(username, user_email, user_name)
            
            if success:
                # Marquer le code comme envoyé pour cette session
                st.session_state[session_2fa_key]['code_sent'] = True
                st.session_state[session_2fa_key]['code_sent_time'] = time.time()
                
                st.success(f"✅ Code de 6 chiffres envoyé à **{user_email}**")
                # Afficher le code pour les tests
                if st.session_state.get('username') in ['pbarennes', 'test_user']:
                    st.info(f"🧪 **Code de test :** {code}")
                # PAS de st.rerun() ici - c'est la cause des doublons !
            else:
                st.error(f"❌ Erreur lors de l'envoi : {error}")
                st.markdown(f"💬 **Contactez le support :** {tfa_manager.support_email}")
                return False
    
    # === VÉRIFIER QU'ON A UNE SESSION VALIDE ===
    if not session_2fa_data['code_sent'] or not session_2fa_data['code_sent_time']:
        st.error("❌ Erreur de session 2FA. Rafraîchissez la page.")
        return False
    
    # === INTERFACE COMPACTE TEMPS RESTANT + RENVOYER ===
    col_timer, col_resend = st.columns([2, 1])
    
    with col_timer:
        elapsed = time.time() - session_2fa_data['code_sent_time']
        remaining = max(0, 300 - elapsed)  # 5 minutes = 300 secondes
        
        if remaining > 0:
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            st.info(f"⏰ Code valide encore **{minutes}m {seconds}s** - Vérifiez vos emails")
        else:
            st.warning("⏰ Code expiré ! Utilisez 'Renvoyer'")
    
    with col_resend:
        if st.button("🔄 Renvoyer", help="Renvoyer un nouveau code", use_container_width=True):
            with st.spinner("📤 Renvoi..."):
                success, code, error = tfa_manager.send_code_by_email(username, user_email, user_name)
                
                if success:
                    # Mettre à jour SEULEMENT le timestamp
                    st.session_state[session_2fa_key]['code_sent_time'] = time.time()
                    st.success("✅ Nouveau code envoyé !")
                    # Afficher le code pour les tests
                    if st.session_state.get('username') in ['pbarennes', 'test_user']:
                        st.info(f"🧪 **Nouveau code :** {code}")
                    st.rerun()
                else:
                    st.error(f"❌ Erreur renvoi : {error}")
    
    # === FORMULAIRE DE VÉRIFICATION COMPACT ===
    st.markdown("---")
    
    with st.form("tlb_code_verification_form", clear_on_submit=True):
        col_input, col_button = st.columns([2, 1])
        
        with col_input:
            code_input = st.text_input(
                "🔢 Code de 6 chiffres",
                max_chars=6,
                placeholder="123456",
                help="Code reçu par email"
            )
        
        with col_button:
            st.markdown("<br>", unsafe_allow_html=True)  # Alignement vertical
            verify_button = st.form_submit_button(
                "✅ Vérifier", 
                type="primary", 
                use_container_width=True
            )
    
    # === TRAITEMENT DE LA VÉRIFICATION ===
    if verify_button and code_input:
        if len(code_input) != 6 or not code_input.isdigit():
            st.error("⚠️ Le code doit contenir exactement 6 chiffres.")
        else:
            result = tfa_manager.verify_code(username, code_input)
            
            if result['success']:
                st.success(result['message'])
                # Nettoyer la session 2FA complètement
                if session_2fa_key in st.session_state:
                    del st.session_state[session_2fa_key]
                # Marquer la 2FA comme validée
                st.session_state.tlb_2fa_verified = True
                time.sleep(1)
                return True  # ✅ VALIDATION RÉUSSIE
            else:
                st.error(result['message'])
                if result['reason'] in ['expired', 'too_many_attempts']:
                    # Code expiré, nettoyer et permettre un nouveau code
                    if session_2fa_key in st.session_state:
                        del st.session_state[session_2fa_key]
                    st.info("💡 Génération d'un nouveau code...")
                    time.sleep(1)
                    st.rerun()
    
    # === MESSAGE D'AIDE COMPACT ===
    with st.expander("💡 Problème avec le code ?", expanded=False):
        st.markdown(f"""
        **🔍 Code non reçu ?** Vérifiez le dossier spam et utilisez "Renvoyer"
        
        **⚠️ Problème persistant ?** Contactez **{tfa_manager.support_email}** avec votre nom d'utilisateur : **{username}**
        """)
    
    return False  # ❌ PAS ENCORE VALIDÉ

def check_2fa_status(username: str, config: Dict) -> str:
    """
    Vérifier le statut 2FA d'un utilisateur
    
    Returns:
        str: 'not_required', 'required', 'verified'
    """
    # Initialiser le gestionnaire si besoin
    if 'tlb_2fa_manager' not in st.session_state:
        st.session_state.tlb_2fa_manager = TLBAuthenticator2FA()
    
    tfa_manager = st.session_state.tlb_2fa_manager
    
    # Vérifier si 2FA requis pour cet utilisateur
    if not tfa_manager.is_2fa_required(username, config):
        return 'not_required'
    
    # Vérifier si déjà vérifié dans cette session
    if st.session_state.get('tlb_2fa_verified', False):
        return 'verified'
    
    return 'required'

def cleanup_2fa_session():
    """Nettoyer toutes les données 2FA de la session"""
    keys_to_delete = []
    for key in st.session_state.keys():
        if key.startswith('tlb_2fa_') or key in ['tlb_2fa_verified', 'tlb_2fa_manager']:
            keys_to_delete.append(key)
    
    for key in keys_to_delete:
        del st.session_state[key]
