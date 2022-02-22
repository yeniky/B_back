from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from flask_mail import Mail
import secrets
import string
from config import Config
from itsdangerous import URLSafeTimedSerializer
from app.models import User, Role
from flask_mail import Message
from app.api.errors import error_response, bad_request
from app import mail

basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()
alphabet = string.ascii_letters + string.digits
config = Config()


@basic_auth.verify_password
def verify_password(email, password):
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        return user


@basic_auth.error_handler
def basic_auth_error(status):
    return error_response(status)


@token_auth.verify_token
def verify_token(token):
    return User.check_token(token) if token else None


@token_auth.error_handler
def token_auth_error(status):
    return error_response(status)


@token_auth.get_user_roles
def get_user_roles(user):
    return [user.role]


def send_activation_email(email, token):
    msg = Message('Activation Email', sender='tranckandtrace@outlook.com',
                  recipients=[email])
    activation_link = f'http://165.227.91.98:3000/activate/{token}'
    msg.body = f'Please, set password for your account throw this link: {activation_link}'
    mail.send(msg)

def send_alert_email(emails, text):
    msg = Message('Notificación de alerta', sender='tranckandtrace@outlook.com',
                  recipients=emails)
    msg.body = text
    mail.send(msg)

def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(config.SECRET_KEY)
    return serializer.dumps(email, salt=config.SECURITY_PASSWORD_SALT)


def confirm_token(token, expiration=3600000):
    serializer = URLSafeTimedSerializer(config.SECRET_KEY)
    try:
        email = serializer.loads(
            token,
            salt=config.SECURITY_PASSWORD_SALT,
            max_age=expiration
        )
    except:
        return False
    return email
