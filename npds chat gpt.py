import numpy as np
import cv2
import imutils
import pytesseract as tess
import time
import firebase_admin
from firebase_admin import credentials, firestore
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Set Tesseract OCR path
tess.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Load image
image = cv2.imread('Toretto/car2.jpg')
if image is None:
    print("Error: Image not loaded.")
    exit()

# Resize image
image = imutils.resize(image, width=500)
cv2.imshow("Original Image", image)

# Preprocess for license plate detection
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
gray = cv2.bilateralFilter(gray, 11, 17, 17)
edged = cv2.Canny(gray, 50, 200)

# Find contours
(cnts, _) = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:30]

NumberPlateCnt = None

# Iterate through contours and find the one with 4 corners
for c in cnts:
    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.02 * peri, True)
    if len(approx) == 4:
        NumberPlateCnt = approx
        break

# Draw contours on the image
cv2.drawContours(image, [NumberPlateCnt], -1, (0, 255, 0), 3)
cv2.imshow("Final Image With Number Plate Detected", image)

# Create a mask to extract the number plate
mask = np.zeros(gray.shape, np.uint8)
new_image = cv2.drawContours(mask, [NumberPlateCnt], 0, 255, -1)
new_image = cv2.bitwise_and(image, image, mask=mask)

# Perform OCR on the number plate
config = ('-l eng --oem 1 --psm 3')
text = tess.image_to_string(new_image, config=config).strip()

print('Vehicle Number is:', text)

# Firebase
cred = credentials.Certificate("path/to/your/serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Get owner information from Firebase based on the vehicle number
result = db.collection('info').document('C7jIqYsBCtFxmWh6eSEX').get()
result = result.to_dict()
owner_info = result.get(text, "Owner information not found.")

print('This Vehicle belongs to:', owner_info)

# Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'path/to/your/keys.json'

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

SPREADSHEET_ID = 'your_spreadsheet_id'

service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()

# Find the next empty row in the spreadsheet
result1 = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="info!A:A").execute()
values = result1.get('values')
next_row = str(len(values) + 1)

# Update the spreadsheet with date, vehicle number, and owner information
date = time.asctime(time.localtime(time.time()))
data_to_update = [[date, text, owner_info]]
range_to_update = f"info!A{next_row}:C{next_row}"

result2 = sheet.values().update(
    spreadsheetId=SPREADSHEET_ID,
    range=range_to_update,
    valueInputOption="USER_ENTERED",
    body={"values": data_to_update}
).execute()

# Close OpenCV windows
cv2.waitKey(0)
cv2.destroyAllWindows()
