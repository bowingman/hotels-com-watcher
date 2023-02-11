import threading
import os
import json
import sys
import time
import smtplib
import mysql.connector

import streamlit as st
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
import utility_box as ut


configs = None
table_name = "hotel_watch_list"


class HintonCalendar:

    def __init__(self, configs, hotel_specs):
        self.configs = configs
        self.base_url = self.configs["base_url"]
        self.current_url = None
        self.driver = None
        self.hotel_specs = hotel_specs
        self.sleep_time = ut.sleep_time_conversion(self.configs["interval"])

    def initialize_driver(self):

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
        self.current_url = _base_url
        self.driver.get(_base_url)
        time.sleep(10)
        print("Loaded Successfully!")

    def gather_active_rooms(self):
        res = {}

        try:
            room_parent = self.driver.find_element(
                By.CSS_SELECTOR, "[data-testid='noOfRoomsReturned']")
            rooms = room_parent.find_elements(By.XPATH, "./*")

            res["hotel_code"] = self.hotel_specs["hotel_code"]
            res["arrival_date"] = self.hotel_specs["arrival_date"]
            res["departure_date"] = self.hotel_specs["departure_date"]
            res["redeem_points"] = self.hotel_specs["redeem_points"]
            res["num_of_adults"] = self.hotel_specs["num_of_adults"]
            res["price_of_watch"] = self.hotel_specs["price_of_watch"]
            res["email"] = self.hotel_specs["email"]
            res["url"] = self.current_url

            res["total_room_count"] = len(rooms)
            res["filtered_room_count"] = 0
            res["room_details"] = []

            for room_detail_element in rooms:
                room_detail_info = {}
                room_detail_info['RoomTypeName'] = room_detail_element.find_element(
                    By.CSS_SELECTOR, "span[data-testid='roomTypeName']").text
                room_detail_info['SubInfo'] = []
                try:
                    room_sub_info = room_detail_element.find_element(
                        By.TAG_NAME, "ul").find_elements(By.XPATH, "./*")
                except Exception as e:
                    room_sub_info = []

                for sub_info in room_sub_info:
                    room_detail_info['SubInfo'].append(sub_info.text)

                try:
                    room_detail_info["PayWithPoint"] = room_detail_element.find_element(
                        By.CSS_SELECTOR, "div[data-testid='pamNotLoggedInMessage']").text
                except Exception as e:
                    print(e)
                    room_detail_info["PayWithPoint"] = None

                try:
                    room_detail_info["QuickBookPrice"] = room_detail_element.find_element(
                        By.CSS_SELECTOR, "span[data-testid='quickBookPrice']").text
                    room_detail_info["QuickBookPriceInt"] = int(
                        room_detail_info["QuickBookPrice"].replace(",", "")[1:])
                except Exception as e:
                    print(e)
                    room_detail_info["QuickBookPrice"] = None
                    room_detail_info["QuickBookPriceInt"] = 0

                try:
                    room_detail_info["MoreRatesPrice"] = room_detail_element.find_element(
                        By.CSS_SELECTOR, "button[data-testid='moreRatesButton']").text
                except Exception as e:
                    print(e)
                    room_detail_info["MoreRatesPrice"] = None

                if room_detail_info["QuickBookPriceInt"] < int(self.hotel_specs['price_of_watch']):
                    res["room_details"].append(room_detail_info)

            res["filtered_room_count"] = len(res["room_details"])

        except Exception as e:
            print(e)

        return res

    def watch_calendar(self):
        ret_code, result = False, {}
        try:
            self.launch_calendar()
            result = self.gather_active_rooms()
            ret_code = True
        except Exception as e:
            ret_code = False
        finally:
            self.driver.quit()
            self.driver = None
        return ret_code, result


def connect_mysql_database():

    conn = mysql.connector.connect(
        host=configs["hostname"],
        user=configs["username"],
        password=configs["password"],
        database=configs["database"]
    )

    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()

    tables = [table[0] for table in tables]
    if table_name in tables:
        print(f"Table {table_name} exists")
    else:
        print(f"Table {table_name} does not exist")

        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        columns = f"( \
            id INT AUTO_INCREMENT PRIMARY KEY, \
            hotel_code VARCHAR(255), \
            arrival_date VARCHAR(255), \
            departure_date VARCHAR(255), \
            redeem_points VARCHAR(255), \
            num_of_adults VARCHAR(255), \
            price_of_watch VARCHAR(255), \
            email VARCHAR(255), \
            url TEXT, \
            results TEXT, \
            active BOOLEAN DEFAULT TRUE, \
            created_at DATETIME DEFAULT '{current_date}', \
            updated_at DATETIME DEFAULT '{current_date}' \
        )"
        query = f"CREATE TABLE {table_name} {columns}"
        cursor.execute(query)

        conn.commit()
        print("Successfully connected to the table!")

    print("Successfully connected to the database!")

    return conn, cursor


def get_watch_list():
    conn, cursor = connect_mysql_database()

    select_query = f"SELECT * FROM {table_name} WHERE active = True"

    cursor.execute(select_query)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


def save_data(results):
    conn, cursor = connect_mysql_database()

    print("SAVING DATA... \n")
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    values = "( \
        hotel_code, \
        arrival_date, \
        departure_date, \
        redeem_points, \
        num_of_adults, \
        price_of_watch, \
        email, \
        url, \
        results, \
        active, \
        created_at, \
        updated_at \
    )"
    data = (
        results["hotel_code"],
        results["arrival_date"],
        results["departure_date"],
        results["redeem_points"],
        results["num_of_adults"],
        results["price_of_watch"],
        results["email"],
        results["url"],
        json.dumps(results),
        True,
        current_date,
        current_date,
    )

    data_str = str(data).replace("(", "").replace(")", "")

    query = f"INSERT INTO {table_name} {values} VALUES ({data_str})"

    cursor.execute(query)
    conn.commit()

    cursor.close()
    conn.close()

    return True


def update_data(id, results):
    conn, cursor = connect_mysql_database()

    print("UPDATING DATA... \n")
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    query = f"UPDATE {table_name} SET results = '{json.dumps(results)}', updated_at = '{current_date}' WHERE id = '{id}'"

    cursor.execute(query)
    conn.commit()

    cursor.close()
    conn.close()

    return True


def delete_data(email):
    conn, cursor = connect_mysql_database()

    print("DELETING DATA... \n")
    query = f"DELETE FROM {table_name} WHERE email = '{email}'"

    cursor.execute(query)
    conn.commit()

    cursor.close()
    conn.close()

    return True


def send_content_to_email(email, results={}):

    print("SENDING EMAIL...\n")

    try:
        # Gmail account credentials
        sender_email = configs["user_mail_address"]
        password = configs["mail_app_key"]

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


def get_rooms(hotel_specs):
    watcher = HintonCalendar(configs, hotel_specs)

    if not watcher.driver:
        watcher.initialize_driver()
    ret_code, results = watcher.watch_calendar()

    if ret_code:
        return True, results
    return False, None
    status = save_data(results)

    if status:
        status = send_content_to_email(hotel_specs['email'], results)

    return True


def set_env_settings():
    global configs

    if not os.path.exists('config.json'):
        return False
    else:
        configs = json.loads(open('config.json').read())
    return True


def handle_update_notification(email, results):
    print('update clicked!')

    delete_data(email)
    update_data(results)
    with st.sidebar:
        st.success(
            "Successfully updated the notification. From now on you will recieve the new contents of emails.")


def handle_keep_notification():
    print('keep clicked!')
    with st.sidebar:
        st.success("You didn't change the notification settings.")


def handle_delete_notification(email):
    print('delete clicked!')

    delete_data(email)

    with st.sidebar:
        st.success("Successfully deleted the notification.")


def main():

    email_notification_status = False

    col1, col2 = st.columns(2)

    st.markdown(
        """ <style>
                .css-163ttbj {
                    background-color: khaki;
                }
            </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        hotel_code = st.text_input('Hotel Code', 'MLEONWA')
        arrival_date = st.text_input('Arrival Date', '2023-02-11')
        departure_date = st.text_input('Departure Date', '2023-02-15')
        num_of_adults = st.number_input("Number of Adults", 1)
        price_of_watch = st.number_input("Price of Watch", 6000, step=100)

        email = st.text_input('Email Address', 'example@gmail.com')
        redeem_points = True

        if st.button('Submit', disabled=not status, type="primary"):
            date1 = datetime.strptime(arrival_date, "%Y-%m-%d")
            date2 = datetime.strptime(departure_date, "%Y-%m-%d")

            difference = date2 - date1

            if difference.days > 15 or difference.days < 1:
                st.error("Please select the correct date!")
                return

            with col1:
                col1.markdown("<h2>Previous Content: </h2>",
                              unsafe_allow_html=True)
                with st.spinner("Wait for it..."):
                    rows = get_watch_list()

                    current_email_watch = [
                        row for row in rows if row[7] == email]

                    if len(current_email_watch) == 0:
                        col1.text("No Previous Content!")

                    else:
                        col1.write(json.loads(current_email_watch[0][9]))

            with col2:
                col2.markdown("<h2>New Content: </h2>",
                              unsafe_allow_html=True)
                with st.spinner("Wait for it..."):

                    ret_code, results = get_rooms(hotel_specs={
                        'hotel_code': hotel_code,
                        'arrival_date': arrival_date,
                        'departure_date': departure_date,
                        'num_of_adults': str(num_of_adults),
                        'price_of_watch': str(price_of_watch),
                        'redeem_points': str(redeem_points),
                        'email': email,
                    })

                    send_content_to_email(email, results)
                    col2.write(results)
                    email_notification_status = True
                    if len(current_email_watch) == 0:
                        save_data(results)

        if email_notification_status:
            st.success(
                f"We've successfully sent it to {email}. Please check your email box.")

            if len(current_email_watch) != 0:
                st.info(
                    "Email notification have been already set before. Do you want to update it?")

                bt1, bt2, bt3 = st.columns([2, 2, 7])
                bt1.button("Y", type="primary",
                           on_click=handle_update_notification, args=(email, results, ))
                bt2.button("N", type="secondary",
                           on_click=handle_keep_notification)
                bt3.button("DELETE NOTIFICATION", type="primary",
                           on_click=handle_delete_notification, args=(email,))


def watch_hotel_interval():
    print("watch_hotel_interval")

    while True:
        time.sleep(1800)

        rows = get_watch_list()

        for row in rows:
            ret_code, results = get_rooms(hotel_specs={
                'hotel_code': row[1],
                'arrival_date': row[2],
                'departure_date': row[3],
                'num_of_adults': str(row[5]),
                'price_of_watch': str(row[6]),
                'redeem_points': str(row[4]),
                'email': row[7],
            })

            prev_results = json.loads(row[9])

            if len(prev_results.room_details) == len(results.room_details):
                for i in range(len(prev_results.room_details)):
                    if prev_results.room_details[i]["RoomTypeName"] != results.room_details[i]["RoomTypeName"]:
                        break

            if i != len(prev_results.room_details) or len(prev_results.room_details) != len(results.room_details):
                print("Diff", row[0])
                send_content_to_email(row[7], results)
                update_data(int(row[0]), results)
                print("Successfully Updated")

            else:
                print("Same", row[0])

        print("Successfully finished interval")


if __name__ == '__main__':
    print("__main__")

    is_thread = False
    running_threads = enumerate(list(threading.enumerate()))

    for i, thread in running_threads:
        if "watch_hotel_interval" in thread.name:
            print("Already interval exists")
            is_thread = True
        print("Thread {}: {}".format(i, thread.name))

    print("Started Main")

    st.set_page_config(layout="wide")
    status = set_env_settings()

    if not status:
        st.error(
            "Config.js Not a Present! You can't use this app. Please check your config.js")
        exit(0)

    if not is_thread:
        thread = threading.Thread(target=watch_hotel_interval)
        thread.start()

    main()
