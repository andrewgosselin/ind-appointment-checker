#!/opt/anaconda3/bin/python3
import getpass
import smtplib
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time
import os
import threading
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import enquiries
import json
from datetime import datetime
from time import gmtime, strftime

from dotenv import load_dotenv
load_dotenv()

category = os.getenv("CATEGORY")
smtp_host = os.getenv("SMTP_HOST")
smtp_port = int(os.getenv("SMTP_PORT"))
smtp_email = os.getenv("SMTP_EMAIL")
smtp_password = os.getenv("SMTP_PASSWORD")
interval_time = int(os.getenv("INTERVAL")) * 60
months_out = int(os.getenv("MONTHS_OUT"))

results = {}

with open('categories.json', 'r') as f:
    categories_json = json.load(f)

try:
    server = smtplib.SMTP(smtp_host, smtp_port)
    server.starttls()
    server.login(smtp_email, smtp_password)
    print("\nSMTP Login Successful!")
except:
    print("\nERROR: SMTP credentials are incorrect.")
    exit()

print("\n")
categories = categories_json.keys()
category = enquiries.choose('Choose one of these options: ', categories)

def loop():
    checkAvailability()

def startTimer():
    threading.Timer(interval_time, startTimer).start()
    loop()

def sendEmail(category, results):
    html = open("email.html").read()
    text = ""

    for month in results.keys():
        text += f"""
            <div>
                <h3>{month}</h2>
                <div>
        """

        text += ", ".join(map(str, results[month]))
            
        text += "</div></div>"

    msg = MIMEText(html, 'html')
    msg['From'] = smtp_email
    msg['To'] = smtp_email
    msg['Subject'] = f"[IND] {category} - New Appointments Available"

    server = smtplib.SMTP(smtp_host, smtp_port)
    server.starttls()
    server.login(smtp_email, smtp_password)
    server.sendmail(smtp_email, smtp_email, msg.as_string().replace("(content)", text))
    print("\n----------------------------------")
    print("\nEmail sent with new appointments.")

def checkAvailability():
    os.system('cls' if os.name=='nt' else 'clear')
    print("\n============================================")
    with open('categories.json', 'r') as f:
        categories_json = json.load(f)
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(categories_json[category]["url"])

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "desk")))
            driver.find_element(By.ID, "desk").click()
            Select(driver.find_element(By.ID, "desk")).select_by_visible_text(os.getenv("LOCATION"))
            driver.find_element(By.ID, "desk").click()
            next_element = driver.find_elements(By.XPATH, "//*[contains(@class, 'pull-right')]")
            month_element = driver.find_elements(By.XPATH, "//*[contains(@id, '-title')]")
            for x in range(months_out):
                if(x > 0):
                    next_element[0].click()
                month = month_element[0].text
                all_days = {}
                day_elements = driver.find_elements(By.XPATH, "//td[@role='gridcell']")
                in_month = False
                last_day = 30 if month.split()[0] in ["April", "June", "September", "November"] else 31
                days_available = False
                new = False
                for day in day_elements:
                    day_number = int(day.text)
                    button = day.find_element(By.TAG_NAME, "button")
                    if in_month == False and day_number == 1:
                        in_month = True
                    if in_month:
                        all_days[day_number] = ("available" in button.get_attribute("class"))
                        if all_days[day_number] == True:
                            days_available = True
                        if day_number == last_day:
                            in_month = None
                            break
                        
                if days_available:
                    # Get cached days
                    try:
                        with open('cache.json', 'r') as cache_file:
                            cached_day_object = json.load(cache_file)
                    except:
                        cached_day_object = {}
                    if category in cached_day_object:
                        if month in cached_day_object[category]:
                            cached_days = cached_day_object[category][month]
                    else:
                        cached_days = []
                        cached_day_object[category] = {}

                    # Get new appointment dates
                    old_days = []
                    new_days = []
                    all_available_days = []
                    for day in all_days.keys():
                        if all_days[day]:
                            all_available_days.append(day)
                            ignored_date_months = categories_json[category]["ignored_dates"]
                            if not month not in ignored_date_months.keys():
                                ignored_days = ignored_date_months[month]
                            else:
                                ignored_days = []
                            if not day in ignored_days:
                                if not day in cached_days:
                                    new_days.append(day)
                                    new = True
                                    cached_days.append(day)
                                else:
                                    old_days.append(day) 
                        
                    for index, day in enumerate(cached_days):
                        if not day in all_available_days:
                            cached_days.remove(day)
                    cached_day_object[category][month] = cached_days

                    with open('cache.json', 'w') as fp:
                        json.dump(cached_day_object, fp, indent=2)

                    if len(new_days) > 0:
                        print(f"\n{month} - NEW APPOINTMENTS AVAILABLE")
                    else:
                        print(f"\n{month} - NO NEW APPOINTMENTS")
                    results[month] = all_available_days
                    day_string = ""
                    for index, day in enumerate(all_available_days):
                        if index > 0:
                            day_string += ", "
                        day_string += str(day)
                    print(f"- {day_string}  -")
                    
                else:
                    print(f"\n{month} - NO APPOINTMENTS")
                    
            print("\n------------------------------------------")
            now = datetime.now()
            print("\nLast checked: ", now.strftime("%d/%m/%Y %H:%M:%S"), datetime.now().astimezone().tzname())
            if len(results.keys()) > 0 and new:
                sendEmail(category, results)
        finally:
            driver.quit()
    print("\n============================================")


startTimer()
