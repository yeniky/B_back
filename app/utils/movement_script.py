import random
import requests
import decimal
from time import sleep
from datetime import datetime
import numpy as np
import decimal
# curl --data "POS,0,ABCD,100,150,0.6,50,xE5" https://localhost:5000/api/positions


def inverse_transformation_cords(x, y):
    x_offset = 984
    y_offset = 505
    scale = decimal.Decimal(8.5)
    return ((x-x_offset)/scale, (y-y_offset)/scale)


def build_path():

    # min_x = 420
    # max_x = 615
    # min_y = 400
    # max_y = 630

    # min_x = 930
    # max_x = 1190
    # min_y = 425
    # max_y = 723

    min_x = 1225
    max_x = 1327
    min_y = 55
    max_y = 338

    line3 = [[x, max_y]
             for x in np.linspace(min_x, max_x, num=8, endpoint=False)]
    line2 = [[max_x, y]
             for y in np.linspace(max_y, min_y, num=8, endpoint=False)]
    line1 = [[x, min_y]
             for x in np.linspace(max_x, min_x, num=8, endpoint=False)]
    line4 = [[min_x, y]
             for y in np.linspace(min_y, max_y, num=8)]
    return line3+line2+line1+line4


def generate_positions(positions):
    for x in positions:
        pos = create_pos('A123', x[0], x[1])
        print(pos)
        requests.post('http://127.0.0.1:5000/api/positions', data=pos)
        sleep(6)


def create_pos(address, x, y):
    (xp, yp) = inverse_transformation_cords(
        decimal.Decimal(x), decimal.Decimal(y))
    return f"POS,0,{address},{xp},{yp},{0}.6,50,xE5"


path = build_path()
print([x[0] for x in path])
print([x[1] for x in path])
while(True):
    generate_positions(path)
    sleep(60)
