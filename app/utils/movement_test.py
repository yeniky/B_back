import random
import requests
import decimal
from time import sleep
from datetime import datetime

# curl --data "POS,0,ABCD,100,150,0.6,50,xE5" https://localhost:5000/api/positions


def get_coord_R15_R14():
    return ['{}'.format(decimal.Decimal(random.randrange(595, 610))),
            '{}'.format(decimal.Decimal(random.randrange(590, 755))),
            random.randrange(2)]


def get_coord_R03():
    return ['{}'.format(decimal.Decimal(random.randrange(343, 358))),
            '{}'.format(decimal.Decimal(random.randrange(590, 755))),
            random.randrange(2)]


start = datetime.utcnow()
for _ in range(1):
    address = 'alpha'
    address_2 = 'beta'
    address_3 = 'theta'
    cords = get_coord_R03()
    cords_2 = get_coord_R15_R14()
    cords_3 = get_coord_R03()
    payload = f"POS,0,{address},{cords[0]},{cords[1]},{cords[2]}.6,50,xE5\n" \
              f"POS,0,{address_2},{cords_2[0]},{cords_2[1]},{cords_2[2]}.6,50,xE5\n"\
              f"POS,0,{address_3},{cords_3[0]},{cords_3[1]},{cords_3[2]}.6,50,xE5"
    requests.post('http://127.0.0.1:5000/api/positions', data=payload)
    # sleep(1)
