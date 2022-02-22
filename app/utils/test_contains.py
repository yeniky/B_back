from time import time
from random import randint

zones = [
  {
    "name": "R15",
    "area": [[595, 590], [610, 755]]
  },
  {
    "name": "R14",
    "area": [[580, 590], [595, 755]]
  },
  {
    "name": "R13",
    "area": [[553, 590], [568, 755]]
  },
  {
    "name": "R12",
    "area": [[538, 590], [553, 755]]
  },
  {
    "name": "R11",
    "area": [[511, 590], [526, 755]]
  },
  {
    "name": "R10",
    "area": [[496, 590], [511, 755]]
  },
  {
    "name": "R09",
    "area": [[469, 590], [484, 755]]
  },
  {
    "name": "R08",
    "area": [[454, 590], [469, 755]]
  },
  {
    "name": "R07",
    "area": [[427, 590], [442, 755]]
  },
  {
    "name": "R06",
    "area": [[412, 590], [427, 755]]
  },
  {
    "name": "R05",
    "area": [[385, 590], [400, 755]]
  },
  {
    "name": "R04",
    "area": [[370, 590], [385, 755]]
  },
  {
    "name": "R03",
    "area": [[343, 590], [358, 755]]
  },
  {
    "name": "SS1",
    "area": [[328, 590], [343, 755]]
  },
  {
    "name": "SS2",
    "area": [[301, 590], [316, 755]]
  },
  {
    "name": "SS3",
    "area": [[286, 590], [301, 755]]
  },
  {
    "name": "SS4",
    "area": [[270, 590], [280, 755]]
  },
  {
    "name": "BL01",
    "area": [[645, 560], [740, 577]]
  },
  {
    "name": "BL02",
    "area": [[645, 577], [740, 594]]
  },
  {
    "name": "BL03",
    "area": [[645, 594], [740, 611]]
  },
  {
    "name": "BL04",
    "area": [[645, 611], [740, 628]]
  },
  {
    "name": "BL05",
    "area": [[645, 628], [740, 645]]
  },
  {
    "name": "BL06",
    "area": [[645, 645], [740, 662]]
  },
  {
    "name": "BL07",
    "area": [[645, 662], [740, 679]]
  },
  {
    "name": "BL08",
    "area": [[645, 679], [740, 696]]
  },
  {
    "name": "BL09",
    "area": [[645, 696], [740, 713]]
  },
  {
    "name": "BL10",
    "area": [[645, 713], [740, 730]]
  },
  {
    "name": "P01",
    "area": [[636, 450], [655, 550]]
  },
  {
    "name": "P02",
    "area": [[655, 450], [674, 550]]
  },
  {
    "name": "P03",
    "area": [[674, 450], [693, 550]]
  },
  {
    "name": "P04",
    "area": [[693, 450], [712, 550]]
  },
  {
    "name": "P05",
    "area": [[712, 450], [731, 550]]
  },
  {
    "name": "P06",
    "area": [[731, 450], [750, 550]]
  },
  {
    "name": "Pull Empacado",
    "area": [[661, 381], [724, 425]]
  },
  {
    "name": "Pull Tratamiento",
    "area": [[598, 381], [661, 425]]
  },
  {
    "name": "submuestreo-01",
    "area": [[767, 723], [862, 753]]
  },
  {
    "name": "submuestreo-02",
    "area": [[767, 693], [862, 723]]
  },
  {
    "name": "submuestreo-03",
    "area": [[767, 663], [862, 693]]
  },
  {
    "name": "submuestreo-04",
    "area": [[767, 633], [862, 663]]
  },
  {
    "name": "submuestreo-05",
    "area": [[767, 603], [862, 633]]
  },
  {
    "name": "submuestreo-06",
    "area": [[767, 573], [862, 603]]
  },
  {
    "name": "pesaje",
    "area": [[775, 515], [862, 550]]
  },
  {
    "name": "Push",
    "area": [[1200, 304], [1250, 380]]
  },
  {
    "name": "BR01",
    "area": [[1268, 18], [1387, 34]]
  },
  {
    "name": "BR02",
    "area": [[1268, 34], [1387, 50]]
  },
  {
    "name": "BR03",
    "area": [[1268, 50], [1387, 66]]
  },
  {
    "name": "BR04",
    "area": [[1268, 66], [1387, 82]]
  },
  {
    "name": "BR05",
    "area": [[1268, 82], [1387, 98]]
  },
  {
    "name": "BR06",
    "area": [[1268, 98], [1387, 114]]
  },
  {
    "name": "BR07",
    "area": [[1268, 114], [1387, 130]]
  },
  {
    "name": "BR08",
    "area": [[1268, 130], [1387, 146]]
  },
  {
    "name": "BR09",
    "area": [[1268, 146], [1387, 162]]
  },
  {
    "name": "BR10",
    "area": [[1268, 162], [1387, 178]]
  },
  {
    "name": "BR11",
    "area": [[1268, 178], [1387, 194]]
  },
  {
    "name": "BR12",
    "area": [[1268, 194], [1387, 210]]
  },
  {
    "name": "BR13",
    "area": [[1268, 210], [1387, 226]]
  },
  {
    "name": "BR14",
    "area": [[1268, 226], [1387, 242]]
  },
  {
    "name": "BR15",
    "area": [[1268, 242], [1387, 258]]
  },
  {
    "name": "BR16",
    "area": [[1268, 258], [1387, 274]]
  },
  {
    "name": "BR17",
    "area": [[1268, 274], [1387, 290]]
  },
  {
    "name": "BR18",
    "area": [[1268, 290], [1387, 306]]
  },
  {
    "name": "BR19",
    "area": [[1268, 306], [1387, 322]]
  },
  {
    "name": "BR20",
    "area": [[1268, 322], [1387, 338]]
  },
  {
    "name": "BR21",
    "area": [[1268, 338], [1387, 354]]
  },
  {
    "name": "BR22",
    "area": [[1268, 354], [1387, 370]]
  },
  {
    "name": "submuestreo 01",
    "area": [[1125, 130], [1180, 146]]
  },
  {
    "name": "submuestreo 02",
    "area": [[1125, 146], [1180, 162]]
  },
  {
    "name": "submuestreo 03",
    "area": [[1125, 162], [1180, 178]]
  },
  {
    "name": "submuestreo 04",
    "area": [[1125, 178], [1180, 194]]
  },
  {
    "name": "submuestreo 05",
    "area": [[1125, 194], [1180, 210]]
  },
  {
    "name": "submuestreo 06",
    "area": [[1125, 210], [1180, 226]]
  },
  {
    "name": "pesaje 02",
    "area": [[1125, 90], [1160, 120]]
  }
]

def zone_to_poly(area):
    a = area[0]
    b = area[1]
    return [
        a,
        [a[0], b[1]],
        b,
        [b[0], a[1]]
    ]

for zone in zones:
    zone['area'] = zone_to_poly(zone['area'])

# Ray tracing
def ray_tracing_method(x,y,poly):
    n = len(poly)
    inside = False

    p1x,p1y = poly[0]
    for i in range(n+1):
        p2x,p2y = poly[i % n]
        if y > min(p1y,p2y):
            if y <= max(p1y,p2y):
                if x <= max(p1x,p2x):
                    if p1y != p2y:
                        xints = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                    if p1x == p2x or x <= xints:
                        inside = not inside
        p1x,p1y = p2x,p2y

    return inside

def ray_tracing_method1(x,y,poly):
  return (poly[0][0] < x <= poly[2][0]) and (poly[0][1] < y <= poly[2][1])


def check_inside_zone(point):
    for zone in zones:
        in_zone = ray_tracing_method(point['x'],point['y'], zone['area'])
        if in_zone:
            return zone

def check_inside_zone1(point):
    for zone in zones:
        in_zone = ray_tracing_method1(point['x'],point['y'], zone['area'])
        if in_zone:
            return zone

start_time = time()
alarms = []
M = 100
print(f'probando {M} puntos...')
for i in range(M):
    point = {'x': randint(400, 800), 'y': randint(400, 900)}
    # point = {'x': 700, 'y': 400}
    zone = check_inside_zone(point)
    zone1 = check_inside_zone1(point)
    if zone != zone1:
      print('Mal')
    if zone:
        print(zone)
        alarms.append(f'element in zone {zone["name"]}')
print(f'se detectaron {len(alarms)} elementos dentro de areas')
print(f'ray tracing done in {time()-start_time}')
