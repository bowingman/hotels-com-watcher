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
        opt = Options()
        opt.add_experimental_option('debuggerAddress', host)

        self.driver = webdriver.Chrome(service=Service(
            ChromeDriverManager().install()), options=opt)

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

    # def get_current_month_active_dates(self):
    #     try:
    #         flex_dates_visible = WebDriverWait(self.driver, 30).until(
    #             EC.presence_of_element_located((By.XPATH, '//div[@data-e2e="flexDatesCalendarDay"]')))
    #     except:
    #         flex_dates_visible = None
    #     if flex_dates_visible:
    #         try:
    #             active_dates_visible = self.driver.find_elements_by_xpath(
    #                 '//div[@data-e2e="flexDatesCalendarDay" and not(contains(@class, "disabled"))]')
    #         except:
    #             active_dates_visible = []

    #         current_month = self.driver.find_element_by_tag_name('header').text
    #         current_month = current_month[:len(current_month) - 4].strip()

    #         for adate in active_dates_visible:
    #             button_text = adate.find_element_by_xpath('button').text
    #             button_text = button_text.split('\n')
    #             date_thru_txt = button_text[0]
    #             date_thru_txt = date_thru_txt.replace('-', 'through')
    #             room_rate_txt = button_text[1]
    #             if room_rate_txt == self.hotel_specs["price_to_watch"]:
    #                 self.active_dates.append(
    #                     current_month + '@' + date_thru_txt)

    # def gotoNextCalendar(self):
    #     if self.hotel_specs["check_future"].lower() == 'true':
    #         try:
    #             next_button = self.driver.find_element_by_xpath(
    #                 '//div[@class="hidden lg:block"]//button[@data-e2e="goToNextMonthButton" and not(@disabled)]')
    #         except:
    #             next_button = None

    #         if next_button:
    #             next_button.click()
    #             return True
    #         else:
    #             return False
    #     return False

    # def gather_calendar_active_dates(self):
    #     while True:
    #         self.get_current_month_active_dates()
    #         is_next_cal = self.gotoNextCalendar()
    #         if not is_next_cal:
    #             break

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
        # Gmail account credentials
        username = "cadra.sag@gmail.com"
        password = "999912141"

        # Email recipient and message
        to = email
        subject = "The results of Hotel Resarch"
        body = json.dumps(results)

        # Compose the email message
        message = f"Subject: {subject}\n\n{body}"

        # Connect to the Gmail SMTP server and send the email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(username, password)
        server.sendmail(username, to, message)
        server.quit()
    except Exception as e:
        print(e)

    print("SUCCESSFULLY SENT!")
    return True


def main():
    global watcher

    hotel_code = st.text_input('Hotel Code', 'MLEONWA')
    arrival_date = st.text_input('Arrival Date', '2021-01-01')
    departure_date = st.text_input('Departure Date', '2021-01-15')
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
                        "gurut.sag@gmail.com", results)
                st.write(results)
            except KeyboardInterrupt:
                sys.exit(2)


if __name__ == '__main__':
    main()
