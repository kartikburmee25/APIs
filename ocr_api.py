from fastapi import File, UploadFile, FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List
import pytesseract
import asyncio
import shutil
import os
import time 

def _save_file_to_server(uploaded_file, path=".", save_as="default"):
	extension = os.path.splitext(uploaded_file.filename)[-1]
	temp_file = os.path.join(path, save_as + extension)

	with open(temp_file, "wb") as buffer:
		shutil.copyfileobj(uploaded_file.file, buffer)

	return temp_file

async def read_image(img_path, lang='eng'):
	try:
		text = pytesseract.image_to_string(img_path, lang=lang)
		await asyncio.sleep(2)
		return text
	except:
		return "[ERROR] Unable to process file: {0}".format(img_path)

app = FastAPI()

@app.get("/")
def home_page():
	return {"message": "Visit the endpoint: /api/v1/extract_text to perform OCR."}

@app.post("/api/v1/extract_text")
async def extract_text(Images: List[UploadFile] = File(...)):
	response = {}
	s = time.time()
	tasks = []
	for img in Images:
		print("Image uploaded: ", img.filename)
		temp_file = _save_file_to_server(img, path="./", save_as=img.filename)
		tasks.append(asyncio.create_task(read_image(temp_file)))

	text = await asyncio.gather(*tasks)
	for i in range(len(text)):
		response[Images[i].filename] = text[i]

	response['Time Taken'] = round((time.time() - s),2)

	return response