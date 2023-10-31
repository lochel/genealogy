import os

from flask import Flask
import flask_login

app = Flask(__name__)

# python3 -c 'import secrets; print(secrets.token_hex())'
app.config['SECRET_KEY'] = '5f5bfb3b1cd072bfa391bfd05e10ba39ec5a365486c79416b97fb88e3fa29495'

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

from genealogy import routes
