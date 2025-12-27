# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/interfaces/cli/main.py
# module: quack_core.interfaces.cli.main
# role: cli
# neighbors: __init__.py, app.py
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

from quack_core.interfaces.cli.app import app

if __name__ == "__main__":
    app()