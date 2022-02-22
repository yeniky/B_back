import math
from math import sqrt
import decimal
from sqlalchemy_utils import get_hybrid_properties
from sqlalchemy import asc
# from sqlalchemy import desc, nullslast
from sqlalchemy import desc
import requests

def send_baliza_message(baliza,ip, message):
    payload = f'{baliza},{message}'
    print(f'Message to baliza {baliza} with IP {ip}: {message}')
    # try:
    #     requests.post(f'http://{ip}/do', data=payload)
    # except e:
    #     print(e)
    #     print(f'Error sending message to {baliza}')
    
    
def generate_order_by(query, table, order_by_str,order,order_transf,with_join=True):
    
    order_by  = order_transf(order_by_str)
    join_tables, order_column = get_column(table, order_by)
    if(join_tables is not None and with_join):
        query = query.join(*join_tables, isouter=True)
    if(order_column is not None):
        if(order != "asc"):
            # query = query.order_by(nullslast(desc(order_column)))
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(order_column)
            # query = query.order_by(nullslast(order_column))

    return query


def get_column(table, order_by):
    elems = order_by.split('.')
    if len(elems) == 1:
        if elems[0] in table.__table__.columns.keys():
            return (None, table.__table__.columns[elems[0]])
        hybrids = get_hybrid_properties(table)
        if elems[0] in hybrids.keys():
            return (None, getattr(table,elems[0]))
        
    current_table = table
    join_tables = []
    if len(elems) > 1:
        for i in range(len(elems)-1):
            if(elems[i] in current_table.__mapper__.relationships.keys()):

                join_table = current_table.__mapper__.relationships[elems[i]].mapper.class_
                current_table = join_table
                join_tables.append(current_table)

                if(i+1 == len(elems)-1):
                    join_table_columns = join_table.__table__.columns
                    if elems[i+1] in join_table_columns.keys():
                        return (join_tables, join_table_columns[elems[i+1]])

    return (None, None)

def build_page(page,order_by,order, mapper=None):
    items = page.items
    return {'items':list(flatten_list([mapper(i) for i in items])) , 'page': page.page, 'per_page': page.per_page, 'has_next': page.has_next, 'total_pages': page.pages, 'total': page.total,'order_by': order_by, 'order': order}

def flatten_list(array):
    for element in array:
        if isinstance(element, list):
            yield from flatten_list(element)
        else:
            yield element

def transformation_cords(x, y):
    x_offset = 984
    y_offset = 505
    scale = 8.5
    return (x*scale+x_offset, y*scale+y_offset)
    # return (x, y)


def inverse_transformation_cords(x, y):
    x_offset = 984
    y_offset = 505
    scale = decimal.Decimal(8.5)
    return ((x-x_offset)/scale, (y-y_offset)/scale)

# def ray_tracing_method(x, y, poly):
#     n = len(poly)
#     inside = False

#     p1x, p1y = poly[0]
#     for i in range(n + 1):
#         p2x, p2y = poly[i % n]
#         if y > min(p1y, p2y):
#             if y <= max(p1y, p2y):
#                 if x <= max(p1x, p2x):
#                     if p1y != p2y:
#                         xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
#                     if p1x == p2x or x <= xints:
#                         inside = not inside
#         p1x, p1y = p2x, p2y
#     return inside


def ray_tracing_method(x, y, zone):
    return (zone.min_x < x <= zone.max_x) and (zone.min_y < y <= zone.max_y)


class Utils:
    @staticmethod
    def parse_message(message: str):
        parsed_message = message.split(",")
        if len(parsed_message) != 8:
            return "invalid message"
        x = float(parsed_message[3])
        y = float(parsed_message[4])
        z = float(parsed_message[5])
        if math.isnan(x) or math.isnan(y) or math.isnan(z):
            return "invalid message"
        parsed_cords = transformation_cords(x, y)
        return {
            "addr": parsed_message[2],
            "x": parsed_cords[0],
            "y": parsed_cords[1],
            "z": z,
            "signal": float(parsed_message[6])
        }
    
    @staticmethod
    def parse_connector(message: str):
        parsed_message = message.split("\n")
        if len(parsed_message) != 6:
            return "invalid message"
        [mac_str,mac] = parsed_message[0].split(':')
        [ip_str,ip] = parsed_message[1].split(':')
        [ios_str,ios] = parsed_message[2].split(':')
        [fw_v_str,fw_version] = parsed_message[3].split(':')
        [hw_v_str,hw_version] = parsed_message[4].split(':')
        [hw_n_str,hw_name] = parsed_message[5].split(':')

        if(mac_str!='MAC' or ip_str!='IP'or ios_str!='IOs'or fw_v_str!='FW Version'or hw_v_str!='HW Version'or hw_n_str!='HW Name'):
            return "invalid message"
       
        return {
            "mac": mac,
            "ip": ip,
            'ios': int(ios),
            'fw_version': fw_version,
            'hw_version':hw_version,
            'hw_name': hw_name
        }

    @staticmethod
    def zone_to_poly(area):
        a = area[0]
        b = area[1]
        return [
            a,
            [a[0], b[1]],
            b,
            [b[0], a[1]]
        ]

    @staticmethod
    def check_zones(point, zones):
        for zone in zones:
            in_zone = ray_tracing_method(point[0], point[1], zone)
            if in_zone:
                return zone
        return None

    @staticmethod
    def get_distance(p1_x, p1_y, p2_x, p2_y):
        x, y = inverse_transformation_cords(p1_x, p1_y)
        x1, y1 = inverse_transformation_cords(p2_x, p2_y)
        return sqrt((x - x1)**2 + (y - y1)**2)
