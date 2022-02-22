import unittest
from app import create_app, db
from app.models import Position, Tag, Container
from app.utils.helpers import Utils
from datetime import datetime
from config import Config


class TestConfig(Config):
    TESTING = True
    # SQLALCHEMY_DATABASE_URI = 'mssql+pymssql://SA:Entretanto123@159.89.36.142/testDB'
    SQLALCHEMY_DATABASE_URI = 'sqlite://'


class DatabaseCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_db(self):
        new_pos = Position(
            timestamp=datetime.utcnow(),
            battery=99,
            signal=10,
            x=-100.12345,
            y=10.22,
            z=0.5
        )
        db.session.add(new_pos)
        db.session.commit()

        assert new_pos in db.session

    def test_relationships(self):
        new_container = Container.create_container("test-container", code="AAA", description="test-container")
        db.session.commit()

        new_tag = Tag.create_tag(address="AAAA", container=new_container)
        db.session.commit()

        self.assertEqual(new_container.tag, new_tag)
        pos_data = {
            'battery': 10,
            'signal': 99,
            'x': 1.02,
            'y': -4.2,
            'z': 0,
            'zone': 'general',
        }
        new_pos = new_tag.new_position(**pos_data)
        self.assertEqual(new_tag.positions[0], new_pos)

    def test_location_message(self):
        Tag.create_tag(address="9C85")
        db.session.commit()

        # message parsing
        pos_data = "POS,0,9C85,-0.99,-0.55,0.26,50,xE5"  # trama enviada desde dispositivo
        data = Utils.parse_message(pos_data)
        self.assertEqual(data, {
            "addr": "9C85",
            "x": -0.99,
            "y": -0.55,
            "z": 0.26,
            "signal": 50.0
        })

        # invalid data
        new_pos = Position.create("POS,0,9C85,-0.55,0.26,50")
        self.assertEqual(new_pos, None)

        # registered TAG
        new_pos = Position.create(pos_data)
        self.assertEqual(new_pos.x, -0.99)
        self.assertEqual(new_pos.y, -0.55)

        # new TAG
        pos_data = "POS,0,AAAA,-0.49,-0.25,0.26,50,xE5"
        new_pos = Position.create(pos_data)
        self.assertEqual(new_pos.tag.address, "AAAA")
        self.assertEqual(new_pos.x, -0.49)
        db.session.commit()

        # get last position of new TAG
        other_tag = Tag.query.filter_by(address="AAAA").first()
        last_pos = other_tag.last_position
        self.assertEqual(last_pos['x'], new_pos.to_dict()['x'])

        # check if tag in correct zone - in an area
        pos_data = "POS,0,WXYZ,700,400,0.6,50,xE5"
        new_pos = Position.create(pos_data)
        self.assertEqual(new_pos.zone, "Pull Empacado")


    def test_api(self):
        client = self.app.test_client()

        # post new position
        answer = client.post('/api/positions', data="POS,0,ABCD,-0.42,-0.256,0.6,50,xE5").get_json()
        self.assertEqual(answer['tag'], "ABCD")

        # check all tags
        answer = client.get('/api/tags').get_json()
        self.assertEqual(len(answer), 1)
        self.assertEqual(answer[0]['address'], "ABCD")

        client.post('/api/positions', data='POS,0,AAAA,-0.42,-0.256,0.6,50,xE5')
        answer = client.get('/api/tags').get_json()
        self.assertEqual(len(answer), 2)
        self.assertEqual(answer[1]['address'], "AAAA")

        # check tag exists
        rv = client.get('/api/tags/AAAA').get_json()
        self.assertEqual(rv['address'], "AAAA")

        # new container
        new_container = client.post('/api/containers', json={
            'name': 'test-container',
            'code': 'AAAA',
            'description': 'testostecontainer',
            'batch': ''
        }).get_json()
        self.assertEqual(new_container['name'], "test-container")

        answer = client.get('/api/containers').get_json()
        self.assertEqual(len(answer), 1)

        # container-tag pairing
        answer = client.put(f'/api/containers/{new_container["id"]}', json={
            'tag': 'AAAA'
        }).get_json()
        self.assertEqual(answer['tag'], 'AAAA')

        # multiple container-tag tests --
        client.post('/api/positions', data='POS,0,BBBB,-0.42,-0.256,0.6,50,xE5')
        second_container = client.post('/api/containers', json={
            'name': 'second-test-container',
            'code': 'BBBB',
            'description': 'another container on the wall',
            'batch': ''
        }).get_json()

        # tag already paired with another container
        answer = client.put(f'/api/containers/{second_container["id"]}', json={
            'tag': 'AAAA'
        })
        self.assertEqual(answer.status_code, 400)
        self.assertIn('error', answer.get_json())

        # container already paired with a tag
        answer = client.put(f'/api/containers/{new_container["id"]}', json={
            'tag': 'BBBB'
        })
        self.assertEqual(answer.status_code, 400)
        self.assertIn('error', answer.get_json())

        # delete container
        client.delete(f'/api/containers/{second_container["id"]}')
        answer = client.get(f'/api/containers/{second_container["id"]}')
        self.assertEqual(answer.status_code, 404)
        answer = client.get('/api/containers').get_json()
        self.assertEqual(len(answer), 1)
        answer = client.get(f'/api/tags/BBBB').get_json()
        self.assertEqual('', answer['container'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
