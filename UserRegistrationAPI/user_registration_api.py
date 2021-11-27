from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import os, time, asyncio, sqlite3, smtplib
from pydantic import BaseModel
import json
from passlib.context import CryptContext
from authentication import (get_hashed_password,verify_password,create_access_token)

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
	first_name: str
	last_name: str
	email_address: str
	username: str
	password: str
	disabled: bool

class UserCredentials(BaseModel):
	username: str
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

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
        print(username,token_data)
    except JWTError:
        raise credentials_exception

    print(token_data.username)
    user = get_user('user_info.db', username=token_data.username)
    print(user)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user[-1] == 'True':
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_user(db, username):

	conn = sqlite3.connect('user_info.db')
	cursor = conn.cursor()
	print ("Opened database successfully")
	try:
		query = '''SELECT Password FROM Users WHERE UserName= '{}'; '''.format(username)
		print(query)
		cursor.execute(query)
		results = cursor.fetchall()
		print(results)
		if len(results)==0:
			raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
	except:
		conn.close()
		return False

	user = results[0]

	return user

async def save_user_to_db(user_info):

	first_name,last_name,email_address,username = user_info['first_name'],user_info['last_name'],user_info['email_address'],user_info['username']
	password = get_hashed_password(user_info['password'])
	values = (first_name,last_name,email_address,username,password)
	conn = sqlite3.connect('user_info.db')
	print ("Opened database successfully")
	conn.execute('''CREATE TABLE IF NOT EXISTS Users (
		UserId integer PRIMARY KEY NOT NULL,
	    FirstName varchar(255) NOT NULL,
	    LastName varchar(255) NOT NULL,
	    EmailAddress varchar(255) NOT NULL UNIQUE,
	    UserName varchar(255) NOT NULL UNIQUE,
	    Password varchar(255) NOT NULL,
	    Disabled boolean DEFAULT FALSE
	);''')

	try:
		conn.execute("INSERT INTO Users (FirstName,LastName,EmailAddress,UserName,Password) \
			VALUES " + str(values) + ";")
		conn.commit()
		output = {'status':'ok', 'message':'User info added to database'}
	except:
		output = {'status':'error', 'message':'Unable to register, Please check user details'}
	finally:
		conn.close()

	return output

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

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):

	is_valid_user = False
	username = form_data.username
	password = form_data.password
	conn = sqlite3.connect('user_info.db')
	cursor = conn.cursor()
	print ("Opened database successfully")
	try:
		query = '''SELECT Password FROM Users WHERE UserName='{}'; '''.format(username)
		#query = '''SELECT * FROM Users;'''
		print(query)
		cursor.execute(query)
		results = cursor.fetchall()
		print(results)
		if len(results)==0:
			raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
	except:
		conn.close()
		return {'status':'Error', 'message':'Username does not exist. Please register as new user'}

	actual_password = results[0][0]
	print(actual_password)

	if verify_password(password, actual_password):
		output = {'status':'ok', 'message': 'Logged in successfully'}
		is_valid_user = True
	else:
		output = {actual_password:password,'status':'Error', 'message':'Sorry! incorrect password. Please try again'}
		raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
	conn.close()

	if is_valid_user:
		access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
		access_token = create_access_token(
		data={"sub": form_data.username}, expires_delta=access_token_expires
		)
		return {"access_token": access_token, "token_type": "bearer"}

	return output


@app.get("/api/v1/users/me/")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return {'user':current_user}


