# Politique de confidentialité — MergeImages

MergeImages traite les fichiers et les messages envoyés volontairement par les utilisateurs afin d’exécuter les opérations demandées. Les images, PDF, GIF, textes OCR et contenus de codes QR traités ne sont pas automatiquement envoyés à l’administrateur.

Le service peut traiter l’identifiant Telegram, le nom public, la langue, les préférences, les événements d’utilisation et les tickets d’assistance. Les journaux généraux ne doivent pas enregistrer les noms d’utilisateur ; l’ancienne colonne peut être conservée pour la compatibilité. Le nom d’utilisateur n’est utilisé que dans le flux des tickets lorsque cela est nécessaire pour contacter l’utilisateur.

L’administrateur peut recevoir des métriques agrégées, notamment le nombre d’actions, d’images générées, de codes QR, d’opérations OCR, de conversions et d’utilisateurs actifs. Lorsqu’un utilisateur ouvre un ticket, le texte, le nom public, le nom d’utilisateur et l’identifiant Telegram peuvent être transmis à l’administrateur afin d’enquêter et de répondre. N’incluez pas de mots de passe, de jetons ou de documents privés dans les tickets.

La recherche visuelle exige une confirmation explicite avant l’envoi d’une image à Telegra.ph ou Catbox.moe, puis son utilisation par Google Lens. Ces services disposent de leurs propres politiques de conservation. Les endpoints du Mini App utilisent `initData` signé par Telegram ; CORS est restreint via `MINIAPP_ALLOWED_ORIGINS`, et CORS ne remplace pas l’authentification. Le diagnostic est réservé à l’administrateur.

Le message de soutien peut être envoyé au maximum une fois après sept jours d’utilisation et, séparément, une fois lorsque le quota de crédits est atteint. L’opérateur doit définir les durées de conservation des fichiers temporaires, de la base de données, des journaux et des tickets, et proposer leur suppression ou anonymisation. Ne publiez jamais de jetons, clés API, bases de données de production ou identifiants.
