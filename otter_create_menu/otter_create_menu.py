from selenium import webdriver

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

import time
import os
import sys
sys.path.append('../ggdriveapi')
sys.path.append('../extract-data')
from ggsheetsapi import GoogleSheets
from ggdriveapi import DriveAPI
from ubereats import readAddonFromUrl
from pathvalidate import sanitize_filename
import shutil
import logging

global menuName
menuName = 'MENU'

class Automation:
    def __init__(self):
        self.driveApi = DriveAPI()

    def run(self):
        os.makedirs("tmp", exist_ok=True)
        os.makedirs("tmp/google drive download", exist_ok=True)
        print('enter the url of the google sheets you want to process:')
        while True:
            x = input()
            if len(x.split('/')) < 2:
                print('invalid url, please enter again:')
                continue
            self.spreadsheetId = x.split('/')[-2]
            try:
                self.sheet = GoogleSheets(self.spreadsheetId, 'original_menu')
                break
            except ValueError:
                print('invalid url, please enter again:')

        print('enter the virtual brand number you want to process:')
        while True:
            self.vNum = input()
            try:
                self.vName = self.sheet.getCell(3, 'V{}_Name'.format(self.vNum))
            except ValueError:
                print('invalid virtual brand number, please enter again:')
                continue
            break
        
        print('do you want to create a new menu or add to an existing one? enter 1 for new menu, 2 for adding to existing menu:')
        while True:
            x = input()
            if x == '1':
                self.mode = 1
                break
            elif x == '2':
                self.mode = 2
                break
            else:
                print('invalid input, please enter again:')
        
        self.startRow = 4
        if self.mode == 2:
            print('enter the Otter url of the menu:')
            while True:
                x = input()
                if x:
                    self.menuUrl = x
                    break

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

        self._process()
        shutil.rmtree("tmp")
    
    def _prepareBrowser(self):
        chromeOptions = webdriver.ChromeOptions()
        chromeOptions.add_argument("--log-level=3")
        chromeOptions.add_argument("--headless")
        chromeOptions.add_argument('--disable-gpu')
        chromeOptions.add_argument("--no-sandbox")
        chromeOptions.add_argument("--window-size=1920x1080")
        self.driver = webdriver.Chrome(options=chromeOptions)
        if self.mode == 1:
            self.driver.get('https://manager.tryotter.com/login')
        else:
            self.driver.get(self.menuUrl)
        try:
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//input[@type="email"]')))
        except:
            print('Otter menu url invalid, exiting')
            return False
        print('logining')
        self.driver.find_element(By.XPATH, '//input[@type="email"]').send_keys('bd@heyremotekitchen.com')
        self.driver.find_element(By.XPATH, '//input[@type="password"]').send_keys('Napoleon1226!')
        self.driver.find_element(By.XPATH, '//div[text()="Sign in"]/..').click()
        try:
            WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//a[@id="pushActionRefuse"]'))).click()
        except:
            pass
        return True

    def _process(self):
        if not self._prepareBrowser():
            return
        if self.mode == 1:
            print('creating menu')
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Apps")]'))).click()
            self.driver.find_element(By.XPATH, '//span[text()="Menus"]/..').click()
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Add menu")]'))).click()
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Create manually within Otter"]/../..'))).click()
            self.driver.find_element(By.XPATH, '//input[@placeholder="Enter a menu name"]').send_keys(menuName)
            self.driver.find_element(By.XPATH, '//button[@id="downshift-0-toggle-button"]').click()
            try:
                self.driver.find_element(By.XPATH, '//span[text()="{}"]/../parent::li'.format(self.vName)).click()
            except:
                print('virtual brand not exist on Otter, please check if the name is the same between menu table and Otter')
                print('exiting')
                return
            self.driver.find_element(By.XPATH, '//button[text()="Continue"]').click()
            
            checkBox = self.driver.find_element(By.XPATH, '//span[text()="Select all"]/../../div[1]/div/input')
            if checkBox.is_selected():
                checkBox.click()
            
            self.driver.find_element(By.XPATH, '//button[text()="Create Menu"]').click()

        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//div[text()="Categories"]/..'))).click()
        self.categories = set()
        categoryElements = self.driver.find_elements(By.XPATH, '//div[@class="ReactVirtualized__Grid ReactVirtualized__List"]/div/div')
        for categoryElement in categoryElements:
            category = categoryElement.find_element(By.XPATH, './div/div[2]/div[1]/span').text
            self.categories.add(category)
        
        self.driver.find_element(By.XPATH, '//div[text()="Overview"]/..').click()
        productNameElements = self.driver.find_elements(By.XPATH, '//div[@src]/../div[2]/div[1]/span')
        self.productNames = set()
        for productNameElement in productNameElements:
            self.productNames.add(productNameElement.text)
        
        self.driver.find_element(By.XPATH, '//div[text()="Items"]/..').click()
        self.url = self.driver.current_url
        row = self.startRow
        rowNum = self.sheet.getRowNum()
        while row <= rowNum:
            print('processing row {}'.format(row))
            if not self._processRow(row):
                break
            row += 1
    
    def _processRow(self, row):
        try:
            name = self.sheet.getCell(row, 'V{}_Name'.format(self.vNum))
            print(name)
            if name == '':
                print('virtual brand product name missing, skipped')
                return True
            name = ' '.join(name.strip().split())
            if name in self.productNames:
                print('product already exists in the menu, skipping')
                return True
            description = self.sheet.getCell(row, 'product description')
            category = self.sheet.getCell(row, 'V{}_category'.format(self.vNum))
            imageUrl = self.sheet.getCell(row, 'V{}_image'.format(self.vNum))
            price = self.sheet.getCell(row, 'virtual price')
            addons = self.sheet.getCell(row, 'original add_on')

            for categoryLine in category.split('\n'):
                if categoryLine not in self.categories:
                    # add to categories
                    self.driver.find_element(By.XPATH, '//div[text()="Categories"]/..').click()
                    self.driver.find_element(By.XPATH, '//button[contains(text(), "Add category")]').click()
                    time.sleep(1)
                    addCategoryPage = self.driver.find_element(By.XPATH, '//span[text() ="Add category"]/../../../../../..')
                    addCategoryPage.find_element(By.XPATH, './/input[@placeholder="Enter a category name"]').send_keys(categoryLine)
                    addCategoryPage.find_element(By.XPATH, './/span[text() ="Add category to a menu"]/..').click()
                    select = addCategoryPage.find_element(By.XPATH, './/span[text() ="{}"]/../../../div[1]/div/input'.format(menuName))
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", select)
                    select.click()
                    addCategoryPage.find_element(By.XPATH, './/span[text() ="Add category to a menu"]/..').click()
                    addCategoryPage.find_element(By.XPATH, './/button[text() ="Save"]').click()
                    successNotice = WebDriverWait(self.driver, 100).until(EC.presence_of_element_located((By.XPATH, '//div[contains(text(), "Added {}")]'.format(categoryLine))))
                    successNotice.find_element(By.XPATH, './span').click()
                    self.categories.add(categoryLine)
                    self.driver.find_element(By.XPATH, '//div[text()="Items"]/..').click()
            
            if imageUrl != '':
                # download image
                fileId = imageUrl.split('/')[-2]
                fileName = self.driveApi.download(fileId, 'tmp/google drive download')
                imageFileName = '{}.{}'.format(sanitize_filename(name, replacement_text=' ').strip(), fileName.split('.')[-1])
                os.replace('tmp/google drive download/' + fileName, 'tmp/google drive download/' + imageFileName)
                filePath = os.path.join(os.getcwd(), 'tmp', 'google drive download', imageFileName)
                # go to image page
                self.driver.find_element(By.XPATH, '//div[text()="Photos"]/..').click()
                # delete existing image with the same product name
                try:
                    WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, '//div[@display="grid"]')))
                    imageElements = self.driver.find_elements(By.XPATH, '//div[@display="grid"]/div[@display="flex"]')
                    for imageElement in imageElements:
                        if imageElement.find_element(By.XPATH, './div[2]/div[1]/span').text == imageFileName:
                            webdriver.ActionChains(self.driver).move_to_element(imageElement).perform()
                            imageElement.find_element(By.XPATH, './div[1]/div/div/input').click()
                            self.driver.find_element(By.XPATH, '//button[contains(text(), "Delete")]').click()
                            self.driver.find_elements(By.XPATH, '//button[contains(text(), "Delete")]')[1].click()
                            successNotice = WebDriverWait(self.driver, 100).until(EC.presence_of_element_located((By.XPATH, '//div[contains(text(), "1 Photo deleted")]')))
                            successNotice.find_element(By.XPATH, './span').click()
                            break
                except:
                    pass
                # add image
                self.driver.find_element(By.XPATH, '//button[contains(text(), "Add photos")]').click()
                WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, '//div[text()="Add photos"]/../../../div[2]/div/div/div/input'))).send_keys(filePath)
                successNotice = WebDriverWait(self.driver, 100).until(EC.presence_of_element_located((By.XPATH, '//div[contains(text(), "1 Photo uploaded")]')))
                successNotice.find_element(By.XPATH, './span').click()
                self.driver.find_element(By.XPATH, '//div[text()="Items"]/..').click()
            
            self.driver.find_element(By.XPATH, '//button[contains(text(), "Add item")]').click()
            addItemPage = self.driver.find_element(By.XPATH, '//span[text() ="Add item"]/../../../../../..')
            time.sleep(1)
            addItemPage.find_element(By.XPATH, './/input[@placeholder="Enter an item name"]').send_keys(name)
            if description != '':
                addItemPage.find_element(By.XPATH, './/textarea[@placeholder="Enter an item description here if you\'d like"]').send_keys(description)
            if imageUrl != '':
                addItemPage.find_element(By.XPATH, './/span[text()="Add photo to item"]/../..').click()
                choosePhotoPage = self.driver.find_element(By.XPATH, '//div[text()="Choose photo(s)"]/../../..')
                WebDriverWait(self.driver, 100).until(EC.presence_of_element_located((By.XPATH, '//img[@alt="Photo preview"]')))
                try:
                    imageElement = choosePhotoPage.find_element(By.XPATH, '//span[text() ="{}"]/../../..'.format(imageFileName))
                    webdriver.ActionChains(self.driver).move_to_element(imageElement).perform()
                    imageElement.find_element(By.XPATH, './div[1]/div/div/input').click()
                except:
                    print('error occured when choosing image for row {}, probably an image that is exactly the same in content but with another name has been uploaded before.')
                choosePhotoPage.find_element(By.XPATH, './/button[text()="Save"]').click()
            
            for categoryLine in category.split('\n'):
                addItemPage.find_element(By.XPATH, './/span[text() ="Add item to a category"]/..').click()
                select = addItemPage.find_element(By.XPATH, './/span[text() ="{}"]/../../../div[1]/div/input'.format(categoryLine))
                self.driver.execute_script("arguments[0].scrollIntoView(true);", select)
                select.click()
                addItemPage.find_element(By.XPATH, './/span[text() ="Add item to a category"]/..').click()
            addItemPage.find_element(By.XPATH, './/label[text()="Item default price"]/../../div[2]/div/input').send_keys(price)
            addItemPage.find_element(By.XPATH, './/button[text() ="Save"]').click()
            successNotice = WebDriverWait(self.driver, 100).until(EC.presence_of_element_located((By.XPATH, '//div[contains(text(), "Added {}")]'.format(name))))
            successNotice.find_element(By.XPATH, './span').click()

            if addons != '' and addons.startswith('https://www.ubereats.com'):
                addons = readAddonFromUrl(addons)
                self.sheet.setCell(row, 'original add_on', addons)

            if addons != '':
                self.driver.find_element(By.XPATH, '//div[text()="Modifier groups"]/..').click()
                modifierGroups = addons.split('\n\n\n')
                for modifierGroup in modifierGroups:
                    modifierGroupMeta = modifierGroup.split('\n\n')[0]
                    modifierGroupName = modifierGroupMeta.split('\n')[0]
                    modifierGroupRequired = modifierGroupMeta.split('\n')[1] == 'Required'
                    modifierGroupNumConstraint = modifierGroupMeta.split('\n')[2]

                    self.driver.find_element(By.XPATH, '//button[contains(text(), "Add modifier group")]').click()
                    # wait for animation to finish
                    time.sleep(1)
                    addModifierGroupPage = self.driver.find_element(By.XPATH, '//span[text() ="Add modifier group"]/../../../../../..')
                    addModifierGroupPage.find_element(By.XPATH, './/input[@placeholder="Enter a modifier group name"]').send_keys(modifierGroupName)
                    addModifierGroupPage.find_element(By.XPATH, './/span[text() ="Add modifier group to an item"]/..').click()
                    # searchBox = addModifierGroupPage.find_element(By.XPATH, './/input[@placeholder="Search"]')
                    # searchBox.click()
                    # searchBox.send_keys(name)
                    select = addModifierGroupPage.find_element(By.XPATH, './/span[text() ="{}"]/../../../div[1]/div/input'.format(name))
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", select)
                    select.click()
                    addModifierGroupPage.find_element(By.XPATH, './/span[text() ="Add modifier group to an item"]/..').click()

                    if not modifierGroupRequired:
                        addModifierGroupPage.find_element(By.XPATH, './/span[text()="Optional"]/../../div[1]/input').click()
                    
                    addModifierGroupPage.find_element(By.XPATH, './/span[text() ="1 modifier only"]/../..').click()
                    if modifierGroupNumConstraint.split()[1] == '1':
                        addModifierGroupPage.find_element(By.XPATH, './/span[text() ="1 modifier only"]/../parent::li').click()
                    elif modifierGroupNumConstraint.split()[1] == 'up':
                        addModifierGroupPage.find_element(By.XPATH, './/span[text() ="Up to a maximum number"]/../parent::li').click()
                        maximumInput = addModifierGroupPage.find_element(By.XPATH, './/label[text()="Maximum number"]/../../div[2]/input')
                        maximumInput.send_keys(Keys.CONTROL + 'a')
                        maximumInput.send_keys(modifierGroupNumConstraint.split()[3])
                    elif modifierGroupNumConstraint.split()[1] == 'between' or modifierGroupNumConstraint.split()[1].isnumeric():
                        addModifierGroupPage.find_element(By.XPATH, './/span[text() ="Within a set range"]/../parent::li').click()
                        minimumInput = addModifierGroupPage.find_element(By.XPATH, './/label[text()="Range"]/../../div[2]/div[1]/input')
                        minimumInput.send_keys(Keys.CONTROL + 'a')
                        if modifierGroupNumConstraint.split()[1] == 'between':
                            minimumInput.send_keys(modifierGroupNumConstraint.split()[2])
                        else:
                            minimumInput.send_keys(modifierGroupNumConstraint.split()[1])
                        maximumInput = addModifierGroupPage.find_element(By.XPATH, './/label[text()="Range"]/../../div[2]/div[2]/input')
                        maximumInput.send_keys(Keys.CONTROL + 'a')
                        if modifierGroupNumConstraint.split()[1] == 'between':
                            maximumInput.send_keys(modifierGroupNumConstraint.split()[4])
                        else:
                            maximumInput.send_keys(modifierGroupNumConstraint.split()[1])
                    else:
                        addModifierGroupPage.find_element(By.XPATH, './/span[text() ="Any number"]/../parent::li').click()
                    
                    for modifier in modifierGroup.split('\n\n')[1:]:
                        modifierName = modifier.split('\n')[0]
                        if len(modifier.split('\n')) > 1 and modifier.split('\n')[1].strip() != '':
                            modifierPrice = modifier.split('\n')[1]
                        else:
                            modifierPrice = '0'
                        addModifierGroupPage.find_element(By.XPATH, './/button[text()="Add modifier"]').click()
                        addModifierGroupPage.find_element(By.XPATH, './/li[text()="Create modifier"]/..').click()
                        self.driver.find_element(By.XPATH, '//input[@placeholder="Modifier name"]').send_keys(modifierName)
                        self.driver.find_element(By.XPATH, '//label[text()="Price"]/../../div[2]/div/input').send_keys(modifierPrice)
                        self.driver.find_element(By.XPATH, '//button[text()="Create and add"]').click()
                    addModifierGroupPage.find_element(By.XPATH, './/button[text() ="Save"]').click()
                    successNotice = WebDriverWait(self.driver, 100).until(EC.presence_of_element_located((By.XPATH, '//div[contains(text(), "Added {}")]'.format(modifierGroupName))))
                    successNotice.find_element(By.XPATH, './span').click()

                self.driver.find_element(By.XPATH, '//div[text()="Items"]/..').click()
            self.productNames.add(name)
            return True
        except KeyboardInterrupt:
            print('manually stoped at row {}'.format(row))
            return False
        except Exception as e:
            print('error occured when processing row {}'.format(row))
            logging.exception(e)
            self.driver.get(self.url)
            WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//div[text()="Categories"]/..')))
            return True
            
def main():
    automation = Automation()
    automation.run()
        

if __name__ == "__main__":
    main()