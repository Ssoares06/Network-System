from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///network.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.urandom(24)
    
    login_manager.init_app(app)
    login_manager.login_view = 'web.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'warning'
    
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        from models.switch import Switch
        from models.user import User
        from models.data_dictionary import DataDictionary
        db.create_all()

    # Registrar rotas web
    from routes.web import web_bp
    app.register_blueprint(web_bp)
    
    # Registrar rotas da API para o sistema de consultas
    from routes.network_api import network_api_bp
    app.register_blueprint(network_api_bp, url_prefix='/api')
    
    return app

@login_manager.user_loader
def load_user(user_id):
    from models.user import User
    return User.query.get(int(user_id))