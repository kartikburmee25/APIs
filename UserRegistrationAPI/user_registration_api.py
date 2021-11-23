from fastapi import FastAPI
import os, time, asyncio, sqlite3, smtplib
from pydantic import BaseModel
import json

class User(BaseModel):
	first_name: str
	last_name: str
	email_address: str
	username: str
	password: str
	confirm_password: str

class UserCredentials(BaseModel):
	user_name: str
	password: str

app = FastAPI()

async def send_email(email_address):

	sender = 'registration_api@api.com'
	receiver = email_address
	message = 'Congrats, You have been successfully registered'

	# dummy development smtp server
	# python -m smtpd -n -c DebuggingServer localhost:1025
	server = smtplib.SMTP('localhost:1025')
	server.sendmail(sender,receiver,message)

	return

async def save_user_to_db(user_info):

	first_name,last_name,email_address,username,password = user_info['first_name'],user_info['last_name'],user_info['email_address'],user_info['username'],user_info['password']
	values = (first_name,last_name,email_address,username,password)
	conn = sqlite3.connect('user_info.db')
	print ("Opened database successfully")
	conn.execute('''CREATE TABLE IF NOT EXISTS Users (
		UserId integer PRIMARY KEY NOT NULL,
	    FirstName varchar(255) NOT NULL,
	    LastName varchar(255) NOT NULL,
	    EmailAddress varchar(255) NOT NULL UNIQUE,
	    UserName varchar(255) NOT NULL UNIQUE,
	    Password varchar(255) NOT NULL
	);''')

	try:
		conn.execute("INSERT INTO Users (FirstName,LastName,EmailAddress,UserName,Password) \
			VALUES " + str(values) + ";")
		conn.commit()
	except:
		conn.close()
	conn.close()
	print("User info added to database")

	return

@app.post("/api/v1/register_user")
async def register_user(user_info: User):

	response = {}
	user_info = user_info.json()
	user_info = json.loads(user_info)
	tasks = []
	tasks.append(asyncio.create_task(send_email(user_info['email_address'])))
	tasks.append(asyncio.create_task(save_user_to_db(user_info)))
	await asyncio.gather(*tasks)

	return {'user_info':user_info}

@app.post("/api/v1/login")
async def login(user_credentials: UserCredentials):
	response = {}
	user_credentials = user_credentials.json()
	user_credentials = json.loads(user_credentials)
	username, password = user_credentials['username'], user_credentials['password']
	values = (first_name,last_name,email_address,username,password)
	conn = sqlite3.connect('user_info.db')
	cursor = conn.cursor()
	print ("Opened database successfully")
	try:
		query = '''SELECT Password FROM Users WHERE UserName= '{}'; '''.format(username)
		cursor.execute(query)
	except:
		conn.close()
		return {'ERROR': 'Username does not exist. Please register as new user'}

	results = cursor.fetchall()
	actual_password = results[0][0]

	if actual_password == password:
		output = {'success':'Logged in successfully'}
	else:
		output = {'ERROR':'Sorry! incorrect password. Please try again'}

	conn.close()

	return
