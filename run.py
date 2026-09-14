from app import create_app

app = create_app()

if __name__ == "__main__":
    # F5 (intentional): debug mode exposes the interactive debugger and stack traces.
    # Fixed in Module 08 (Semgrep flags this) by driving debug from an env var, default False.
    app.run(host="0.0.0.0", port=5000, debug=True)
