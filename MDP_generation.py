import bcrypt

mot_de_passe = "tLibert$20250722_001"  # Change ici ton mot de passe
mot_de_passe_bytes = mot_de_passe.encode('utf-8')

# Génération du hash
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(mot_de_passe_bytes, salt)

# Affichage
print("Mot de passe :", mot_de_passe)
print("Hash bcrypt à copier dans config.yaml :")
print(hashed.decode('utf-8'))
