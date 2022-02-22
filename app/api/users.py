from flask import jsonify, request
from app.api.errors import error_response, bad_request
from flask import Response
from app import db
from app.api import bp
from app.models import User, Role, AlertRule,BatchAlertRule,ProximityAlertRule, ZoneAlertRule, MapInfo
from app.utils.user_auth import basic_auth, token_auth, generate_confirmation_token, send_activation_email, confirm_token
from app.utils.helpers import build_page
from app.utils.helpers import generate_order_by

@bp.route('/users', methods=['GET'])
@token_auth.login_required(role=[Role.Admin])
def get_users():
    user = basic_auth.current_user()
    page = request.args.get('page', 1, type=int)
    include_self = request.args.get('include_self', False, type=bool)
    per_page = request.args.get('per_page', 10, type=int)
    order_by = request.args.get('order_by', "")
    order = request.args.get('order', "asc")
    query = User.query.filter(User.id !=user.id) if not include_self else User.query
    if order_by:
        query = generate_order_by(query, User, order_by,order,User.prop_to_order)
    users = query.paginate(page,per_page,False)
    return jsonify(build_page(users,order_by,order, User.to_dict))


@bp.route('/users/login', methods=['GET'])
@basic_auth.login_required
def login():
    user = basic_auth.current_user()
    if(not user.active):
        return bad_request(f'Inactive account. Check your email for activation link')
    return jsonify(user.to_dict())


@bp.route('/users/<int:id>', methods=['DELETE'])
@token_auth.login_required(role=[Role.Admin])
def delete_users(id):
    user = User.query.get(id)
    if(user and user.role != Role.Admin):
        db.session.delete(user)
        db.session.commit()
        return Response(status=200)
    return bad_request(f'User with id={id} does not exist')


@bp.route('/users', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def create_user():
    data = request.get_json() or {}
    if(not 'email' in data):
        return bad_request('Email required')
    if(User.query.filter_by(email=data['email']).first()):
        return bad_request('A user with that email already exists')
    if(not data['role'] in [str(r) for r in Role]):
        return bad_request('Invalid role')
    user = User(email=data['email'], role=Role(data['role']))
    token = generate_confirmation_token(user.email)
    try:
        send_activation_email(user.email, token)
    except Exception as e:
        print(e)
        print('error sending mail')
        return False
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict())


@bp.route('/users/activation/<token>', methods=['POST'])
def activate_user(token):
    data = request.get_json() or {}
    if(not 'password' in data):
        return bad_request('Password is required')
    if(not 'username' in data):
        return bad_request('Username is required')
    if(len(data['password']) < 8 or len(data['password']) > 20):
        return bad_request('Invalid password. Min length:8, Max length:20')
    user = confirm_user(token, data['username'], data['password'])
    if(not user):
        return bad_request('Invalid activation token')
    subscribe_user(user)
    return Response(status=200)

def subscribe_user(user):
    rules = AlertRule.query.all()
    for r in rules:
        if r.owner_type != 'inactivity_alert_rule':
            r.users.append(user)
    db.session.commit()

def confirm_user(token, username, password):
    email = confirm_token(token)
    if(not email):
        return None
    user = User.query.filter_by(email=email).first()
    if(not user):
        return None
    user.username = username
    user.set_password(password)
    user.active = True
    db.session.commit()
    return user


@bp.route('/users/token', methods=['POST'])
@basic_auth.login_required
def get_token():
    user = basic_auth.current_user()
    if(not user.active):
        return bad_request(f'Inactive account. Check your email for activation link')
    token = user.get_token()
    db.session.commit()
    return jsonify({'token': token})


@bp.route('/users/<int:id>', methods=['PUT'])
@token_auth.login_required
def edit_user(id):
    if (not token_auth.current_user()) or token_auth.current_user().id != id:
        return Response(status=403)

    data = request.get_json()
    user = User.query.get(id)
    if(not user):
        return bad_request(f'User with id={id} does not exist')

    if('username' in data):
        user.username = data['username']
    db.session.commit()
    return jsonify(user.to_dict())


@bp.route('/users/role/<int:id>', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def edit_user_role(id):
    data = request.get_json()
    user = User.query.get(id)
    if(not user):
        return bad_request(f'User with id={id} does not exist')

    if('role' in data):
        try:
            user.role = Role(data['role'])
        except:
            return bad_request(f'Invalid role')
    db.session.commit()
    return jsonify(user.to_dict())


@bp.route('/users/role', methods=['GET'])
@token_auth.login_required
def get_user_roles():
    print([str(r) for r in Role])
    return jsonify([str(r) for r in Role])


@bp.route('/users/toggle_activate/<int:id>', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def desactivar(id):
    data = request.get_json()
    user = User.query.get(id)
    if(not user):
        return bad_request(f'User with id={id} does not exist')
    if(not user.token):
        return bad_request(f'User with unfinished register process')
    if(not 'active' in data):
        return bad_request(f'Active parameter required')
    user.active = data['active']
    db.session.commit()
    return jsonify(user.to_dict())


@bp.route('/users/password', methods=['PUT'])
@token_auth.login_required
def change_password():
    user = token_auth.current_user()
    data = request.get_json()
    if(len(data['password']) < 8 or len(data['password']) > 20):
        return bad_request('Invalid password. Min length:8, Max length:20')

    if(user.check_password(data['old_password'])):
        user.set_password(data['password'])
    else:
        return bad_request(f'Old password is incorrect')

    return Response(status=200)

@bp.route('/users/map', methods=['PUT'])
@token_auth.login_required
def change_map():
    user = token_auth.current_user()
    data = request.get_json()
    if(not user.map_info):
        map_info = MapInfo()
        map_info.user_id = user.id
        db.session.add(map_info)
        db.session.commit()
    map_info = user.map_info
    map_info.zoom = data['zoom']
    map_info.rotation = data['rotation']
    map_info.center_x = data['center_x']
    map_info.center_y = data['center_y']
    db.session.commit()
    return jsonify(user.to_dict())