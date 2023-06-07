from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time

import requests
import json

global ignoredCategories
ignoredCategories = {'Popular Items', 'Picked for you', 'Buy 1 get 1 free'}

def extractRestaurantInfo(url):
    result = {}
    while True:
        chromeOptions = webdriver.ChromeOptions()
        chromeOptions.add_argument("--log-level=3")
        chromeOptions.add_argument("--headless")
        chromeOptions.add_argument("--window-size=1920x1080")
        driver = webdriver.Chrome(options=chromeOptions)
        driver.get(url)
        # driver.maximize_window()
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Close"]'))).click()
        try:
            quickViewLink = driver.find_element(By.XPATH, '//a[text()="Quick view"]')
            link = quickViewLink.get_attribute('href')
            storeUuid = link[link.find('storeUuid') + 24: link.find('storeUuid') + 60]
            print('storeUuid: ' + storeUuid)
            break
        except:
            driver.quit()
    
    headers = { "x-csrf-token": "x" }
    res = requests.post('https://www.ubereats.com/api/getStoreV1?localeCode=ca', headers=headers, json={'storeUuid': storeUuid})
    store = res.json()["data"]

    menuUuidToName = {}
    for menu in store["sections"]:
        menuUuidToName[menu["uuid"]] = menu["title"]

    for menuUuid in store["catalogSectionsMap"]:
        menuName = menuUuidToName[menuUuid]
        for category in store["catalogSectionsMap"][menuUuid]:
            categoryName = category["payload"]["standardItemsPayload"]["title"]["text"]
            categoryUuid = category["catalogSectionUUID"]
            if categoryName in ignoredCategories:
                continue
            for product in category["payload"]["standardItemsPayload"]["catalogItems"]:
                productUuid = product["uuid"]
                productName = product["title"]
                print('product name: {}, uuid: {}'.format(productName, productUuid))
                if productName in result:
                    print('product seen before, merging category or menu')
                    result[productName]['category'].add(categoryName)
                    result[productName]['menu'].add(menuName)
                    continue
                payload = {
                    'itemRequestType': 'ITEM',
                    'menuItemUuid': productUuid,
                    'sectionUuid': menuUuid,
                    'storeUuid': storeUuid,
                    'subsectionUuid': categoryUuid
                }
                res = requests.post('https://www.ubereats.com/api/getMenuItemV1', headers=headers, json=payload)
                try:
                    productData = res.json()["data"]
                except requests.exceptions.JSONDecodeError as e:
                    print(res)
                    quit()
                product = {}
                product['category'] = {categoryName}
                product['menu'] = {menuName}
                product['price'] = priceToText(productData["price"])
                product['description'] = productData["itemDescription"]
                product['addon'] = readAddon(productData["customizationsList"])
                product['image url'] = productData["imageUrl"]
                result[productName] = product
                
                # prevent too frequent api call
                time.sleep(0.5)
  
    for productName in result:
        product = result[productName]
        categoryText = ''
        for category in product['category']:
            categoryText += category + '\n'
        product['category'] = categoryText.strip()

        menuText = ''
        for menu in product['menu']:
            menuText += menu + '\n'
        product['menu'] = menuText.strip()

    return result

def priceToText(price):
    priceText = str(price)
    while len(priceText) < 3:
        priceText = '0' + priceText
    priceText = priceText[:-2] + '.' + priceText[-2:]
    return priceText

def readAddon(modifierGroups):
    result = ''
    for modifierGroup in modifierGroups:
        modifierGroupName = modifierGroup["title"]
        result += modifierGroupName + '\n'

        minPermitted = modifierGroup["minPermitted"]
        maxPermitted = modifierGroup["maxPermitted"]
        if maxPermitted == 0:
            maxPermitted = 'inf'     
        result += '{}-{}'.format(minPermitted, maxPermitted) + '\n'

        optionMaxPermitted = modifierGroup["options"][0]["maxPermitted"]
        if optionMaxPermitted == 0:
            optionMaxPermitted = 1
        if optionMaxPermitted > 1 and optionMaxPermitted == modifierGroup["maxPermitted"]:
            optionMaxPermitted = 'inf'
        result += '{}\n\n'.format(optionMaxPermitted)

        for modifier in modifierGroup["options"]:
            result += modifier["title"] + '\n'
            result += priceToText(modifier["price"]) + '\n\n'
        result += '\n'
    return result.strip()

if __name__ == "__main__":
    # # cold tea (two menus)
    with open('Cold-Tea.txt', 'w', encoding='UTF-8') as f:
        f.write(json.dumps(extractRestaurantInfo('https://www.ubereats.com/ca/store/cold-tea-restaurant/AWr0i2oyQui0ZGTBYTHUYA')))
    # halove keto :
    # with open('halove-keto.txt', 'w', encoding='UTF-8') as f:
    #     f.write(json.dumps(extractRestaurantInfo('https://www.ubereats.com/ca/store/halove-keto-1230-davie-street/elHNvCkCVEOURL9PYcqjNw')))
    # Loz Takos : (taco addon can be chosen more than 1 time)
    # with open('Loz-Takos.txt', 'w', encoding='UTF-8') as f:
    #     f.write(json.dumps(extractRestaurantInfo('https://www.ubereats.com/ca/store/loz-takos-coquitlam-centre/by-ovfakRDKmG690hv50yQ?diningMode=DELIVERY')))
    # MB The Place To Be :
    # with open('MB-The-Place-To-Be.txt', 'w', encoding='UTF-8') as f:
    #     f.write(json.dumps(extractRestaurantInfo('https://www.ubereats.com/ca/store/mb-the-place-to-be/eOGaexm8SWiRIo-vpGASjA')))
    # extractRestaurantInfo('https://www.ubereats.com/store/aloha-plates/FlR1yzzyRJCQKJ1HH2piLA')
    