import json
import os
import sys
import time

import telegram
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

import utility_box as ut

chromedriver = None
watcher = None

class HiltonCalendar:

    def __init__( self, configs ):
        self.configs = configs
        self.base_url = self.configs[ "base_url" ]
        self.driver = None
        self._telegram = telegram.Bot(self.configs[ "telegram" ][ "token" ])
        self._chatIDObject = self.configs[ "telegram" ][ "bot_id" ]
        self.hotel_specs = self.configs[ 'hotelspecs' ]
        self.active_dates = [ ]
        self.sleep_time = ut.sleep_time_conversion(self.configs[ "interval" ])

    def initialize_driver( self ):
        try:
            chromedriver = os.path.abspath(
                "C:\\projects\\mygitlab\\mlpython\\Jupyter_Notebooks\\web_drivers\\chromedriver.exe")
        except:
            chromedriver = os.path.abspath('chromedriver.exe')
        self.driver = webdriver.Chrome(chromedriver)

    def launch_calendar( self ):
        _base_url = self.base_url.replace('{hotel_code}', self.hotel_specs[ "hotel_code" ])
        _base_url = _base_url.replace('{arrival_date}', self.hotel_specs[ "arrival_date" ])
        _base_url = _base_url.replace('{departure_date}', self.hotel_specs[ "departure_date" ])
        _base_url = _base_url.replace('{redeem_points}', self.hotel_specs[ "redeem_points" ])
        _base_url = _base_url.replace('{num_of_adults}', self.hotel_specs[ "num_of_adults" ])
        self.driver.get(_base_url)

    def get_current_month_active_dates( self ):
        try:
            flex_dates_visible = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//div[@data-e2e="flexDatesCalendarDay"]')))
        except:
            flex_dates_visible = None
        if flex_dates_visible:
            try:
                active_dates_visible = self.driver.find_elements_by_xpath(
                    '//div[@data-e2e="flexDatesCalendarDay" and not(contains(@class, "disabled"))]')
            except:
                active_dates_visible = [ ]

            current_month = self.driver.find_element_by_tag_name('header').text
            current_month = current_month[ :len(current_month) - 4 ].strip()

            for adate in active_dates_visible:
                button_text = adate.find_element_by_xpath('button').text
                button_text = button_text.split('\n')
                date_thru_txt = button_text[ 0 ]
                date_thru_txt = date_thru_txt.replace('-', 'through')
                room_rate_txt = button_text[ 1 ]
                if room_rate_txt == self.hotel_specs[ "price_to_watch" ]:
                    self.active_dates.append(current_month + '@' + date_thru_txt)

    def gotoNextCalendar( self ):
        if self.hotel_specs[ "check_future" ].lower() == 'true':
            try:
                next_button = self.driver.find_element_by_xpath(
                    '//div[@class="hidden lg:block"]//button[@data-e2e="goToNextMonthButton" and not(@disabled)]')
            except:
                next_button = None

            if next_button:
                next_button.click()
                return True
            else:
                return False
        return False

    def gather_calender_active_dates( self ):
        while True:
            self.get_current_month_active_dates()
            is_next_cal = self.gotoNextCalendar()
            if not is_next_cal:
                break

    def send_telegram_message( self, dt_table ):
        for k, v in dt_table.items():
            # Send Message to Telegram
            message = '\n\t' + k + ' \- for ' + self.hotel_specs[
                "price_to_watch" ] + '\n```______________________```\n' + v.replace(' ,', '\n')
            self._telegram.send_message(self._chatIDObject, message, parse_mode = telegram.ParseMode.MARKDOWN_V2, )
            time.sleep(ut.get_random_num())

    def watch_calendar( self ):
        self.active_dates = [ ]
        ret_code = False
        try:
            self.launch_calendar()
            self.gather_calender_active_dates()
            dt_table = ut.parse_active_dates(self.active_dates)
            self.send_telegram_message(dt_table)
            ret_code = True
        except:
            ret_code = False
        finally:
            self.driver.quit()
            self.driver = None
        return ret_code

#### MAIN Module
def main( ):
    global watcher

    if os.path.exists('hilton-watcher.json'):
        configs = json.loads(open('hilton-watcher.json').read())
    else:
        print('hilton-watcher.json - Not Present !!!')
        sys.exit(2)

    watcher = HiltonCalendar(configs)

    try:
        while True:
            if not watcher.driver:
                watcher.initialize_driver()
            watcher.watch_calendar()
            time.sleep(watcher.sleep_time)
    except KeyboardInterrupt:
        sys.exit(2)

if __name__ == "__main__":
    main()
