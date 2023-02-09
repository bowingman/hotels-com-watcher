import os
import json
import sys
import time
import smtplib

import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options

from webdriver_manager.chrome import ChromeDriverManager


import utility_box as ut


chromedriver = None
watcher = None


class HintonCalendar:

    def __init__(self, configs, hotel_specs):
        self.configs = configs
        self.base_url = self.configs["base_url"]
        self.driver = None
        self.hotel_specs = hotel_specs
        self.activate_rooms = []
        self.sleep_time = ut.sleep_time_conversion(self.configs["interval"])

    def initialize_driver(self, host="localhost:8989"):
        
        chromedriver = os.path.abspath('chrome\\chromedriver.exe')
        self.driver = webdriver.Chrome(chromedriver)

        self.driver.set_window_size(1300, 1000)
        self.driver.implicitly_wait(10)

    def launch_calendar(self):
        _base_url = self.base_url.replace(
            '{hotel_code}', self.hotel_specs["hotel_code"])
        _base_url = _base_url.replace(
            '{arrival_date}', self.hotel_specs["arrival_date"])
        _base_url = _base_url.replace(
            '{departure_date}', self.hotel_specs["departure_date"])
        _base_url = _base_url.replace(
            '{redeem_points}', self.hotel_specs["redeem_points"])
        _base_url = _base_url.replace(
            '{num_of_adults}', self.hotel_specs["num_of_adults"])
        self.driver.get(_base_url)
        time.sleep(10)
        print("Loaded Successfully!")

    def gather_active_rooms(self):
        res = {}

        try:
            room_parent = self.driver.find_element(
                By.CSS_SELECTOR, "[data-testid='noOfRoomsReturned']")
            rooms = room_parent.find_elements(By.XPATH, "./*")

            res["room_count"] = len(rooms)
            res["room_details"] = []

            for room_detail_element in rooms:
                room_detail_info = {}
                room_detail_info['RoomTypeName'] = room_detail_element.find_element(
                    By.CSS_SELECTOR, "span[data-testid='roomTypeName']").text
                room_detail_info['SubInfo'] = []
                room_sub_info = room_detail_element.find_element(
                    By.TAG_NAME, "ul").find_elements(By.XPATH, "./*")

                for sub_info in room_sub_info:
                    room_detail_info['SubInfo'].append(sub_info.text)

                room_detail_info["PayWithPoint"] = room_detail_element.find_element(
                    By.CSS_SELECTOR, "div[data-testid='pamNotLoggedInMessage']").text
                room_detail_info["QuickBookPrice"] = room_detail_element.find_element(
                    By.CSS_SELECTOR, "span[data-testid='quickBookPrice']").text
                room_detail_info["MoreRatesPrice"] = room_detail_element.find_element(
                    By.CSS_SELECTOR, "button[data-testid='moreRatesButton']").text

                res["room_details"].append(room_detail_info)

        except Exception as e:
            print(e)

        return res

    def watch_calendar(self):
        self.activate_rooms = []
        ret_code, result = False, {}
        try:
            self.launch_calendar()
            result = self.gather_active_rooms()
            # dt_table = ut.parse_active_dates(self.active_dates)
            ret_code = True
        except Exception as e:
            ret_code = False
        finally:
            self.driver.quit()
            self.driver = None
        return ret_code, result


def save_data(results):
    return True


def send_content_to_email(email, results={}):

    print("SEND_EMAIL", results)

    try:
        
        gmail_configs = json.loads(open('config.json').read())
        # Gmail account credentials
        sender_email = gmail_configs["user_mail_address"]
        password = gmail_configs["mail_app_key"]

        # Email recipient and message
        receiver_email = email
        subject = "The results of Hotel Resarch"
        body = json.dumps(results)

        # Compose the email message
        message = f"Subject: {subject}\n\n{body}"

        # Connect to the Gmail SMTP server and send the email
        
        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.ehlo()
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message)
            server.close()

            print('Email sent!')
        except Exception as exception:
            print("Error: %s!\n\n" % exception)

    except Exception as e:
        print(e)

    return True


def main():
    global watcher

    hotel_code = st.text_input('Hotel Code', 'MLEONWA')
    arrival_date = st.text_input('Arrival Date', '2023-02-11')
    departure_date = st.text_input('Departure Date', '2023-02-15')
    num_of_adults = st.number_input("Number of Adults", 1)
    price_of_watch = st.number_input("Price of Watch", 2000000, step=10000)

    email = st.text_input('Email Address', 'example@gmail.com')
    redeem_points = True

    if st.button('Submit'):
        if not os.path.exists('hotel-watcher.json'):
            st.write('hotel-watcher.json - Not Present !!!')
        else:
            configs = json.loads(open('hotel-watcher.json').read())
            watcher = HintonCalendar(configs, hotel_specs={
                'hotel_code': hotel_code,
                'arrival_date': arrival_date,
                'departure_date': departure_date,
                'num_of_adults': str(num_of_adults),
                'price_of_watch': str(price_of_watch),
                'redeem_points': str(redeem_points),
            })

            try:
                if not watcher.driver:
                    watcher.initialize_driver()
                ret_code, results = watcher.watch_calendar()

                if ret_code:
                    status = save_data(results)

                if status:
                    status = send_content_to_email(
                        email, results)
                st.write(results)
            except KeyboardInterrupt:
                sys.exit(2)


if __name__ == '__main__':
    main()
