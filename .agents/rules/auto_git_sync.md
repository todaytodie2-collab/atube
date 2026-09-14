# Continuous Real-Time GitHub Synchronization Rule

## Mandatory Rule for AI Assistant
Whenever ANY code modification, bug fix, feature addition, or file update is performed:
1. You MUST automatically stage and commit all modified files.
2. You MUST immediately push the commit to GitHub (`git push origin main`).
3. DO NOT wait for the user to ask "هل تمت المزامنة؟" or request a push. Synchronization must occur automatically at the end of every task or change set.
4. If remote changes exist, use `git pull --rebase origin main` before pushing.
5. If any transient cache files are modified, keep them ignored or excluded so the commit remains clean.
