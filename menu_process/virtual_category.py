import sys
sys.path.append('../ggdriveapi')
from ggsheetsapi import GoogleSheets

def main():
    print('enter the url of the google sheets you want to process:')
    while True:
        x = input()
        if len(x.split('/')) < 2:
            print('invalid url, please enter again:')
            continue
        spreadsheetId = x.split('/')[-2]
        try:
            menuSheet = GoogleSheets(spreadsheetId, 'original_menu')
            categoryMappingSheet = GoogleSheets(spreadsheetId, 'category_mapping')
            break
        except ValueError:
            print('invalid url, please enter again:')
    
    endV = 1
    virtualCategories = {}
    categoryMappingRowNum = categoryMappingSheet.getRowNum()
    originalCategoryColumn = categoryMappingSheet.getCells(2, categoryMappingRowNum,  ['Original'])['Original']
    categoryMappings = []
    while True:
        try:
            virtualCategoryColumn = categoryMappingSheet.getCells(2, categoryMappingRowNum,  ['V{}'.format(endV)])['V{}'.format(endV)]
            categoryMapping = {}
            for i in range(len(originalCategoryColumn)):
                categoryMapping[originalCategoryColumn[i]] = virtualCategoryColumn[i]
            virtualCategories['V{}_category'.format(endV)] = []
            categoryMappings.append(categoryMapping)
        except ValueError:
            break
        endV += 1
    endV -= 1
    originalCategories = menuSheet.getCells(4, menuSheet.getRowNum(), ['original product category'])['original product category']
    for originalCategory in originalCategories:
        for v in range(1, endV + 1):
            virtualCategory = ''
            for category in originalCategory.split('\n'):
                virtualCategory += categoryMappings[v - 1][category] + '\n'
            virtualCategory = virtualCategory.strip()
            virtualCategories['V{}_category'.format(v)].append(virtualCategory)
    
    menuSheet.setCells(4, virtualCategories)

if __name__ == "__main__":
    main()