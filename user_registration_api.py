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

app = FastAPI()

async def send_email(email_address):

	sender = 'registeration_api@api.com'
	receiver = email_address
	message = 'Congrats, You have been successfully registered'

	server = smtplib.SMTP('localhost:1025')
	server.sendmail(sender,receiver,message)

	return

async def save_user_to_db(user_info):

	first_name,last_name,email_address,username,password = user_info['first_name'],user_info['last_name'],user_info['email_address'],user_info['username'],user_info['password']
	values = (first_name,last_name,email_address,username,password)
	conn = sqlite3.connect('user_info.db')
	print ("Opened database successfully")
	conn.execute('''CREATE TABLE IF NOT EXISTS Users (
		UserId int,
	    FirstName varchar(255),
	    LastName varchar(255),
	    EmailAddress varchar(255),
	    UserName varchar(255),
	    Password varchar(255),
	    PRIMARY KEY (UserID)
	);''')

	conn.execute("INSERT INTO Users (FirstName,LastName,EmailAddress,UserName,Password) \
		VALUES " + str(values) + ";")
	conn.commit()
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
