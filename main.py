import os

from flask import Flask
from app import create_app

app = create_app()

if __name__ == "__main__":
    # app.run(debug=True, port=8001, host="0.0.0.0")
    port = int(os.environ.get("PORT", 5000))

    # app.run(port=port, host="0.0.0.0")
    app.run(debug=True)
