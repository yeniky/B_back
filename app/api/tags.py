from flask import jsonify, request
from app import db
from app.api import bp
from app.models import Tag, Container, Batch, Order, Material,\
    BinBatchAssociation, MaterialGroup, TagType, \
    MaterialPricingGroup, OrderType, Baliza, Zone, Connector
from app.api.errors import bad_request
from datetime import datetime
import pandas as pd
from app.utils.user_auth import token_auth
from app.models import Role, Status
from app.utils.helpers import build_page
from app.utils.helpers import generate_order_by

@bp.route('/containers', methods=['GET'])
@token_auth.login_required
def get_containers():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    order_by = request.args.get('order_by', "")
    order = request.args.get('order', "asc")
    query = Container.query
    if order_by:
        query = generate_order_by(query, Container, order_by,order,Container.prop_to_order)
    return jsonify(build_page(query.paginate(page, per_page, False),order_by,order, Container.to_dict))


@bp.route('/containers', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def create_container():
    data = request.get_json()
    if 'name' not in data:
        return bad_request('must include at least a name field')
    if Container.query.filter_by(name=data['name']).first():
        return bad_request('a container with that name already exists')

    new_container = Container.create_container(
        data['name'],
        data['type'],
        data['description'],
        data['batch']
    )
    db.session.commit()
    if(new_container.batch):
        BinBatchAssociation.create_new_association(
            new_container.id, new_container.batch.id, datetime.utcnow())
    return jsonify(new_container.to_dict())


@bp.route('/containers/<container_id>', methods=['GET'])
@token_auth.login_required
def get_container(container_id):
    container = Container.query.filter_by(id=container_id).first_or_404()
    return jsonify(container.to_dict())


@bp.route('/containers/<container_id>', methods=['PUT'])
@token_auth.login_required(role=[Role.Admin])
def edit_container(container_id):
    data = request.get_json()
    container = Container.query.filter_by(id=container_id).first_or_404()

    container_name = Container.query.filter_by(
        name=data['name']).first()

    if(container_name and container_name.id != container.id):
        return bad_request('a container with that name already exists')

    if request.args.get('unset_tag'):
        container.unset_tag()
        db.session.commit()
        return jsonify(container.to_dict())
    container.edit_container(data)
    if 'tag' in data:
        answer = container.set_tag(data['tag'])
        if 'error' in answer:
            return bad_request(answer)
    db.session.commit()
    return jsonify(container.to_dict())


@bp.route('/containers/<container_id>', methods=['DELETE'])
@token_auth.login_required(role=[Role.Admin])
def delete_container(container_id):
    container = Container.query.filter_by(id=container_id).first_or_404()
    db.session.delete(container)
    db.session.commit()
    return jsonify({'status': 'ok'})


@bp.route('/tag_types', methods=['GET'])
@token_auth.login_required
def get_container_types():
    return jsonify([t.to_dict() for t in TagType.query.all()])


@bp.route('/tags', methods=['GET'])
@token_auth.login_required
def get_tags():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    order_by = request.args.get('order_by', "")
    order = request.args.get('order', "asc")
    query = None
    if request.args.get('without_containers'):
        query = Tag.query.filter_by(container_id=None)
    else:
        query = Tag.query
    if order_by:
        query = generate_order_by(query, Tag, order_by,order,Tag.prop_to_order)
    query = query.paginate(page, per_page, False)
    return jsonify(build_page(query, order_by,order,Tag.to_dict))


@bp.route('/tags/<address>', methods=['GET'])
@token_auth.login_required(role=[Role.Admin])
def get_tag_by_address(address):
    tag = Tag.query.filter_by(address=address).first_or_404()
    return jsonify(tag.to_dict())


@bp.route('/tags/activate/<id>', methods=['POST'])
@token_auth.login_required
def activate_tag(id):
    active = True if request.args.get('active') == 'true' else False
    tag = Tag.query.get_or_404(id)
    tag.active = active
    db.session.commit()
    return jsonify(tag.to_dict())


@bp.route('/material', methods=['GET'])
@token_auth.login_required
def get_materials():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    order_by = request.args.get('order_by', "")
    order = request.args.get('order', "asc")
    query = Material.query
    if order_by:
        query = generate_order_by(query, Material, order_by,order,Material.prop_to_order)
    query = query.paginate(page, per_page, False)
    return jsonify(build_page(query,order_by,order, Material.to_dict))



@bp.route('/material/import', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def import_material():
    file = request.files['file']
    if file:
        try:
            data = pd.read_csv(file, dtype={
                               'Type of Reproduction': object, 'Phase': object, 'Package Type': object, 'Variety Name': object})
        except:
            return bad_request(f'File with bad format')
        required_columns = ["Material",
                            "Material Description", "Matl Group", "MPG"]
        optional_columns = ["Type of Reproduction",
                            "Phase", "Package Type", "Variety Name"]
        data.columns = data.columns.str.strip()

        data_obj = data.select_dtypes(['object'])
        data[data_obj.columns] = data_obj.apply(lambda x: x.str.strip())
        errors = []

        for c in required_columns:
            if(not c in data.columns):
                return bad_request(f'{c} is a required column')

        for index, row in data.iterrows():

            mat = Material.query.filter_by(
                name=row['Material']).first()
            if(mat):
                errors.append(
                    f'Row {index} invalid. Material with name {row["Material"]} already exists')
                continue
            mg = MaterialGroup.query.filter_by(
                name=row['Matl Group']).first()
            if(not mg):
                errors.append(
                    f'Row {index} invalid. Material group {row["Matl Group"]} does not exist')
                continue
            mpg = MaterialPricingGroup.query.filter_by(
                name=row['MPG']).first()
            if(not mpg):
                errors.append(
                    f'Row {index} invalid. Material price group {row["MPG"]} does not exist')
                continue

            material = Material(name=row['Material'],
                                material_description=row["Material Description"],
                                material_group_id=mg.id,
                                material_pricing_group_id=mpg.id)

            if("Type of Reproduction" in row and pd.notna(row['Type of Reproduction'])):
                material.reproduction_type = row['Type of Reproduction']
            if("Phase" in row and pd.notna(row['Phase'])):
                material.phase = row['Phase']
            if("Package Type" in row and pd.notna(row['Package Type'])):
                material.package_type = row['Package Type']
            if("Variety Name" in row and pd.notna(row['Variety Name'])):
                material.variety_name = row['Variety Name']
            db.session.add(material)

        db.session.commit()
        return jsonify({"status": "OK", "errors": errors})


@bp.route('/material', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def create_material():
    data = request.get_json()
    if Material.query.filter_by(name=data['name']).first():
        return bad_request('a material with that name already exists')
    mat_group = MaterialGroup.query.filter_by(
        name=data['material_group']).first()
    mat_p_group = MaterialPricingGroup.query.filter_by(
        name=data['material_price_group']).first()
    new_material = Material(
        name=data['name'],
        material_description=data['description'],
        material_group=mat_group,
        material_pricing_group=mat_p_group
    )
    if 'reproduction_type' in data:
        new_material.reproduction_type = data['reproduction_type']
    if 'phase' in data:
        new_material.phase = data['phase']
    if 'package_type' in data:
        new_material.package_type = data['package_type']
    if 'variety_name' in data:
        new_material.variety_name = data['variety_name']
    db.session.add(new_material)
    db.session.commit()
    return jsonify(new_material.to_dict())


@bp.route('/material/<id>', methods=['PUT'])
@token_auth.login_required(role=[Role.Admin])
def edit_material(id):
    data = request.get_json()
    material = Material.query.filter_by(id=id).first_or_404()
    mat_group = MaterialGroup.query.filter_by(
        name=data['material_group']).first()
    mat_p_group = MaterialPricingGroup.query.filter_by(
        name=data['material_price_group']).first()

    mat_name = Material.query.filter_by(
        name=data['name']).first()
    if(mat_name and mat_name.id != material.id):
        return bad_request('a material with that name already exists')

    material.name = data['name']
    material.material_description = data['description']
    material.material_group = mat_group
    material.material_pricing_group = mat_p_group

    if 'reproduction_type' in data:
        material.reproduction_type = data['reproduction_type']
    if 'phase' in data:
        material.phase = data['phase']
    if 'package_type' in data:
        material.package_type = data['package_type']
    if 'variety_name' in data:
        material.variety_name = data['variety_name']
    db.session.commit()
    return jsonify(material.to_dict())


@bp.route('/material_group', methods=['GET'])
@token_auth.login_required
def get_materials_group():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    order_by = request.args.get('order_by', "")
    order = request.args.get('order', "asc")
    query = MaterialGroup.query
    if order_by:
        query = generate_order_by(query, MaterialGroup, order_by,order,MaterialGroup.prop_to_order)
    query = query.paginate(page, per_page, False)
    return jsonify(build_page(query,order_by,order, MaterialGroup.to_dict))


@bp.route('/material_group', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def create_materials_group():
    data = request.get_json()
    if 'name' not in data:
        return bad_request('must include at least a name field')

    if MaterialGroup.query.filter_by(name=data['name']).first():
        return bad_request('a material group with that name already exists')
    new_mg = MaterialGroup(
        name=data['name'],
        description=data['description'],
    )
    db.session.add(new_mg)
    db.session.commit()
    return jsonify(new_mg.to_dict())


@bp.route('/material_group/<id>', methods=['PUT'])
@token_auth.login_required(role=[Role.Admin])
def edit_materials_group(id):
    data = request.get_json()
    mg = MaterialGroup.query.filter_by(id=id).first_or_404()
    matg_name = MaterialGroup.query.filter_by(
        name=data['name']).first()
    if(matg_name and matg_name.id != mg.id):
        return bad_request('a material group with that name already exists')
    if 'name' in data:

        mg.name = data['name']
    if 'description' in data:
        mg.description = data['description']
    db.session.commit()
    return jsonify(mg.to_dict())


@ bp.route('/material_group/import', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def import_material_group():
    file = request.files['file']
    if file:
        try:
            data = pd.read_csv(file)
        except:
            return bad_request(f'File with bad format')
        required_columns = ["Material Group",
                            "Matl Grp Desc."]
        optional_columns = []
        data.columns = data.columns.str.strip()

        data_obj = data.select_dtypes(['object'])
        data[data_obj.columns] = data_obj.apply(lambda x: x.str.strip())
        errors = []

        for c in required_columns:
            if(not c in data.columns):
                return bad_request(f'{c} is a required column')

        for index, row in data.iterrows():

            mat = MaterialGroup.query.filter_by(
                name=row['Material Group']).first()
            if(mat):
                errors.append(
                    f'Row {index} invalid. Material Group with name {row["Material Group"]} already exists')
                continue

            material_group = MaterialGroup(name=row['Material Group'],
                                           description=row["Matl Grp Desc."])
            db.session.add(material_group)

        db.session.commit()
        return jsonify({"status": "OK", "errors": errors})


@ bp.route('/material_price', methods=['GET'])
@token_auth.login_required
def get_materials_price():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    order_by = request.args.get('order_by', "")
    order = request.args.get('order', "asc")
    query = MaterialPricingGroup.query
    if order_by:
        query = generate_order_by(query, MaterialPricingGroup, order_by,order,MaterialPricingGroup.prop_to_order)
    query = query.paginate(page, per_page, False)
    return jsonify(build_page(query,order_by,order, MaterialPricingGroup.to_dict))


@ bp.route('/material_price', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def create_materials_price():
    data = request.get_json()
    if 'name' not in data:
        return bad_request('must include at least a name field')
    if MaterialPricingGroup.query.filter_by(name=data['name']).first():
        return bad_request('a material price group with that name already exists')
    new_mpg = MaterialPricingGroup(
        name=data['name'],
        description=data['description'],
    )
    db.session.add(new_mpg)
    db.session.commit()
    return jsonify(new_mpg.to_dict())


@bp.route('/material_price/<id>', methods=['PUT'])
@token_auth.login_required(role=[Role.Admin])
def edit_materials_price(id):
    data = request.get_json()
    mg = MaterialPricingGroup.query.filter_by(id=id).first_or_404()
    matg_name = MaterialPricingGroup.query.filter_by(
        name=data['name']).first()
    if(matg_name and matg_name.id != mg.id):
        return bad_request('a material price group with that name already exists')
    if 'name' in data:
        mg.name = data['name']
    if 'description' in data:
        mg.description = data['description']
    db.session.commit()
    return jsonify(mg.to_dict())


@ bp.route('/material_price/import', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def import_material_price():
    file = request.files['file']
    if file:
        try:
            data = pd.read_csv(file)
        except:
            return bad_request(f'File with bad format')
        required_columns = ["MPG",
                            "MPG Description"]
        optional_columns = []
        data.columns = data.columns.str.strip()

        data_obj = data.select_dtypes(['object'])
        data[data_obj.columns] = data_obj.apply(lambda x: x.str.strip())
        errors = []

        for c in required_columns:
            if(not c in data.columns):
                return bad_request(f'{c} is a required column')

        for index, row in data.iterrows():

            mat = MaterialPricingGroup.query.filter_by(
                name=row['MPG']).first()
            if(mat):
                errors.append(
                    f'Row {index} invalid. Material Price Group with name {row["MPG"]} already exists')
                continue

            material_group = MaterialPricingGroup(name=row['MPG'],
                                                  description=row["MPG Description"])
            db.session.add(material_group)

        db.session.commit()
        return jsonify({"status": "OK", "errors": errors})


@ bp.route('/batch', methods=['GET'])
@token_auth.login_required
def get_batchs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    order_by = request.args.get('order_by', "")
    order = request.args.get('order', "asc")
    query = Batch.query
    if order_by:
        query = generate_order_by(query, Batch, order_by,order,Batch.prop_to_order)
    query = query.paginate(page, per_page, False)
    return jsonify(build_page(query,order_by,order, Batch.to_dict))


@ bp.route('/batch', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def create_batch():
    data = request.get_json()
    if Batch.query.filter_by(name=data['name']).first():
        return bad_request('a batch with that name already exists')

    order = Order.query.filter_by(name=data['order']).first()
    new_batch = Batch(
        name=data['name'],
        type=data['type'],
        order=order
    )
    db.session.add(new_batch)
    if 'containers' in data['containers']:
        for container_id in data['containers']:
            cnt = Container.query.filter_by(id=container_id).first()
            if cnt:
                cnt.batch = new_batch
                BinBatchAssociation.create_new_association(
                    cnt.id, new_batch.id, datetime.utcnow())

    db.session.commit()
    return jsonify(new_batch.to_dict())


@ bp.route('/batch/<id>', methods=['PUT'])
@token_auth.login_required(role=[Role.Admin])
def edit_batch(id):
    data = request.get_json()
    batch = Batch.query.filter_by(id=id).first_or_404()
    old_batch = Batch.query.filter_by(name=data['name']).first()

    if(old_batch and old_batch.id != batch.id):
        return bad_request('a batch with that name already exists')

    batch.name = data['name']
    batch.type = data['type']

    if 'order' in data and data['order'] != '':
        order = Order.query.filter_by(name=data['order']).first()
        batch.order = order

    if 'containers' in data:
        to_close = []
        for current_container in batch.containers:
            to_close.append(current_container)

        for container in to_close:
            if(container.id in data['containers']):
                continue
            container.batch = None
            BinBatchAssociation.close_association(container.id,
                                                  batch.id, datetime.utcnow())

        for container_id in data['containers']:
            cnt = Container.query.filter_by(id=container_id).first()
            if cnt:
                if(not cnt in batch.containers):
                    cnt.batch = batch
                    BinBatchAssociation.create_new_association(
                        container_id, batch.id, datetime.utcnow())

    db.session.commit()
    return jsonify(batch.to_dict())


@ bp.route('/batch/activate/<id>', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def activate_batch(id):
    active = True if request.args.get('active') == 'true' else False
    batch = Batch.query.get_or_404(id)
    batch.active = active
    db.session.commit()
    return jsonify(batch.to_dict())


@ bp.route('/orders', methods=['GET'])
@token_auth.login_required
def get_orders():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    order_by = request.args.get('order_by', "")
    order = request.args.get('order', "asc")
    query = Order.query
    if order_by:
        query = generate_order_by(query, Order, order_by,order,Order.prop_to_order)
    query = query.paginate(page, per_page, False)
    print(build_page(query,order_by,order, Order.to_dict))
    return jsonify(build_page(query,order_by,order, Order.to_dict))


@ bp.route('/orders', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def create_order():
    data = request.get_json()
    if Order.query.filter_by(name=data['name']).first():
        return bad_request('a order with that name already exists')

    type = OrderType.query.filter_by(name=data['type']).first()
    material = Material.query.filter_by(name=data['material']).first()
    new_order = Order(
        name=data['name'],
        order_type=type,
        material=material
    )
    if 'start_date' in data and data['start_date']:
        new_order.date_start = datetime.strptime(
            data['start_date'], "%Y-%m-%d")
    if 'end_date' in data and data['end_date']:
        new_order.date_finish = datetime.strptime(data['end_date'], "%Y-%m-%d")
    if 'agreement' in data:
        new_order.agreement = data['agreement']
    if 'purch_doc' in data:
        new_order.purch_doc = data['purch_doc']

    db.session.add(new_order)
    db.session.commit()
    return jsonify(new_order.to_dict())


@ bp.route('/order/import', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def import_order():
    file = request.files['file']
    if file:
        try:
            data = pd.read_csv(
                file, dtype={'Purch.doc': object, 'Agreement': object})
        except:
            return bad_request(f'File with bad format')

        required_columns = ["Order", "Plnt",
                            "Ord Type", "Crop Year", "Material"]
        optional_columns = ["Agreement",
                            "Purch.doc", "F. Inicio", "F. Termino"]
        data.columns = data.columns.str.strip()

        errors = []
        data_obj = data.select_dtypes(['object'])
        data[data_obj.columns] = data_obj.apply(lambda x: x.str.strip())

        for c in required_columns:
            if(not c in data.columns):
                return bad_request(f'{c} is a required column')

        for index, row in data.iterrows():

            old_order = Order.query.filter_by(
                name=row['Order']).first()
            if(old_order):
                errors.append(
                    f'Row {index} invalid. Order with name {row["Order"]} already exists')
                continue

            material = Material.query.filter_by(
                name=row['Material']).first()
            if(not material):
                errors.append(
                    f'Row {index} invalid. Material {row["Material"]} does not exist')
                continue

            order_type = OrderType.query.filter_by(
                name=row['Ord Type']).first()
            if(not order_type):
                errors.append(
                    f'Row {index} invalid. Order Type {row["Ord Type"]} does not exist')
                continue

            order = Order(name=row['Order'],
                          order_type=order_type,
                          material=material,
                          crop_year=row['Crop Year'],
                          plant=row['Plnt'])

            if("Agreement" in row and pd.notna(row['Agreement'])):
                order.agreement = row['Agreement']
            if("F. Inicio" in row and pd.notna(row['F. Inicio'])):
                try:
                    date = datetime.strptime(
                        row['F. Inicio'], "%Y-%m-%d")
                except:
                    errors.append(
                        f'Row {index} invalid. F. Inicio with invalid format')
                    continue
                order.date_start = date

            if("F. Termino" in row and pd.notna(row['F. Termino'])):
                try:
                    date = datetime.strptime(
                        row['F. Termino'], "%Y-%m-%d")
                except:
                    errors.append(
                        f'Row {index} invalid. F. Termino with invalid format')
                    continue
                order.date_finish = date

            if("Purch.doc" in row and pd.notna(row['Purch.doc'])):
                order.purch_doc = row['Purch.doc']
            db.session.add(material)

        db.session.commit()
        return jsonify({"status": "OK", "errors": errors})


@ bp.route('/orders/<id>', methods=['PUT'])
@token_auth.login_required(role=[Role.Admin])
def edit_order(id):
    data = request.get_json()
    order = Order.query.filter_by(id=id).first_or_404()

    old_order = Order.query.filter_by(name=data['name']).first()
    if(old_order and old_order.id != order.id):
        return bad_request('a order with that name already exists')

    type = OrderType.query.filter_by(name=data['type']).first()
    material = Material.query.filter_by(name=data['material']).first()

    order.name = data['name']
    order.order_type = type
    order.material = material

    if 'start_date' in data:
        if(not data['start_date']):
            order.date_start = None
        else:
            order.date_start = datetime.strptime(
                data['start_date'], "%Y-%m-%d")
    if 'end_date' in data:
        if(not data['end_date']):
            order.date_finish = None
        else:
            order.date_finish = datetime.strptime(
                data['end_date'], "%Y-%m-%d")
    if 'agreement' in data:
        order.agreement = data['agreement']
    if 'purch_doc' in data:
        order.purch_doc = data['purch_doc']

    if 'batches' in data:
        for batch_id in data['batches']:
            b = Batch.query.filter_by(id=batch_id).first()
            if(b.order):
                return bad_request('Batch {} belongs to another order'.format(b.name))

            b.order = order

    db.session.commit()
    return jsonify(order.to_dict())


@ bp.route('/orders/activate/<id>', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def activate_order(id):
    active = True if request.args.get('active') == 'true' else False
    order = Order.query.get_or_404(id)
    order.active = active
    db.session.commit()
    return jsonify(order.to_dict())


@ bp.route('/order_types', methods=['GET'])
@token_auth.login_required
def get_order_types():
    return jsonify([t.to_dict() for t in OrderType.query.all()])

@ bp.route('/connectors', methods=['GET'])
@token_auth.login_required
def get_connectors():
    return jsonify([c.to_dict() for c in Connector.query.all()])

@ bp.route('/balizas', methods=['GET'])
@token_auth.login_required
def get_balizas():
    return jsonify([b.to_dict() for b in Baliza.query.all()])

@ bp.route('/balizas/<id>', methods=['PUT'])
@token_auth.login_required
def edit_balizas(id):
    data = request.get_json()
    baliza = Baliza.query.filter_by(id=id).first_or_404()
    if not baliza.connector.active:
        return bad_request("Baliza must be active for edit")
    if('zone_name' not in data):
        baliza.zone = None
    else:
        zone_name = data['zone_name']
        zone = Zone.query.filter_by(name=zone_name).first()
        if(not zone):
            return bad_request("A zone with that name doesn't exist")
        baliza.zone = zone
    db.session.commit()
    return jsonify(baliza.to_dict())

@ bp.route('/balizas/deactivate/<id>', methods=['POST'])
@token_auth.login_required
def offline_baliza(id):
    baliza = Baliza.query.filter_by(id=id).first_or_404()
    baliza.connector.active = False
    db.session.commit()
    return jsonify(baliza.to_dict())

@ bp.route('/balizas/activate/<id>', methods=['POST'])
@token_auth.login_required
def online_baliza(id):
    baliza = Baliza.query.filter_by(id=id).first_or_404()
    baliza.connector.active = True
    db.session.commit()
    return jsonify(baliza.to_dict())