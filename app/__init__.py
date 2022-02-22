from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_admin import Admin
from config import Config
import flask_excel as excel
from flask_mail import Mail
from flask_apscheduler import APScheduler

db = SQLAlchemy()
admin = Admin(name="Bayer Admin")
mail = Mail()
scheduler = APScheduler()

def create_app(config_class=Config):
    app = Flask(__name__, static_folder='../client/build/',
                instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Mail
    app.config['MAIL_SERVER'] = 'smtp.office365.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USERNAME'] = 'tranckandtrace@outlook.com'
    app.config['MAIL_PASSWORD'] = 'lqnrchjzofokckyb'
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    mail.init_app(app)

    # Scheduler
    scheduler.api_enabled = True
    scheduler.init_app(app)
    scheduler.start()


    admin.init_app(app)
    excel.init_excel(app)
    import app.controllers.admin_views as admin_routes

    from app.api import bp as api_routes
    app.register_blueprint(api_routes, url_prefix='/api')

    from app.controllers.api_debug_routes import bp as debug_routes
    app.register_blueprint(debug_routes, url_prefix='/debug')

    from app import models

    @app.before_first_request
    def load_tasks():
        from app.utils import inactivity_alert 
    return app
