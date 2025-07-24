import smtplib
import random
import string
import time
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

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
        self.sender_email = "pierre.barennes@gmail.com"  # ← CHANGEZ ICI
        self.sender_password = "yzzv lozh txvk alyv"  # ← MOT DE PASSE D'APPLICATION GMAIL
    
    def generate_code(self) -> str:
        """Générer un code aléatoire de 6 chiffres"""
        return ''.join(random.choices(string.digits, k=6))
    
    def send_code_by_email(self, username: str, user_email: str) -> bool:
        """
        Envoyer le code de 6 chiffres par email
        """
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
            
            # Préparer l'email
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = user_email
            msg['Subject'] = "🔐 Code de connexion TLB INVESTOR"
            
            # Corps de l'email simple et clair
            body = f"""
Bonjour {username},

Voici votre code de connexion pour TLB INVESTOR :

    {code}

⏰ Ce code expire dans 5 minutes.

Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.

Cordialement,
TLB INVESTOR
            """
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Envoyer via Gmail
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            print(f"✅ Code {code} envoyé à {user_email}")  # Debug
            return True
            
        except Exception as e:
            print(f"❌ Erreur envoi email : {e}")  # Debug
            return False
    
    def verify_code(self, username: str, entered_code: str) -> dict:
        """
        Vérifier le code saisi par l'utilisateur
        """
        codes_data = self._load_codes()
        
        # Vérifier si un code existe pour cet utilisateur
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
            # Code expiré, le supprimer
            del codes_data[username]
            self._save_codes(codes_data)
            return {
                'success': False, 
                'reason': 'expired', 
                'message': "Code expiré (5 min). Demandez un nouveau code."
            }
        
        # Vérifier le code
        if entered_code.strip() == user_data['code']:
            # Code correct ! Le supprimer pour qu'il ne soit plus utilisable
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

# === INTERFACE STREAMLIT ===

def display_2fa_interface(username: str, user_email: str) -> bool:
    """
    Interface 2FA : Demander et vérifier le code
    Retourne True si validation réussie, False sinon
    """
    
    # Initialiser le gestionnaire 2FA
    if 'tfa_manager' not in st.session_state:
        st.session_state.tfa_manager = Simple2FA()
    
    tfa_manager = st.session_state.tfa_manager
    
    # Interface utilisateur
    st.markdown("### 🔐 Authentification à double facteur")
    st.info(f"📧 Un code va être envoyé à : **{user_email}**")
    
    # === ÉTAPE 1 : ENVOYER LE CODE ===
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("📨 Envoyer le code de connexion", type="primary", use_container_width=True):
            with st.spinner("📤 Envoi du code en cours..."):
                if tfa_manager.send_code_by_email(username, user_email):
                    st.success("✅ Code envoyé ! Vérifiez votre boîte email.")
                    if 'code_sent_time' not in st.session_state:
                        st.session_state.code_sent_time = time.time()
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de l'envoi. Vérifiez la configuration email.")
    
    with col2:
        if st.button("🔄 Renvoyer", help="Renvoyer un nouveau code"):
            with st.spinner("📤 Renvoi en cours..."):
                if tfa_manager.send_code_by_email(username, user_email):
                    st.success("✅ Nouveau code envoyé !")
                    st.session_state.code_sent_time = time.time()
                    st.rerun()
                else:
                    st.error("❌ Erreur lors du renvoi.")
    
    # === ÉTAPE 2 : VÉRIFIER LE CODE ===
    st.markdown("---")
    
    # Afficher le temps restant si un code a été envoyé
    if 'code_sent_time' in st.session_state:
        elapsed = time.time() - st.session_state.code_sent_time
        remaining = max(0, 300 - elapsed)  # 5 minutes = 300 secondes
        
        if remaining > 0:
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            st.info(f"⏰ Code valide encore {minutes}m {seconds}s")
        else:
            st.warning("⏰ Code expiré ! Demandez un nouveau code.")
    
    # Formulaire de saisie du code
    with st.form("code_verification_form"):
        st.markdown("#### 🔢 Saisissez votre code de 6 chiffres")
        
        code_input = st.text_input(
            "Code reçu par email",
            max_chars=6,
            placeholder="123456",
            help="Code de 6 chiffres reçu par email"
        )
        
        verify_button = st.form_submit_button("✅ Vérifier le code", type="primary", use_container_width=True)
    
    # === TRAITEMENT DE LA VÉRIFICATION ===
    if verify_button and code_input:
        if len(code_input) != 6 or not code_input.isdigit():
            st.error("⚠️ Le code doit contenir exactement 6 chiffres.")
        else:
            result = tfa_manager.verify_code(username, code_input)
            
            if result['success']:
                st.success(result['message'])
                # Nettoyer les variables de session
                if 'code_sent_time' in st.session_state:
                    del st.session_state.code_sent_time
                time.sleep(1)
                return True  # ✅ VALIDATION RÉUSSIE
            else:
                st.error(result['message'])
                if result['reason'] == 'expired':
                    # Code expiré, nettoyer
                    if 'code_sent_time' in st.session_state:
                        del st.session_state.code_sent_time
    
    return False  # ❌ PAS ENCORE VALIDÉ

# === INTÉGRATION DANS MAIN.PY ===

def integrate_2fa_in_main():
    """
    Code à intégrer dans main.py après l'authentification username/password
    """
    
    # === APRÈS : elif st.session_state.get('authentication_status') is True:
    
    username = st.session_state.get('username')
    
    # Récupérer l'email depuis config.yaml
    try:
        user_email = config['credentials']['usernames'][username].get('email')
        if not user_email:
            st.error("❌ Aucun email configuré pour cet utilisateur.")
            st.stop()
    except:
        st.error("❌ Erreur de configuration utilisateur.")
        st.stop()
    
    # === VÉRIFICATION 2FA ===
    if 'tfa_verified' not in st.session_state:
        st.session_state.tfa_verified = False
    
    if not st.session_state.tfa_verified:
        # Afficher l'interface 2FA
        if display_2fa_interface(username, user_email):
            st.session_state.tfa_verified = True
            st.rerun()
        else:
            st.stop()  # Arrêter jusqu'à validation 2FA
    
# === TEST EN CONSOLE ===
def test_email_sending():
    """
    Fonction de test pour vérifier l'envoi d'email
    """
    tfa = Simple2FA()
    
    # Test d'envoi
    success = tfa.send_code_by_email("test_user", "destinataire@example.com")
    print(f"Test envoi : {'✅ Succès' if success else '❌ Échec'}")
    
    # Afficher le code généré (pour debug)
    codes = tfa._load_codes()
    if "test_user" in codes:
        print(f"Code généré : {codes['test_user']['code']}")

# Décommentez pour tester :
test_email_sending()
