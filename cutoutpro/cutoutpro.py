from selenium import webdriver

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

import logging
import os
import shutil
import sys
import time
sys.path.append('../ggdriveapi')
sys.path.append('../util')

from ggdriveapi import DriveAPI
from ggsheetsapi import GoogleSheets
from pathvalidate import sanitize_filename
from util import click

import requests
import browser_cookie3
import filetype

def main():
    automation = Automation()
    automation.run()

class Automation:
    EDITED_IMAGES_FOLDER_ID = '1rnXxPeMsAclM-_qea1GOx4RHlkg3Mraw'

    def __init__(self):
        self.driveApi = DriveAPI()

    def run(self):
        shutil.rmtree("tmp", ignore_errors=True)
        os.makedirs("tmp", exist_ok=True)
        os.makedirs("tmp/download", exist_ok=True)
        os.makedirs("tmp/edited images", exist_ok=True)
        os.makedirs("tmp/original images", exist_ok=True)
        self.cj = browser_cookie3.chrome(domain_name='www.cutout.pro')
        self._prepareBrowser()
        print('enter the url of the google sheets you want to process:')
        while True:
            x = input()
            if len(x.split('/')) < 2:
                print('invalid url, please enter again:')
                continue
            self.spreadsheetId = x.split('/')[-2]
            try:
                self.sheet = GoogleSheets(self.spreadsheetId, 'original_menu')
                self._processRestaurant()
                break
            except ValueError:
                print('invalid url, please enter again:')
        print('job finished, exiting')
        self.driver.quit()

    def _prepareBrowser(self, headless=True):
        # open new browser and set default download path
        options = webdriver.ChromeOptions()
        prefs = {"download.default_directory" : os.path.abspath("tmp/download")}
        options.add_experimental_option("prefs",prefs) 
        options.add_argument("--log-level=3")
        if headless:
            options.add_argument("--headless")
            options.add_argument("--window-size=1920x1080")
        self.driver = webdriver.Chrome(options=options)
    
        # go to cutout.pro
        self.driver.get("https://www.cutout.pro/photo-editing-background/upload")

        self.driver.maximize_window()

        for cookie in self.cj:  # session cookies
            cookie_dict = {'domain': cookie.domain, 'name': cookie.name, 'value': cookie.value}
            if cookie.expires:
                cookie_dict['expiry'] = cookie.expires
            if cookie.path_specified:
                cookie_dict['path'] = cookie.path
            self.driver.add_cookie(cookie_dict)
        
        self.driver.get("https://www.cutout.pro/photo-editing-background/upload")

        # close the Recommend section (ads)
        try:
            closeAds = self.driver.find_element(By.CLASS_NAME, "closeIcon")
            click(self.driver, closeAds)
        except:
            pass
        
        try:
            profileIcon = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[1]/div[1]/div/div[1]/header/div/div[2]/div[2]/div/a')))
        except:
            print('login to cutout.pro failed, please make sure you have logged in to cutout.pro in Chrome before running this script')
            quit()
        
        if headless:
            webdriver.ActionChains(self.driver).move_to_element(profileIcon).perform()
            email = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, '//div[@id="email"]'))).text
            print('logged in as {}'.format(email))

        self.skippedPopup = False

    def _processRestaurant(self):
        self.hints = []
        while True:
            print('enter a hint for background generation (one at a time), enter "finished" when you are finished:')
            x = input()
            if not x.strip():
                continue
            elif x == 'finished':
                break
            else:
                self.hints.append(x)

        self.restaurantName = self.driveApi.getFileNameById(self.spreadsheetId)
        self.restaurantFolderId = self.driveApi.getIdByPath(self.EDITED_IMAGES_FOLDER_ID, self.restaurantName)
        if self.restaurantFolderId == -1:
            self.restaurantFolderId = self.driveApi.createFolder(self.EDITED_IMAGES_FOLDER_ID, self.restaurantName)

        print('from which row to start processing? press enter directly for the first product:')
        self.startRow = 4
        while True:
            rowInput = input()
            if not rowInput:
                break
            else:
                try:
                    rowInt = int(rowInput)
                    if rowInt >= 4:
                        self.startRow = rowInt
                        break
                    else:
                        print("invalid row number, note valid row numbers start from 4, please enter again:")
                except:
                    print('invalid row number, please enter an integer:')
        
        print('from which virtual brand to start processing? for example, enter 1 to start from V1:')
        self.startV = 1
        while True:
            try:
                vInt = int(input())
                if vInt >= 1:
                    self.startV = vInt
                    break
                else:
                    print("invalid input, please enter again:")
            except:
                print("invalid input, please enter again:")        

        # generate images for each row
        row = self.startRow
        self.validRows = []
        rowNum = self.sheet.getRowNum()
        columns = [
            'Machine code',
            'product image URL',
            'V{index}_image'.format(index=self.startV)
        ]
        self.cells = self.sheet.getCells(self.startRow, rowNum, columns)
        while row <= rowNum:
            print('processing row {row}'.format(row=row))
            if not self._generateImages(row):
                break
            row += 1

        self.driver.quit()
        self._prepareBrowser(headless=False)
        self.driver.get("https://www.cutout.pro/photo-editing-background/upload")
        
        print('enter "finished" after you download the images and put them to the corresponding folders:')
        while True:
            if input() == 'finished':
                break
        
        self.endV = self.startV
        while True:
            try:
                self.sheet.getCell(1, 'V{}_image'.format(self.endV))
            except ValueError:
                break
            self.endV += 1
        self.endV -= 1

        for row in self.validRows:
            self._processDownloadedImages(row)
       

    def _generateImages(self, row):
        try:
            index = row - self.startRow
            productName = self.cells['Machine code'][index]
            if productName == '':
                print('original product name missing, skipped')
                return True

            # get the url of the picture
            originalImageUrl = self.cells['product image URL'][index]
            if originalImageUrl == '':
                print('original product image url is missing, skipped')
                return True
            
            # check if the row already has generated images starting from self.startV:
            startVImageUrl = self.cells['V{index}_image'.format(index=self.startV)][index]
            if startVImageUrl != '':
                print('already processed, skipped')
                return True
            
            if len(self.hints) > 0:         
                if originalImageUrl.startswith('https://drive.google.com'):
                    fileId = originalImageUrl.split('/')[-2]
                    fileName = self.driveApi.download(fileId, 'tmp/original images')
                    newName = '{}.{}'.format(row, fileName.split('.')[-1])
                    os.rename('tmp/original images/{}'.format(fileName), 'tmp/original images/{}'.format(newName))
                    fileName = newName
                else:
                    res = requests.get(originalImageUrl)
                    imgData = res.content
                    with open('tmp/original images/downloading', 'wb') as handler:
                        handler.write(imgData)
                    extension = filetype.guess('tmp/original images/downloading').extension
                    fileName = '{}.{}'.format(row, extension)
                    os.rename('tmp/original images/downloading', 'tmp/original images/{}'.format(fileName))
                
                filePath = os.path.join(os.getcwd(), 'tmp', 'original images', fileName)
                imageInput = self.driver.find_element(By.XPATH, '//input[@accept="image/png,image/jpeg,image/webp"]')
                self.driver.execute_script('arguments[0].click = function() {};', imageInput)
                uploadBtn = self.driver.find_element(By.XPATH, '//button[contains(@class, "drag-drop-btn")]')
                click(self.driver, uploadBtn)
                imageInput.send_keys(filePath)

                if not self.skippedPopup:
                    # turn off the pop-up section generated by the webpage
                    try:
                        skipBtn = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.jump-over")))
                        click(self.driver, skipBtn)
                    except:
                        pass
                    self.skippedPopup = True

                # resize
                WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//div[contains(text(), "Resize")]')))
                resizeBtn = self.driver.find_element(By.CSS_SELECTOR, 'div.resize')
                click(self.driver, resizeBtn)

                WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(('xpath', '//*[@class="customSize"]/div[1]/div[1]/div/div[1]/div/input')))
                size1 = self.driver.find_element('xpath', '//*[@class="customSize"]/div[1]/div[1]/div/div[1]/div/input')
                size2 = self.driver.find_element('xpath', '//*[@class="customSize"]/div[1]/div[2]/div/div[1]/div/input')
                applyBtn = self.driver.find_element(By.CSS_SELECTOR, 'div.customSize > div.customBotton')
                doneBtn = self.driver.find_element(By.CSS_SELECTOR, 'div.right > button.elevation-2')          
                time.sleep(3)
                canvas = WebDriverWait(self.driver, 30).until(EC.element_to_be_clickable((By.TAG_NAME, "canvas")))
                iconResize = WebDriverWait(self.driver, 30).until(EC.element_to_be_clickable((By.CLASS_NAME, "iSeven")))
                image = WebDriverWait(self.driver, 30).until(EC.element_to_be_clickable((By.CLASS_NAME, "main-left-inner-cover")))

                size2.send_keys(Keys.CONTROL + "a")
                size2.send_keys("900")
                size1.send_keys(Keys.CONTROL + "a")
                size1.send_keys("1600")
                # wait for canvas image to draw
                waitCanvasDrawImageJs = "return arguments[0].getContext('2d').getImageData(0, 0, arguments[0].width, arguments[0].height).data.some(channel => channel !== 0);"
                WebDriverWait(self.driver, 30).until(lambda driver: driver.execute_script(waitCanvasDrawImageJs, canvas))
                # cannot use js click, weird bug
                applyBtn.click()

                # Edit the image on the canvas by drag and drop actions.
                webdriver.ActionChains(self.driver).drag_and_drop_by_offset(iconResize, image.size['width'] / 6 , -image.size['height'] / 6).perform()
                WebDriverWait(self.driver, 30).until(lambda driver: driver.execute_script(waitCanvasDrawImageJs, canvas))
                webdriver.ActionChains(self.driver).drag_and_drop(image, canvas).perform()
                WebDriverWait(self.driver, 30).until(lambda driver: driver.execute_script(waitCanvasDrawImageJs, canvas))
                
                # click done
                click(self.driver, doneBtn)

                print('generating images')
                #for each background hint, generate pictures
                for hint in self.hints:
                    hintInput = self.driver.find_element(By.CSS_SELECTOR, "div.three-imgs-main-right > textarea")
                    hintInput.send_keys(Keys.CONTROL + 'a')
                    hintInput.send_keys('({}) '.format(row) + hint)
                    WebDriverWait(self.driver, 10000).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".generate > button")))
                    generateBtn = self.driver.find_element(By.CSS_SELECTOR, ".generate > button")
                    click(self.driver, generateBtn)
                
                WebDriverWait(self.driver, 10000).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".generate > button")))

            # os.makedirs('tmp/edited images/{row} {productName}'.format(row=row, productName=sanitize_filename(productName, replacement_text=' ')), exist_ok=True)
            os.makedirs('tmp/edited images/{row}'.format(row=row), exist_ok=True)

            self.validRows.append(row)

            return True
        except KeyboardInterrupt:
            return False
        except Exception as e: 
            logging.exception(e)
            self.driver.quit()
            self._prepareBrowser()
            return True


    def _processDownloadedImages(self, row):
        index = row - self.startRow
        productName = self.cells['Machine code'][index]
        # folder = 'tmp/edited images/{row} {productName}'.format(row=row, productName=sanitize_filename(productName, replacement_text=' '))
        folder = 'tmp/edited images/{row}'.format(row=row)
        # change filenames, upload to google drive, and fill url
        productFolderId = self.driveApi.createFolder(self.restaurantFolderId, productName)
        os.chdir(folder)
        files = os.listdir('.')
        files.sort(key=os.path.getmtime)
        index = self.startV
        for filename in files:
            if index > self.endV:
                break
            newName = str(index) + '.' + filename.split('.')[1]
            os.rename(filename, newName)
            fileId, link = self.driveApi.upload(productFolderId, newName)
            
            self.sheet.setCell(row, 'V{index}_image'.format(index=index), link)
            index += 1

        os.chdir('../../..')


if __name__ == "__main__":
    main()

