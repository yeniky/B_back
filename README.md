# bayer-backend

## installation instructions

Clone the repo and create a virtual enviroment, after that just run:
`$ pip install -r requirements.txt`

running the server:

`$python server.py`

## Server first time run

When the server starts, the local db must be created and the models loaded, to do that go to the following address:
`http://localhost:5000/debug/first_time`
the message 'DONE' will be returned after some minutes, indicating that everything run successfully.

## Admin view

To check the data and a quick glance at the relations on the db, you can check the following address:
`http://localhost:5000/admin`
