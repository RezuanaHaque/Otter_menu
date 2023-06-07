from selenium import webdriver

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
from datetime import datetime
import calendar
import os
from pathlib import Path
import pandas as pd

class Automation:
    def run(self):
        self._download()
        self._processTable()

    def _download(self):
        try:
            chromeOptions = webdriver.ChromeOptions()
            prefs = {"download.default_directory" : os.path.abspath(".")}
            chromeOptions.add_experimental_option("prefs",prefs) 
            chromeOptions.add_argument("--log-level=3")
            chromeOptions.add_argument("--headless")
            chromeOptions.add_argument('--disable-gpu')
            chromeOptions.add_argument("--no-sandbox")
            chromeOptions.add_argument("--window-size=1920x1080")
            driver = webdriver.Chrome(options=chromeOptions)
            driver.get('https://manager.tryotter.com/login')

            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//input[@type="email"]')))
            driver.find_element(By.XPATH, '//input[@type="email"]').send_keys('bd@heyremotekitchen.com')
            driver.find_element(By.XPATH, '//input[@type="password"]').send_keys('Napoleon1226!')
            driver.find_element(By.XPATH, '//div[text()="Sign in"]/..').click()
            try:
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//a[@id="pushActionRefuse"]'))).click()
            except:
                pass
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Apps")]'))).click()
            driver.find_element(By.XPATH, '//span[text()="Orders"]/..').click()
            WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@data-testid="op-dayrangepicker"]/button'))).click()
            driver.find_element(By.XPATH, '//li[text()="Custom range"]').click()

            print('enter the date range by format "yyyy/mm/dd-yyyy/mm/dd":')
            while True:
                try:
                    x = input()
                    date1 = datetime.strptime(x[0:10], '%Y/%m/%d')
                    date2 = datetime.strptime(x[11:21], '%Y/%m/%d')
                    today = datetime.today()
                    intervalDays = (date2 - date1).days
                    if intervalDays < 0:
                        print('dates order incorrect, please put the ealier date first:')
                        continue
                    if today < date2:
                        print('cannot select a future date, please enter again:')
                        continue
                    if (today - date2).days > 3650:
                        print('the date is too far from today, make sure you are entering the correct date:')
                        continue
                    if intervalDays >= 31:
                        print('selection range cannot exceed 31 days, please enter again:')
                        continue
                    break
                except KeyboardInterrupt:
                    return
                except:
                    print('invalid dates, please enter again:')
            
            monthEnglishToInt = {}
            for i in range(1, 13):
                monthEnglishToInt[calendar.month_name[i]] = i

            while True:
                calendars = driver.find_elements(By.XPATH, '//div[@class="CalendarMonth CalendarMonth_1"]')
                leftCalendar = calendars[1]
                leftCalendarMonthYear = leftCalendar.find_element(By.XPATH, './div/div').text
                leftCalendarMonth = monthEnglishToInt[leftCalendarMonthYear[:-5]]
                leftCalendarYear = int(leftCalendarMonthYear[-4:])
                leftCalendarMonthNum = leftCalendarMonth - 1 + leftCalendarYear * 12
                date1MonthNum = date1.month - 1 + date1.year * 12
                navigationButtons = driver.find_elements(By.XPATH, '//div[@class="DayPickerNavigation_button DayPickerNavigation_button_1 DayPickerNavigation_button__horizontal DayPickerNavigation_button__horizontal_2"]')
                if leftCalendarMonthNum < date1MonthNum:
                    navigationButtons[1].find_element(By.XPATH, './*[local-name() = "svg"]').click()
                elif leftCalendarMonthNum > date1MonthNum:
                    navigationButtons[0].find_element(By.XPATH, './*[local-name() = "svg"]').click()
                else:
                    break
                time.sleep(1)
            
            rightCalendar = calendars[2]
            date1Button = leftCalendar.find_element(By.XPATH, './/span[text()="{}"]/../..'.format(date1.day))
            webdriver.ActionChains(driver).move_to_element(date1Button).click(date1Button).perform()
            if (date1.month == date2.month):
                date2Button = leftCalendar.find_element(By.XPATH, './/span[text()="{}"]/../..'.format(date2.day))
            else:
                date2Button = rightCalendar.find_element(By.XPATH, './/span[text()="{}"]/../..'.format(date2.day))
            webdriver.ActionChains(driver).move_to_element(date2Button).click(date2Button).perform()

            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Export"]'))).click()
            driver.find_elements(By.XPATH, '//button[@data-testid="op-action-list-item"]')[2].click()
            # wait for download to complete
            time.sleep(3)

        except Exception as e: 
            print(e)
            self._download()
        
        driver.quit()
    
    def _processTable(self):
        folder_path = Path('.')
        files = folder_path.glob('*.xls*')
        for file in files:
            fileName = file.name
        os.rename(fileName, 'Order History.xlsx')
        fileName = 'Order History.xlsx'

        df = pd.read_excel(fileName, sheet_name='sheet1')
        df.insert(13, 'Original Price', 0)
        df['Original Price'] = df['Subtotal'] * 0.9
        df.insert(14, 'Base Price', 0)
        df['Base Price'] = df['Original Price'] * 0.8
        df.insert(15, 'Price we have to pay', 0)
        df['Price we have to pay'] = df['Base Price'] * 1.05

        df.loc[len(df) + 1, 'Price we have to pay'] = df['Price we have to pay'].sum()

        df.to_excel(fileName, sheet_name='sheet1', index=False)
            
def main():
    automation = Automation()
    automation.run()
        

if __name__ == "__main__":
    main()