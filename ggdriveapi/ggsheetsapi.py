from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
# from gglogin import gglogin
# from gglogin import gglogin
from ggdriveapi.gglogin import gglogin


class GoogleSheets:
    def __init__(self, spreadsheetId, sheetName, headerRow=4):
        creds = gglogin()
        self.service = build('sheets', 'v4', credentials=creds)
        try:
            result = self.service.spreadsheets().values().get(spreadsheetId=spreadsheetId,
                                                              range='{sheetName}'.format(
                                                                  sheetName=sheetName, headerRow=headerRow)).execute()
            # print(result)
        except HttpError:
            raise ValueError

        # get header to column mapping
        values = result.get('values', [[]])[0]
        self.headers = {}
        for i, value in enumerate(values, start=1):
            if value is not None and value != '':
                self.headers[value] = self._col_to_letter(i)

        self.spreadsheetId = spreadsheetId
        self.sheetName = sheetName
        self.columns = {}

    def _col_to_letter(self, col):
        r = ''
        while col > 0:
            v = (col - 1) % 26
            r = chr(v + 65) + r
            col = (col - v - 1) // 26
        return r

        # returns empty string if cell is empty

    def getCell(self, row, columnHeader):
        if columnHeader not in self.headers:
            raise ValueError
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheetId,
            range='{sheetName}!{column}{row}:{column}{row}'.format(sheetName=self.sheetName,
                                                                   column=self.headers[columnHeader],
                                                                   row=row)).execute()
        values = result.get('values', [[]])
        if len(values[0]) == 0:
            return ''
        return values[0][0]

    # returns empty string if cell is empty
    def getCells(self, startRow, endRow, columnHeaders):
        ranges = []
        for columnHeader in columnHeaders:
            if columnHeader not in self.headers:
                raise ValueError
            ranges.append('{sheetName}!{column}{startRow}:{column}{endRow}'.format(sheetName=self.sheetName,
                                                                                   column=self.headers[columnHeader],
                                                                                   startRow=startRow, endRow=endRow))
        result = self.service.spreadsheets().values().batchGet(
            spreadsheetId=self.spreadsheetId, ranges=ranges, majorDimension='COLUMNS',
            valueRenderOption='FORMATTED_VALUE').execute()
        valueRanges = result.get('valueRanges', [])
        cells = {}
        rowNum = endRow - startRow + 1
        for i in range(len(columnHeaders)):
            if 'values' in valueRanges[i]:
                column = valueRanges[i]['values'][0]
                while len(column) < rowNum:
                    column.append('')
                cells[columnHeaders[i]] = column
            else:
                cells[columnHeaders[i]] = [''] * rowNum
        return cells

    def setCell(self, row, columnHeader, value):
        if columnHeader not in self.headers:
            raise ValueError
        body = {'values': [[value]]}
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheetId,
            range='{sheetName}!{column}{row}:{column}{row}'.format(sheetName=self.sheetName,
                                                                   column=self.headers[columnHeader], row=row),
            valueInputOption='USER_ENTERED', body=body).execute()

    def setCells(self, startRow, values):
        data = []
        for columnHeader in values:
            if columnHeader not in self.headers:
                raise ValueError
            endRow = startRow + len(values[columnHeader]) - 1
            valueRange = {
                'range': '{sheetName}!{column}{startRow}:{column}{endRow}'.format(sheetName=self.sheetName,
                                                                                  column=self.headers[columnHeader],
                                                                                  startRow=startRow, endRow=endRow),
                'values': [values[columnHeader]],
                'majorDimension': 'COLUMNS'
            }
            data.append(valueRange)
        body = {
            'valueInputOption': 'USER_ENTERED',
            'data': data
        }
        self.service.spreadsheets().values().batchUpdate(
            spreadsheetId=self.spreadsheetId, body=body).execute()

    def setCellsScatterd(self, cells):
        data = []
        for cell in cells:
            valueRange = {
                'range': '{sheetName}!{column}{row}:{column}{row}'.format(sheetName=self.sheetName,
                                                                          column=self.headers[cell['columnHeader']],
                                                                          row=cell['row']),
                'values': [[cell['value']]]
            }
            data.append(valueRange)
        body = {
            'valueInputOption': 'USER_ENTERED',
            'data': data
        }
        self.service.spreadsheets().values().batchUpdate(
            spreadsheetId=self.spreadsheetId, body=body).execute()

    # get row num according to column A size
    def getRowNum(self):
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheetId, range='{sheetName}!A:A'.format(sheetName=self.sheetName)).execute()
        return len(result.get('values', [[]]))

    def copyTo(self, copyToSpreadsheetId):
        result = self.service.spreadsheets().get(spreadsheetId=self.spreadsheetId, ranges=[self.sheetName],
                                                 includeGridData=False).execute()
        sheetId = result['sheets'][0]['properties']['sheetId']

        body = {'destination_spreadsheet_id': copyToSpreadsheetId}
        try:
            result = self.service.spreadsheets().sheets().copyTo(spreadsheetId=self.spreadsheetId, sheetId=sheetId,
                                                                 body=body).execute()
        except HttpError:
            raise ValueError
        copyToSheetId = result['sheetId']

        body = {
            'requests': [
                {
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': copyToSheetId,
                            'title': self.sheetName
                        },
                        'fields': 'title'
                    }
                }
            ],
            'includeSpreadsheetInResponse': False
        }
        self.service.spreadsheets().batchUpdate(spreadsheetId=copyToSpreadsheetId, body=body).execute()



if __name__ == "__main__":
    spreadsheet_id = '1SvS8ttP4CmT3FdXndZFpry5QKAQ2YZtx-_5jjeADnbI'
    sheet_name = 'original_menu'
    sheet = GoogleSheets(spreadsheet_id, sheet_name)
    # sheet.copyTo('16L5YAduS8KfY0EwbIIz0rPx6xz5mOAlC1dxKIdSb1WA')
