# test_2fa.py
# Module de test pour l'authentification 2FA

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import smtplib
import random
import string
import time
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# === CONFIGURATION ===
st.set_page_config(page_title='Test 2FA TLB INVESTOR', layout='wide')

class Simple2FA:
    """
    Système 2FA simple : Username/MDP → Code par email → Accès
    """
    
    def __init__(self):
        self.codes_file = ".temp/2fa_codes.json"
        self.code_expiry = 5 * 60  # 5 minutes en secondes
        
        # 📧 CONFIGURATION EMAIL GMAIL
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = "pierre.barennes@gmail.com"  # Votre Gmail
        self.sender_password = "yzzv lozh txvk alyv"     # Votre mot de passe d'app
    
    def generate_code(self) -> str:
        """Générer un code aléatoire de 8 chiffres"""
        return ''.join(random.choices(string.digits, k=6))
    
    def send_code_by_email(self, username: str, user_email: str) -> bool:
        """Envoyer le code de 8 chiffres par email avec mise en forme"""
        try:
            # Générer le code
            code = self.generate_code()
            
            # Sauvegarder le code avec timestamp
            codes_data = self._load_codes()
            codes_data[username] = {
                'code': code,
                'timestamp': time.time(),
                'email': user_email
            }
            self._save_codes(codes_data)
            
            # Préparer l'email avec mise en forme HTML
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = user_email
            msg['Subject'] = "🔐 Code de connexion TLB INVESTOR"
            
            # Version texte
            text_body = f"""
Bonjour {username},

Voici votre code de connexion pour TLB INVESTOR :

    {code}

⏰ Ce code expire dans 5 minutes.

Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.

Cordialement,
TLB INVESTOR
            """
            
            # Version HTML avec mise en forme
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                    .header h1 {{ margin: 0; font-size: 24px; }}
                    .content {{ padding: 30px; }}
                    .code-container {{ background-color: #f8f9fa; border: 2px dashed #6c63ff; border-radius: 8px; padding: 25px; text-align: center; margin: 20px 0; }}
                    .code {{ font-size: 36px; font-weight: bold; color: #6c63ff; letter-spacing: 4px; font-family: 'Courier New', monospace; }}
                    .warning {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
                    .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #6c757d; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔐 TLB INVESTOR</h1>
                        <p>Code de connexion sécurisé</p>
                    </div>
                    <div class="content">
                        <h2>Bonjour {username},</h2>
                        <p>Voici votre code de connexion sécurisé pour accéder à TLB INVESTOR :</p>
                        
                        <div class="code-container">
                            <div class="code">{code}</div>
                            <p style="margin: 10px 0 0 0; color: #6c757d;">Code de vérification</p>
                        </div>
                        
                        <div class="warning">
                            <strong>⏰ Important :</strong> Ce code expire dans <strong>5 minutes</strong> pour votre sécurité.
                        </div>
                        
                        <p>Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email en toute sécurité.</p>
                        
                        <p>Cordialement,<br><strong>L'équipe TLB INVESTOR</strong></p>
                    </div>
                    <div class="footer">
                        <p>© 2025 TLB INVESTOR - Système d'authentification sécurisé</p>
                        <p>Ce message est généré automatiquement, merci de ne pas y répondre.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Créer les parties texte et HTML
            part1 = MIMEText(text_body, 'plain', 'utf-8')
            part2 = MIMEText(html_body, 'html', 'utf-8')
            
            # Ajouter les parties au message
            msg.attach(part1)
            msg.attach(part2)
            
            # Envoyer via Gmail
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            st.success(f"✅ Code {code} envoyé à {user_email}")  # Afficher le code pour le test
            return True
            
        except Exception as e:
            st.error(f"❌ Erreur envoi email : {e}")
            return False
    
    def verify_code(self, username: str, entered_code: str) -> dict:
        """Vérifier le code saisi par l'utilisateur"""
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
        
        # Vérifier le code
        if entered_code.strip() == user_data['code']:
            del codes_data[username]
            self._save_codes(codes_data)
            return {
                'success': True, 
                'message': "Code vérifié ! Connexion autorisée."
            }
        else:
            return {
                'success': False, 
                'reason': 'wrong_code', 
                'message': "Code incorrect. Vérifiez et réessayez."
            }
    
    def _load_codes(self) -> dict:
        """Charger les codes depuis le fichier JSON"""
        try:
            if os.path.exists(self.codes_file):
                with open(self.codes_file, 'r') as f:
                    return json.load(f)
            return {}
        except:
            return {}
    
    def _save_codes(self, codes_data: dict):
        """Sauvegarder les codes dans le fichier JSON"""
        try:
            os.makedirs(".temp", exist_ok=True)
            with open(self.codes_file, 'w') as f:
                json.dump(codes_data, f, indent=2)
        except:
            pass

def display_2fa_interface(username: str, user_email: str) -> bool:
    """
    Interface 2FA : Envoi automatique + vérification du code
    Retourne True si validation réussie, False sinon
    """
    
    # Initialiser le gestionnaire 2FA
    if 'tfa_manager' not in st.session_state:
        st.session_state.tfa_manager = Simple2FA()
    
    tfa_manager = st.session_state.tfa_manager
    
    # Interface utilisateur
    st.markdown("### 🔐 Authentification à double facteur")
    st.info(f"📧 Un code de sécurité va être envoyé automatiquement à : **{user_email}**")
    
    # === ENVOI AUTOMATIQUE DU CODE ===
    if 'auto_code_sent' not in st.session_state:
        st.session_state.auto_code_sent = False
    
    if not st.session_state.auto_code_sent:
        with st.spinner("📤 Envoi automatique du code de sécurité..."):
            if tfa_manager.send_code_by_email(username, user_email):
                st.session_state.code_sent_time = time.time()
                st.session_state.auto_code_sent = True
                st.rerun()
            else:
                st.error("❌ Erreur lors de l'envoi automatique.")
                return False
    
    # === BOUTON RENVOYER ===
    st.markdown("---")
    col_info, col_resend = st.columns([3, 1])
    
    with col_info:
        st.success("✅ Code envoyé ! Vérifiez votre boîte email (et le dossier spam).")
    
    with col_resend:
        if st.button("🔄 Renvoyer", help="Renvoyer un nouveau code", use_container_width=True):
            with st.spinner("📤 Renvoi en cours..."):
                if tfa_manager.send_code_by_email(username, user_email):
                    st.session_state.code_sent_time = time.time()
                    st.success("✅ Nouveau code envoyé !")
                    st.rerun()
                else:
                    st.error("❌ Erreur lors du renvoi.")
    
    # === AFFICHER LE TEMPS RESTANT ===
    if 'code_sent_time' in st.session_state:
        elapsed = time.time() - st.session_state.code_sent_time
        remaining = max(0, 300 - elapsed)  # 5 minutes = 300 secondes
        
        if remaining > 0:
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            st.info(f"⏰ Code valide encore **{minutes}m {seconds}s**")
        else:
            st.warning("⏰ Code expiré ! Cliquez sur 'Renvoyer' pour un nouveau code.")
    
    # === FORMULAIRE DE VÉRIFICATION ===
    st.markdown("---")
    with st.form("code_verification_form"):
        st.markdown("#### 🔢 Saisissez votre code de 8 chiffres")
        
        code_input = st.text_input(
            "Code reçu par email",
            max_chars=8,
            placeholder="12345678",
            help="Code de 8 chiffres reçu par email"
        )
        
        verify_button = st.form_submit_button("✅ Vérifier le code", type="primary", use_container_width=True)
    
    # === TRAITEMENT DE LA VÉRIFICATION ===
    if verify_button and code_input:
        if len(code_input) != 8 or not code_input.isdigit():
            st.error("⚠️ Le code doit contenir exactement 8 chiffres.")
        else:
            result = tfa_manager.verify_code(username, code_input)
            
            if result['success']:
                st.success(result['message'])
                # Nettoyer les variables de session
                if 'code_sent_time' in st.session_state:
                    del st.session_state.code_sent_time
                if 'auto_code_sent' in st.session_state:
                    del st.session_state.auto_code_sent
                time.sleep(1)
                return True  # ✅ VALIDATION RÉUSSIE
            else:
                st.error(result['message'])
                if result['reason'] == 'expired':
                    # Code expiré, nettoyer
                    if 'code_sent_time' in st.session_state:
                        del st.session_state.code_sent_time
                    if 'auto_code_sent' in st.session_state:
                        del st.session_state.auto_code_sent
    
    return False  # ❌ PAS ENCORE VALIDÉ

# === CONFIGURATION DU CONFIG.YAML ===

# Charger le config.yaml existant depuis le dossier courant
config_path = 'config.yaml'
if not os.path.exists(config_path):
    st.error('❌ Fichier config.yaml introuvable dans le dossier courant.')
    st.info('💡 Assurez-vous que le fichier config.yaml est dans le même dossier que ce script de test.')
    st.stop()

# === CHARGER LA CONFIGURATION ===
try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.load(f, Loader=SafeLoader)
    st.success(f"✅ Configuration chargée depuis {config_path}")
except Exception as e:
    st.error(f"❌ Erreur lors du chargement du fichier config.yaml : {e}")
    st.stop()

# === AUTHENTIFICATEUR ===
authenticator = stauth.Authenticate(
    config['credentials'], 
    config['cookie']['name'],
    config['cookie']['key'], 
    config['cookie']['expiry_days']
)

# === INTERFACE PRINCIPALE ===

st.title("🧪 Test Authentification 2FA - TLB INVESTOR")

st.markdown("""
### 🎯 **Test du système d'authentification à 2 facteurs**

**Étapes du test :**
1. **Connexion classique** : Username + Mot de passe
2. **2FA automatique** : Code envoyé par email
3. **Validation** : Saisie du code reçu
4. **Accès** : Interface d'administration

**Comptes de test disponibles :**
- `pbarennes` (MDP: `PB`) → pierre.barennes@gmail.com
- `PB` (MDP: `PB`) → p.barennes@pareanbiotech.fr  
- `tlibert` (MDP: voir Thomas) → contact.thomastlb@gmail.com
""")

st.markdown("---")

# === GESTION DE L'AUTHENTIFICATION ===
try:
    authenticator.login()
except Exception as e:
    st.error(f"Erreur d'authentification : {e}")

# === TRAITEMENT DES CAS ===
if st.session_state.get('authentication_status') is False:
    st.error('❌ Nom d\'utilisateur ou mot de passe incorrect')
    
elif st.session_state.get('authentication_status') is None:
    st.warning('👆 Veuillez saisir vos identifiants ci-dessus')
    
elif st.session_state.get('authentication_status') is True:
    
    # === ÉTAPE 1 : AUTHENTIFICATION CLASSIQUE RÉUSSIE ===
    username = st.session_state.get('username')
    st.success(f"✅ **Étape 1 réussie** : Authentification classique pour {username}")
    
    # Récupérer les informations utilisateur
    user_info = config['credentials']['usernames'][username]
    user_email = user_info.get('email')
    first_name = user_info.get('first_name')
    last_name = user_info.get('last_name')
    
    st.info(f"👤 **Utilisateur** : {first_name} {last_name} ({user_email})")
    
    # === ÉTAPE 2 : VÉRIFICATION 2FA ===
    if 'tfa_verified' not in st.session_state:
        st.session_state.tfa_verified = False
    
    if not st.session_state.tfa_verified:
        st.markdown("---")
        st.markdown("### ⭐ **Étape 2 : Authentification 2FA**")
        
        if display_2fa_interface(username, user_email):
            st.session_state.tfa_verified = True
            st.rerun()
        else:
            st.stop()  # Arrêter jusqu'à validation 2FA
    
    # === ÉTAPE 3 : ACCÈS ACCORDÉ ===
    st.markdown("---")
    st.success("🎉 **Test réussi !** Authentification 2FA complète")
    
    st.markdown(f"""
    ### ✅ **Récapitulatif du test :**
    
    **👤 Utilisateur connecté :** {first_name} {last_name} ({username})  
    **📧 Email utilisé :** {user_email}  
    **🔐 Étape 1 :** Authentification classique ✅  
    **📱 Étape 2 :** Code 2FA par email ✅  
    **🚪 Accès :** Application autorisée ✅  
    
    ### 🛠️ **Interface d'administration (simulation)**
    """)
    
    # Interface de test
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🔒 Sécurité", "2FA Activé", "✅ Sécurisé")
    
    with col2:
        access_level = user_info.get('access_level', 'standard')
        st.metric("👑 Niveau d'accès", access_level.title(), "🎯 Autorisé")
    
    with col3:
        login_time = datetime.now().strftime('%H:%M:%S')
        st.metric("⏰ Connexion", login_time, "🕐 Maintenant")
    
    # Bouton de déconnexion
    st.markdown("---")
    col_logout, col_empty = st.columns([1, 3])
    
    with col_logout:
        if st.button("🚪 Se déconnecter", type="secondary"):
            # Nettoyer toutes les variables 2FA
            if 'tfa_verified' in st.session_state:
                del st.session_state.tfa_verified
            if 'code_sent_time' in st.session_state:
                del st.session_state.code_sent_time
            if 'auto_code_sent' in st.session_state:
                del st.session_state.auto_code_sent
            if 'tfa_manager' in st.session_state:
                del st.session_state.tfa_manager
            
            # Déconnexion classique
            authenticator.logout()
            st.rerun()

# === SECTION DEBUG ===
with st.sidebar:
    st.markdown("### 🔧 Debug")
    
    if st.button("🧪 Test envoi email rapide"):
        tfa = Simple2FA()
        test_success = tfa.send_code_by_email("test_user", "pierre.barennes@gmail.com")
        if test_success:
            st.success("✅ Email de test envoyé !")
        else:
            st.error("❌ Erreur envoi test")
    
    st.markdown("### 📊 État de la session")
    st.write("**Authentication Status:**", st.session_state.get('authentication_status'))
    st.write("**Username:**", st.session_state.get('username'))
    st.write("**2FA Verified:**", st.session_state.get('tfa_verified', False))
    st.write("**Auto Code Sent:**", st.session_state.get('auto_code_sent', False))
    
    if 'code_sent_time' in st.session_state:
        elapsed = time.time() - st.session_state.code_sent_time
        st.write(f"**Code envoyé il y a:** {elapsed:.0f}s")

st.markdown("---")
st.markdown("_Test module créé pour TLB INVESTOR - Authentification 2FA_")
