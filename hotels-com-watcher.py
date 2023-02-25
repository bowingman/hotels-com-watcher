import threading
import os
import json
import sys
import time
import smtplib
import mysql.connector

import streamlit as st
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options

from email.mime.text import MIMEText


configs = None
table_name = "hotel_watch_list"


class HintonCalendar:

    def __init__(self, configs, hotel_specs):
        self.configs = configs
        self.base_url = self.configs["base_url"]
        self.current_url = None
        self.driver = None
        self.hotel_specs = hotel_specs

        self.arrival_date = datetime.strptime(
            hotel_specs['arrival_date'], "%Y-%m-%d")
        self.departure_date = datetime.strptime(
            hotel_specs['departure_date'], "%Y-%m-%d")
        self.nights = int(hotel_specs['nights'])

    def initialize_driver(self):

        chromedriver = os.path.abspath('chrome\\chromedriver.exe')
        self.driver = webdriver.Chrome(chromedriver)

        self.driver.set_window_size(1300, 1000)
        self.driver.implicitly_wait(0.5)

    def launch_calendar(self):
        _base_url = self.base_url.replace(
            '{hotel_code}', self.hotel_specs["hotel_code"])
        _base_url = _base_url.replace(
            '{arrival_date}', str(self.exc_start_date.date()))
        _base_url = _base_url.replace(
            '{departure_date}', str(self.exc_end_date.date()))
        _base_url = _base_url.replace(
            '{redeem_points}', self.hotel_specs["redeem_points"])
        _base_url = _base_url.replace(
            '{num_of_adults}', self.hotel_specs["num_of_adults"])
        self.current_url = _base_url
        self.driver.get(_base_url)
        time.sleep(7)
        print("Loaded Successfully!")

    def gather_active_rooms(self):
        res = {}

        try:
            room_parent = self.driver.find_element(
                By.CSS_SELECTOR, "[data-testid='noOfRoomsReturned']")
            rooms = room_parent.find_elements(By.XPATH, "./*")

            res["from"] = str(self.exc_start_date.date())
            res["to"] = str(self.exc_end_date.date())
            res["url"] = self.current_url
            res["total_room_count"] = len(rooms)
            res["filtered_room_count"] = 0
            res["room_details"] = []

            for room_detail_element in rooms:
                time_logger_st = datetime.now()

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

                time_logger_en = datetime.now()

                print("Finished =>", room_detail_info['RoomTypeName'], "in", (
                    time_logger_en - time_logger_st).microseconds, "ms", str(time_logger_st.time()), str(time_logger_en.time()))

            res["filtered_room_count"] = len(res["room_details"])

        except Exception as e:
            print(e)

        return res

    def watch_calendar(self):
        ret_code, result, total_result = False, {}, {**self.hotel_specs}

        total_result["rooms_by_date"] = []

        for i in range(self.hotel_specs['total_nights']):
            self.exc_start_date = self.arrival_date + timedelta(days=i)
            self.exc_end_date = self.exc_start_date + \
                timedelta(days=self.nights)

            if self.exc_end_date > self.departure_date:
                break
            if self.exc_start_date.month != self.arrival_date.month:
                break
            try:
                self.launch_calendar()
                result = self.gather_active_rooms()
                ret_code = True
            except Exception as e:
                ret_code = False
            if ret_code:
                total_result["rooms_by_date"].append(result)

        self.driver.quit()
        self.driver = None
        return ret_code, total_result


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


def update_data(id, colname, results):
    conn, cursor = connect_mysql_database()

    print("UPDATING DATA... \n")
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    query = f"UPDATE {table_name} SET {colname} = '{json.dumps(results)}', updated_at = '{current_date}' WHERE id = '{id}'"

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


def generate_email_body(results):
    resultheader = """<html>
            <head>
                <style>
                .hotel-info {
                    width: 60%;
                    margin: 0 auto;
                    text-align: center;
                }

                .hotel-info h1 {
                    font-size: 36px;
                    margin-bottom: 20px;
                }

                .hotel-info p {
                    font-size: 18px;
                    margin-bottom: 10px;
                }

                .room-details {
                    width: 100%;
                    margin: 40px 0;
                    text-align: left;
                }

                .room-details h2 {
                    font-size: 24px;
                    margin-bottom: 20px;
                }

                .room-details .room-type {
                    font-size: 18px;
                    margin-bottom: 10px;
                }

                .room-details .room-info {
                    font-size: 14px;
                    margin-bottom: 20px;
                }

                .room-details .room-price {
                    font-size: 18px;
                    margin-bottom: 20px;
                }
                </style>
            </head>"""
    resultbody = """    
            <body>
                <div class="hotel-info">
                <h1>{hotel_code}</h1>
                <p>Arrival Date: {arrival_date}</p>
                <p>Departure Date: {departure_date}</p>
                <p>Number of Adults: {num_of_adults}</p>
                <p>Price of Watch: {price_of_watch}</p>
                </div>
                <div class="room-details">
                <h2>Room Details</h2>
                %ROOM_DETAILS%
                </div>
            </body>
        </html>
    """.format(
        hotel_code=results["hotel_code"],
        arrival_date=results["arrival_date"],
        departure_date=results["departure_date"],
        num_of_adults=results["num_of_adults"],
        price_of_watch=results["price_of_watch"]
    )

    room_details = ""

    for room in results["room_details"]:

        room_details += """
            <div class = "room-type" > {RoomTypeName} </div>
            <div class = "room-info" > {SubInfo} </div>
            <div class = "room-price" >
                Quick Book Price: {QuickBookPrice}
                <br > Pay with Points: {PayWithPoint}
            </div >
        """.format(
            RoomTypeName=room["RoomTypeName"],
            SubInfo=room["SubInfo"],
            QuickBookPrice=room["QuickBookPrice"],
            PayWithPoint=room["PayWithPoint"],
        )

    resultbody = resultbody.replace("%ROOM_DETAILS%", room_details)

    return resultheader + resultbody


def send_content_to_email(email, results={}):

    print("SENDING EMAIL...\n")

    try:
        # Gmail account credentials
        sender_email = configs["user_mail_address"]
        password = configs["mail_app_key"]

        # Email recipient and message
        receiver_email = email
        subject = "The results of Hotel Resarch"
        body = generate_email_body(results)

        # Compose the email message
        message = """From: You <{sender_email}>
To: Recipient <{receiver_email}>
Subject: The results of Hotel Resarch
MIME-Version: 1.0
Content-type: text/html
{body}
""".format(sender_email=sender_email, receiver_email=receiver_email, body=body)

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
    save_data(results)
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
        current_date = datetime.now()
        start_default_date = current_date + timedelta(days=2)
        end_default_date = start_default_date + timedelta(days=5)

        hotel_code = st.text_input('Hotel Code', 'MLEONWA')
        arrival_date = st.text_input(
            'Arrival Date', str(start_default_date.date()))
        departure_date = st.text_input(
            'Departure Date', str(end_default_date.date()))
        num_of_adults = st.number_input("Number of Adults", 1)
        price_of_watch = st.number_input("Price of Watch", 6000, step=100)
        nights = st.number_input("For nights", 1)

        email = st.text_input('Email Address', 'example@gmail.com')
        redeem_points = True

        if st.button('Submit', disabled=not status, type="primary"):
            date1 = datetime.strptime(arrival_date, "%Y-%m-%d")
            date2 = datetime.strptime(departure_date, "%Y-%m-%d")

            max_date = date1 + timedelta(days=14)

            difference1 = date2 - date1
            difference2 = date1 - current_date

            if difference1.days < 1 or difference2.days < 1:
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
                        'nights': int(nights),
                        'total_nights': int(difference1.days),
                        'email': email,
                    })

                    # send_content_to_email(email, results)
                    col2.write(results)
                    # email_notification_status = True
                    # if len(current_email_watch) == 0:
                    # save_data(results)

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
            prev_results = json.loads(row[9])
            current_date = datetime.now()

            print('here', prev_results)

            diff = datetime.strptime(
                prev_results["arrival_date"], "%Y-%m-%d") - current_date

            if diff.days < 2:
                update_data(int(row[0]), "active", False)
                print(int(row[0]), ": Expired")
                continue

            ret_code, results = get_rooms(hotel_specs={
                'hotel_code': row[1],
                'arrival_date': row[2],
                'departure_date': row[3],
                'num_of_adults': str(row[5]),
                'price_of_watch': str(row[6]),
                'redeem_points': str(row[4]),
                'email': row[7],
            })

            if prev_results["filtered_room_count"] == results["filtered_room_count"]:
                for i in range(prev_results["filtered_room_count"]):
                    if prev_results["room_details"][i]["RoomTypeName"] != results["room_details"][i]["RoomTypeName"]:
                        break

            if prev_results["filtered_room_count"] != results["filtered_room_count"] or i != len(prev_results["room_details"]) - 1:
                print("Diff", row[0])
                send_content_to_email(row[7], results)
                update_data(int(row[0]), "results", results)
                print("Successfully Updated")

            else:
                print("Same", row[0])

        print("Successfully finished interval")


if __name__ == '__main__':
    print("__main__")

    is_thread = False
    running_threads = enumerate(list(threading.enumerate()))

    # for i, thread in running_threads:
    #     if "watch_hotel_interval" in thread.name:
    #         print("Already interval exists")
    #         is_thread = True
    #     print("Thread {}: {}".format(i, thread.name))

    # print("Started Main")

    st.set_page_config(layout="wide")
    status = set_env_settings()

    # if not status:
    #     st.error(
    #         "Config.js Not a Present! You can't use this app. Please check your config.js")
    #     exit(0)

    # if not is_thread:
    #     thread = threading.Thread(target=watch_hotel_interval)
    #     thread.start()

    main()
