import os

import sys
sys.path.append('../ggdriveapi')
from ggsheetsapi import GoogleSheets
import ubereats
import json

global headerMapping
headerMapping = {
    'name': 'Original dish name',  #here the name is empty        
    'category': 'Original Product Category',
    'addon': 'Original Add-on', 
    'price': 'Original Product Price',
    'description': 'Original Product Description', 
    'image url': 'Original Image',
    'menu': 'Menu'}

class ExtractRestaurantInfo:
    def run(self):
        os.makedirs("tmp", exist_ok=True)
        os.makedirs("tmp/google drive download", exist_ok=True)

        print('do you want to create a new menu or make change to existing one? enter 1 for new menu, 2 for existing menu:')
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

        print('enter the url of the google sheets you want to store the data:')
        while True:
            x = input()
            if len(x.split('/')) < 2:
                print('invalid url, please enter again:')
                continue
            self.spreadsheetId = x.split('/')[-2]
            try:
                if self.mode == 1:
                    templateMenuSheet = GoogleSheets('16L5YAduS8KfY0EwbIIz0rPx6xz5mOAlC1dxKIdSb1WA', 'original_menu')
                    templateMenuSheet.copyTo(self.spreadsheetId)
                    templateCategoryMappingSheet = GoogleSheets('16L5YAduS8KfY0EwbIIz0rPx6xz5mOAlC1dxKIdSb1WA', 'category_mapping')
                    templateCategoryMappingSheet.copyTo(self.spreadsheetId)
                self.sheet = GoogleSheets(self.spreadsheetId, 'original_menu')
                break
            except ValueError:
                print('invalid url, please enter again:')

        print('enter the url of the store on delivery platform:')
        while True:
            url = input()
            if url.startswith('https://www.ubereats.com'):
                info = ubereats.extractRestaurantInfo(url)
                total_images = sum(1 for item in info.values() if 'image url' in item)
                print(f"Total images: {total_images}")

                break
            else:
                print('platform not supported, please enter again:')

        # with open('Cold-Tea.txt', 'r', encoding='UTF-8') as f:
        #     info = json.load(f)
        
        modifiedCount = 0
        if self.mode == 2:
            cells = []
            originalProductNames = self.sheet.getCells(4, self.sheet.getRowNum(), ['Machine code'])['Machine code']
            for i in range(len(originalProductNames)):
                originalProductName = originalProductNames[i]
                if originalProductName in info:
                    row = i + 4
                    product = info[originalProductName]
                    for infoHeader in headerMapping:
                        if infoHeader == 'name':
                            continue
                        cell = {
                            'columnHeader': headerMapping[infoHeader],
                            'row': row,
                            'value': product[infoHeader]
                        }
                        cells.append(cell)
                    del info[originalProductName]
                    modifiedCount += 1
            self.sheet.setCellsScatterd(cells)
            print('modified {} rows'.format(modifiedCount))

        startRow = self.sheet.getRowNum() + 1
        values = {}
        for infoHeader in headerMapping:
            column = []
            for productName in info:
                if infoHeader == 'name':
                    column.append(productName)
                else:
                    column.append(info[productName][infoHeader])
            if infoHeader == 'name':
                values[headerMapping[infoHeader]] = column
            else:
                values[headerMapping[infoHeader]] = [str(val) if val is not None else '' for val in column]
        self.sheet.setCells(startRow, values)
        print('added {} rows'.format(len(info)))


if __name__ == "__main__":
    runner = ExtractRestaurantInfo()

    runner.run()
