# Nouveau compte Claude : tout reconnecter

À suivre à chaque changement de compte Claude. Ce fichier est la **seule** source de cette procédure :
ne la recopie nulle part ailleurs, renvoie ici.

**Ce qu'il faut demander à Claude**, dans un nouveau projet ou un nouveau thread :

> Nouveau compte Claude : suis NOUVEAU-COMPTE.md de ArnaudLafosse92100/orchestration-pack et reconnecte tout.

Depuis la 2.0.0, le pack n'a besoin d'aucun réglage par projet ni par compte : chaque dépôt projet porte
dans `.claude/settings.json` un hook SessionStart (le « bootstrap ») qui, dans une session cloud, clone ce
dépôt public et installe le pack dans `~/.claude`. Les étapes marquées **(toi)** passent par des réglages
que seul le titulaire du compte peut modifier ; Claude t'y envoie par un lien.

## 1. GitHub (toi)

1. Connecte ton compte GitHub : https://claude.ai/connect-github
2. Vérifie que l'app Claude a accès aux dépôts des projets : https://github.com/apps/claude/installations/select_target
   (`orchestration-pack` est public : aucun accès à lui donner).

## 2. Environnement cloud : rien à faire

L'environnement par défaut suffit, tant que son réseau laisse passer github.com (« Trusted » ou plus large).
Pas de Setup script. Si un ancien environnement « Orchestration » a encore un Setup script
`sync.sh --cloud`, vide-le : il enregistrerait les hooks une seconde fois.

## 3. Dépôt projet (Claude, une seule fois par dépôt)

Un dépôt sans bootstrap (`.claude/settings.json` sans entrée SessionStart `orchestration-pack`) le reçoit
par une PR :

```bash
git clone --depth 1 --branch main https://github.com/ArnaudLafosse92100/orchestration-pack /tmp/orchestration-pack
/tmp/orchestration-pack/sync.sh --bootstrap <repo>   # écrit <repo>/.claude/settings.json, retire une copie vendorée
```

Puis commit de `.claude/` sur une branche `chore/orchestration-bootstrap` et PR vers la branche par défaut.
Ensuite plus rien : chaque version fusionnée sur `main` d'orchestration-pack arrive seule à la session suivante.

## 4. Mac (Claude via ta session locale, ou toi)

Pour les sessions de l'app desktop (le bootstrap ne tourne qu'en cloud) :

```bash
git clone https://github.com/ArnaudLafosse92100/orchestration-pack ~/code/orchestration-pack
~/code/orchestration-pack/sync.sh --home
```

Mise à jour plus tard : `git -C ~/code/orchestration-pack pull && ~/code/orchestration-pack/sync.sh --home`.

## 5. Test de vérification (Claude, dans un thread neuf d'un projet équipé)

1. `ls ~/.claude/skills` montre `cloud` et `sisyphus`, et `cat ~/.claude/ORCHESTRATION_VERSION` montre la version de `VERSION`.
2. `/cloud` figure dans la liste des skills de la session.
3. `jq '.hooks | keys' .claude/settings.json` (dans le dépôt) liste `SessionStart`, `UserPromptSubmit`, `PreToolUse` et `Stop`.
4. Archivage de bout en bout : une Piste de test pousse `MESSAGE MONTANT : FINI, À ARCHIVER — …` sur
   `notes/verif-archive-status`, `skills/cloud/scripts/watch-status.sh --once verif-archive` réveille
   l'Orchestrateur, qui archive la Piste (`ARCHIVED (preuve)`) sans demander ton accord, ou note
   `CANNOT ARCHIVE (tool unavailable)`.

**Si le point 1 échoue** : `ls ~/.cache/orchestration-pack` (clone fait ?) puis lancer à la main
`~/.cache/orchestration-pack/sync.sh --session`. Le hook ne bloque jamais la session et reste muet.

## Limite connue

Le mode Auto ne peut pas venir du dépôt : Claude Code ignore `permissions.defaultMode` dans le `.claude/`
d'un projet, et le bootstrap tourne après le chargement des réglages utilisateur. Il se choisit dans la session.
