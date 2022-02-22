import random, string, requests

# curl --data "POS,0,ABCD,100,150,0.6,50,xE5" https://localhost:5000/api/positions

def randomword(length):
   letters = string.ascii_lowercase + string.ascii_uppercase
   return ''.join(random.choice(letters) for i in range(length))

def get_coord():
    return [random.randrange(1400), random.randrange(773), random.randrange(10)]

for _ in range(5):
    address = randomword(10)
    cords = get_coord()
    payload = f"POS,0,{address},{cords[0]},{cords[1]},{cords[2]}.6,50,xE5"
    print(payload)
    requests.post('http://localhost:5000/api/positions', data=payload)