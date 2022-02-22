
import flask_excel as excel
from app.api import bp
from flask import request
from app.utils.user_auth import token_auth
from app.models import Alert, InactivityAlert
from sqlalchemy.orm import with_polymorphic
from dateutil import parser

@bp.route('/utility/csv', methods=['POST'])
@token_auth.login_required
def get_csv():
    data = request.get_json()
    return create_csv(data['table'], data['title'])


def create_csv(data, title):
    return excel.make_response_from_array(
        data, "csv", file_name=title)


