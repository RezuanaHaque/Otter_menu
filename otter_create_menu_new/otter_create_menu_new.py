import time
import os
import sys
from pathvalidate import sanitize_filename
import shutil
import requests
import json
import uuid
import logging
# sys.path.append('../ggdriveapi')
# from ggdriveapi import DriveAPI
# from ggdriveapi.ggsheetsapi import GoogleSheets
from ggdriveapi.ggdriveapi import DriveAPI
# from ggdriveapi.ggsheetsapi import GoogleSheets
from ggdriveapi.ggsheetsapi import GoogleSheets


class Automation:
    imageUuid = '0'

    def __init__(self):
        self.driveApi = DriveAPI()

    def run(self):
        os.makedirs("tmp", exist_ok=True)
        os.makedirs("tmp/google drive download", exist_ok=True)
        print('enter the url of the google sheets you want to process:')
        while True:
            x = input()
            # x = 'https://docs.google.com/spreadsheets/d/1SvS8ttP4CmT3FdXndZFpry5QKAQ2YZtx-_5jjeADnbI/edit#gid=623556071'
            if len(x.split('/')) < 2:
                print('invalid url, please enter again:')
                continue
            self.spreadsheetId = x.split('/')[-2]
            try:
                self.sheet = GoogleSheets(self.spreadsheetId, 'original_menu')
                break
            except ValueError:
                print('invalid url, please enter again:')
        # self.spreadsheetId = '1XbvbBYAREaFmtXtDc-CGThQJiAhuo2lulsCtm8d5vok'
        # self.sheet = GoogleSheets(self.spreadsheetId, 'original_menu')

        print('enter the virtual brand number you want to process:')
        while True:
            self.vNum = input()
            # self.vNum = '1'
            try:
                self.vName = self.sheet.getCell(3, 'V{}_Name'.format(self.vNum))
            except ValueError:
                print('invalid virtual brand number, please enter again:')
                continue
            break
        # self.vNum = '1'
        # self.vName = self.sheet.getCell(3, 'V{}_Name'.format(self.vNum))

        self.startRow = 4
        print('enter the Otter url of the menu:')
        while True:
            x = input()
            # x = 'https://manager.tryotter.com/menus/brand/12a5db47-90c6-431a-a6e4-863970b79d8f'
            if x:
                self.menuUrl = x
                break
        # self.menuUrl = 'https://manager.tryotter.com/menus/brand/1641853f-40ee-49aa-8890-d87cdcf47d16'

        print(
            # 'What fields do you want to update if a product already exists? 1: image; 2: addon; 3: the rest. e.g. "1,3". Enter nothing to skip existing products.')
            'What fields do you want to update if a product already exists? 1: image; 2. rest. e.g. "1,2". Enter nothing to skip existing products.')

        while True:
            x = input()
            # x = '3'
            self.updateImage, self.updateAddon, self.updateRest = False, False, False
            try:
                for choice in x.split(','):
                    if choice == '1':
                        self.updateImage = True
                    # if choice == '2':
                    #     self.updateAddon = True
                    if choice == '3':
                        self.updateRest = True
                break
            except:
                print('invalid input, please enter again:')

        self.req = requests.Session()
        body = {
            "email": "bd@heyremotekitchen.com",
            "password": "OtterRemote123!"
        }
        headers = {
            'User-Agent': 'Thunder Client (https://www.thunderclient.com)'
        }
        res = self.req.post('https://api.tryotter.com/users/sign_in', json=body, headers=headers)
        # print(res.text)
        # print(res.status_code)
        # print(res.text)

        token = res.json()['accessToken']
        # print(token)
        self.headers = {'authorization': 'Bearer ' + token}

        self._process()
        shutil.rmtree("tmp")

    def _process(self):
        self.menuTemplateUuid = self.menuUrl.split('/')[-1]
        self.getMenuSummary()
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

            if name == '':
                print('virtual brand product name missing, skipped')
                return True
            name = ' '.join(name.strip().split())
            time.sleep(5)
            description = self.sheet.getCell(row, 'product description')  # this is from row 1
            category = self.sheet.getCell(row, 'V{}_category'.format(self.vNum))
            imageUrl = self.sheet.getCell(row, 'V{}_image'.format(self.vNum))
            price = self.sheet.getCell(row, 'virtual price')
            # addons = self.sheet.getCell(row, 'original add_on')

            categoryUuids = []

            for categoryLine in category.split('\n'):

                if categoryLine not in self.categories:
                    print(categoryLine, self.categories)

                    self.createCategory(categoryLine)
                categoryUuids.append(self.categories[categoryLine])

            imageUuid = None  # Initialize imageUuid here

            if name not in self.items:
                # add new item
                if imageUrl != '':
                    filePath = self.downloadImage(imageUrl, name)
                    imageUuid = self.uploadImage(filePath)
                if addons.strip() != '':
                    modifierGroupUuids = self.createModifierGroups(addons)
                else:
                    modifierGroupUuids = []
                self.createItem(name, imageUuid, description, price, categoryUuids, modifierGroupUuids)
            else:
                if not (self.updateAddon or self.updateImage or self.updateRest):
                    print('skipping')
                    return True

                itemUuid = self.items[name]
                itemInfo = self.itemInfo[itemUuid]

                if self.updateAddon:
                    print('updating addon')
                    if itemUuid in self.itemUuidToModifierGroupUuids:
                        # delete existing addon
                        modifierGroupUuids = self.itemUuidToModifierGroupUuids[itemUuid]
                        modifierUuids = []
                        for modifierGroupUuid in modifierGroupUuids:
                            for modifierUuid in self.modifierGroupUuidToModifierUuids[modifierGroupUuid]:
                                modifierUuids.append(modifierUuid)
                        self.delete(modifierUuids)
                        self.delete(modifierGroupUuids)
                    if addons.strip() != '':
                        modifierGroupUuids = self.createModifierGroups(addons)
                    else:
                        modifierGroupUuids = []
                else:
                    modifierGroupUuids = self.itemUuidToModifierGroupUuids[itemUuid]

                if self.updateImage:
                    print('updating image')
                    self.deleteImage(itemInfo["imageUuid"])
                    if imageUrl != '':
                        filePath = self.downloadImage(imageUrl, name)
                        imageUuid = self.uploadImage(filePath)
                elif "imageUuid" in itemInfo:  # Only assign value if imageUuid exists in itemInfo
                    imageUuid = itemInfo["imageUuid"]

                addCategoryUuids = []
                deleteCategoryUuids = []
                if not self.updateRest:
                    description = itemInfo["description"]
                    price = itemInfo["price"]
                else:
                    originalCategoryUuids = self.itemUuidToCategoryUuids[itemUuid]
                    for categoryUuid in categoryUuids:
                        if categoryUuid not in originalCategoryUuids:
                            addCategoryUuids.append(categoryUuid)
                    for categoryUuid in originalCategoryUuids:
                        if categoryUuid not in categoryUuids:
                            deleteCategoryUuids.append(categoryUuid)
                skuid = itemInfo["skuid"]
                with open("template_entity_specific_info_payload.json", "r") as f:
                    templateEntityPayload = json.load(f)
                templateEntityPayload["variables"]["input"]["templateAndTemplateEntityIds"][0]["entityId"] = itemUuid
                templateEntityPayload["variables"]["input"]["templateAndTemplateEntityIds"][0][
                    "owningEntityId"] = self.menuTemplateUuid

                if self.published:
                    res = self.req.post("https://api.tryotter.com/graphql", headers=self.headers,
                                        json=templateEntityPayload)
                    print('res', res.json())
                    entities = res.json()["data"]["brandMenuTemplateEntities"]["entities"]
                    if entities:  # Check if entities is not empty
                        store_configurations = entities[0]["storeConfigurations"]
                        if store_configurations:  # Check if storeConfigurations is not empty
                            storeEntityUuid = store_configurations[0]["id"]
                        else:
                            storeEntityUuid = None

                self.updateItem(itemUuid, skuid, name, imageUuid, description, price, addCategoryUuids,
                                deleteCategoryUuids, storeEntityUuid, modifierGroupUuids)

            return True
        except KeyboardInterrupt:
            print('manually stopped at row {}'.format(row))
            return False
        except Exception as e:
            print('error occurred when processing row {}'.format(row))
            logging.exception(e)
            return True

    def getMenuSummary(self):
        res = self.req.get("https://api.tryotter.com/users/me", headers=self.headers)
        # print('res', res.json())
        self.organizationUuid = res.json()["user"]["organizationId"]
        # print('res', self.organizationUuid)

        with open("menu_summary_payload.json", "r") as f:
            summaryPayload = json.load(f)
        summaryPayload["variables"]["templateId"] = self.menuTemplateUuid
        # print('res', summaryPayload["variables"]["templateId"])

        res = self.req.post("https://api.tryotter.com/graphql", headers=self.headers, json=summaryPayload)
        summary = res.json()
        # print('res2', summary)
        # print('res2', res.text)
        self.brandUuid = res.json()["data"]["menuTemplate"]["parentEntities"][0]["id"]
        stores = res.json()["data"]["menuTemplate"]["stores"]
        # print('stores',stores)
        if len(stores) == 0:
            self.storeUuid = None
            self.published = False
        else:
            self.storeUuid = stores[0]["id"]
            self.published = True

            with open("brand_payload.json", "r") as f:
                brandPayload = json.load(f)
            brandPayload["variables"]["brandId"] = self.brandUuid
            # print('111111',self.brandUuid)
            res = self.req.post("https://api.tryotter.com/graphql", headers=self.headers, json=brandPayload)
            brand = res.json()
            # print('111111',brand)
            facilityUuid = brand["data"]["brandById"]["storesV2"]["edges"][0]["node"]["facility"]["id"]

            res = self.req.get(
                "https://api.tryotter.com/facilities/stations?organization_id={}".format(self.organizationUuid),
                headers=self.headers)
            # print('111111',res.text)

            stations = res.json()["stations"]
            # print('111111', stations)
            for station in stations:
                if station["facilityId"] == facilityUuid and station["type"] == "STATION_TYPE_KITCHEN":
                    self.stationUuid = station["stationId"]
                    break

        self.categories = {}
        self.items = {}
        self.itemUuidToModifierGroupUuids = {}
        self.modifierGroupUuidToModifierUuids = {}
        self.itemUuidToCategoryUuids = {}
        self.itemInfo = {}
        entities = summary["data"]["menuTemplate"]["entities"]
        # print('111111', entities)

        for entity in entities:
            if entity["__typename"] == "MenuTemplateMenu":
                self.menuUuid = entity['id']
                # print('111111', entities)

            if entity["__typename"] == "MenuTemplateCategory":
                categoryName = entity["name"][0]["value"]
                categoryUuid = entity["id"]
                self.categories[categoryName] = categoryUuid
                for itemUuid in entity["childrenIds"]:
                    if itemUuid not in self.itemUuidToCategoryUuids:
                        self.itemUuidToCategoryUuids[itemUuid] = []
                    self.itemUuidToCategoryUuids[itemUuid].append(categoryUuid)
            if entity["__typename"] == 'MenuTemplateItem':
                itemName = entity["name"][0]["value"]
                itemUuid = entity["id"]
                self.items[itemName] = itemUuid
                self.itemUuidToModifierGroupUuids[itemUuid] = entity["childrenIds"]
                itemInfo = {"name": itemName, "description": entity["description"][0]["value"]}
                # print(itemInfo)
                if len(entity["attachedEntityIds"]) > 0:
                    itemInfo["imageUuid"] = entity["attachedEntityIds"][0]
                else:
                    itemInfo["imageUuid"] = None
                dollars = str(entity["priceData"]["price"]["units"])
                cents = str(entity["priceData"]["price"]["nanos"] / 10000000)
                if len(cents) == 1:
                    cents = '0' + cents
                price = dollars + '.' + cents
                itemInfo["price"] = price
                itemInfo["skuid"] = entity["skuId"]
                self.itemInfo[itemUuid] = itemInfo

            if entity["__typename"] == "MenuTemplateModifierGroup":
                modifierGroupUuid = entity["id"]
                self.modifierGroupUuidToModifierUuids[modifierGroupUuid] = entity["childrenIds"]

    def createCategory(self, categoryName):
        categoryUuid = str(uuid.uuid4())
        # print('categ', categoryUuid)
        with open("category_payload.json", "r") as f:
            payload = json.load(f)
        payload["variables"]["templateId"] = self.menuTemplateUuid
        input = payload["variables"]["input"]["templateEntities"][0]
        input["templateId"] = self.menuTemplateUuid
        input["id"] = categoryUuid
        menuEntity = input["data"]["menuEntity"]
        category = menuEntity["category"]
        category["id"] = categoryUuid
        category["name"][0]["value"] = categoryName
        menuEntity["parentsToAdd"] = self.menuUuid

        res = self.req.post("https://api.tryotter.com/graphql", headers=self.headers, json=payload)
        # print('ressssss',res.text)
        self.categories[categoryName] = categoryUuid

        if self.published:
            with open("store_category_payload.json", "r") as f:
                storeCategoryPayload = json.load(f)

            storeCategoryEntity, _ = self.constructStoreEntity('store_category_create', templateEntityId=categoryUuid)
            storeCategoryPayload["variables"]["input"]["categories"].append(storeCategoryEntity)
            storeCategoryPayload["variables"]["templateId"] = self.menuTemplateUuid

            res = self.req.post("https://api.tryotter.com/graphql", headers=self.headers, json=storeCategoryPayload)

        return categoryUuid

    def downloadImage(self, imageUrl, name):
        fileId = imageUrl.split('/')[-2]
        # print(self.driveApi.__class__)
        # print(fileId)

        # Create the directory if it doesn't exist
        directory = 'tmp/google drive download'
        if not os.path.exists(directory):
            os.makedirs(directory)
        fileName = self.driveApi.download(fileId, 'tmp/google drive download')
        imageFileName = '{}.{}'.format(sanitize_filename(name, replacement_text=' ').strip(), fileName.split('.')[-1])
        os.replace('tmp/google drive download/' + fileName, 'tmp/google drive download/' + imageFileName)
        filePath = os.path.join(os.getcwd(), 'tmp', 'google drive download', imageFileName)
        return filePath

    def uploadImage(self, filePath):
        imageUuid = str(uuid.uuid4())

        # start upload request
        with open("image_upload.json", "r") as f:
            payload = json.load(f)
        startPayload = payload["startUpload"]
        startInput = startPayload["variables"]["input"]["inputs"][0]
        startInput["brandId"] = self.brandUuid
        startInput["fileId"] = imageUuid
        startInput["fileName"] = filePath.split('\\')[-1]

        res = self.req.post("https://api.tryotter.com/graphql", headers=self.headers, json=startPayload)
        resJson = res.json()

        # upload
        uploadUrl = resJson["data"]["startMenuTemplatePhotoUploads"]["responses"][0]["photoUploadUrl"]
        res = self.req.put(uploadUrl, open(filePath, "rb"), headers=self.headers)

        # end upload request
        endPayload = payload["endUpload"]
        endInput = endPayload["variables"]["input"]["inputs"][0]
        endInput["brandId"] = self.brandUuid
        endInput["fileId"] = imageUuid

        res = self.req.post("https://api.tryotter.com/graphql", headers=self.headers, json=endPayload)
        resJson = res.json()

        return resJson["data"]["finishMenuTemplateEntityPhotoUploads"]["photos"][0]["id"]

    def createItem(self, name, imageUuid, description, price, categoryUuids, modifierGroupUuids):
        with open("upsert_payload.json", "r") as f:
            payload = json.load(f)

        # print(payload)

        skuid = str(uuid.uuid4())
        sku = self.constructSku(skuid=skuid, name=name)
        payload["variables"]["upsertOrganizationSkusInput"]["inputs"].append(sku)

        itemUuid = str(uuid.uuid4())

        item = self.constructItem("item_create", itemUuid=itemUuid, skuid=skuid, name=name, price=price,
                                  imageUuid=imageUuid, description=description, addCategoryUuids=categoryUuids,
                                  modifierGroupUuids=modifierGroupUuids)

        payload["variables"]["createMenuTemplateEntitiesInput"]["templateEntities"].append(item)

        if self.published:
            storeEntity, storeEntityUuid = self.constructStoreEntity('store_item_create', templateEntityId=itemUuid,
                                                                     price=price)
            payload["variables"]["createMenuTemplateEntityStoreConfigurationsInput"]["items"].append(storeEntity)

            bulkUpdate = self.constructBulkUpdate(storeEntityUuid, name)
            payload["variables"]["bulkUpdateFulfillmentItemDataInput"]["inputs"].append(bulkUpdate)

        payload["variables"]["templateId"] = self.menuTemplateUuid

        res = self.req.post("https://api.tryotter.com/graphql", headers=self.headers, json=payload)
        self.items[name] = itemUuid
        # print(itemUuid)

    def updateItem(self, itemUuid, skuid, name, imageUuid, description, price, addCategoryUuids, deleteCategoryUuids,
                   storeEntityUuid, modifierGroupUuids):
        with open("upsert_payload.json", "r") as f:
            payload = json.load(f)

        item = self.constructItem("item_update", itemUuid=itemUuid, skuid=skuid, name=name, price=price,
                                  imageUuid=imageUuid, description=description, addCategoryUuids=addCategoryUuids,
                                  deleteCategoryUuids=deleteCategoryUuids, modifierGroupUuids=modifierGroupUuids)
        payload["variables"]["updateMenuTemplateEntitiesInput"]["templateEntities"].append(item)

        if self.published:
            storeEntity, _ = self.constructStoreEntity('store_item_update', price=price,
                                                       storeEntityUuid=storeEntityUuid)
            payload["variables"]["updateMenuTemplateEntityStoreConfigurationsInput"]["items"] = [storeEntity]

            bulkUpdate = self.constructBulkUpdate(storeEntityUuid, name)
            payload["variables"]["bulkUpdateFulfillmentItemDataInput"]["inputs"].append(bulkUpdate)

        payload["variables"]["templateId"] = self.menuTemplateUuid

        res = self.req.post("https://api.tryotter.com/graphql", headers=self.headers, json=payload)
        self.items[name] = itemUuid

    def createModifierGroups(self, addons):
        modifierGroupUuids = []
        # addonR = addons.replace('\r', '')
        # addonR1 = [text.replace('\r', '') for text in addonR]
        # print(addonR.split('\n\n\n'))
        for modifierGroup in addons.split('\n\n\n'):
            # print("modifierGroup:", modifierGroup)
            modifierGroupMeta = modifierGroup.split('\n\n')[0]
            # print("modifierGroupMeta:", modifierGroupMeta)
            modifierGroupName = modifierGroupMeta.split('\n')[0]
            # print("modifierGroupName:", modifierGroupName)
            modifierGroupNumConstraint = modifierGroupMeta.split('\n')[1]
            # print("modifierGroupNumConstraint:", modifierGroupNumConstraint)
            modifierGroupSingleItemNumConstraint = modifierGroupMeta.split('\n')[2]
            # print("modifierGroupSingleItemNumConstraint:", modifierGroupSingleItemNumConstraint)
            # break

            with open("upsert_payload.json", "r") as f:
                payload = json.load(f)

            payload["variables"]["templateId"] = self.menuTemplateUuid

            modifierUuids = []
            for modifier in modifierGroup.split('\n\n')[1:]:
                modifierName = modifier.split('\n')[0]
                if len(modifier.split('\n')) > 1 and modifier.split('\n')[1].strip() != '':
                    modifierPrice = modifier.split('\n')[1]
                else:
                    modifierPrice = '0'

                modifierUuid = str(uuid.uuid4())
                modifierSkuid = str(uuid.uuid4())
                sku = self.constructSku(skuid=modifierSkuid, name=modifierName)
                payload["variables"]["upsertOrganizationSkusInput"]["inputs"].append(sku)
                modifierObject = self.constructItem("modifier_item_create", itemUuid=modifierUuid, skuid=modifierSkuid,
                                                    name=modifierName, price=modifierPrice)
                payload["variables"]["createMenuTemplateEntitiesInput"]["templateEntities"].append(modifierObject)

                if self.published:
                    storeEntity, _ = self.constructStoreEntity('store_modifier_create', templateEntityId=modifierUuid,
                                                               price=modifierPrice)
                    payload["variables"]["createMenuTemplateEntityStoreConfigurationsInput"]["items"].append(
                        storeEntity)

                modifierUuids.append(modifierUuid)

            modifierGroupUuid = str(uuid.uuid4())
            modifierGroupUuids.append(modifierGroupUuid)
            minimumNumberOfChoices = int(modifierGroupNumConstraint.split('-')[0].strip())
            if modifierGroupNumConstraint.split('-')[1].strip() != 'inf':
                maximumNumberOfChoices = int(modifierGroupNumConstraint.split('-')[1].strip())
            else:
                maximumNumberOfChoices = 'inf'
            if modifierGroupSingleItemNumConstraint.strip() != 'inf':
                maxPerModifierSelectionQuantity = int(modifierGroupSingleItemNumConstraint.strip())
            else:
                maxPerModifierSelectionQuantity = 'inf'
            modifierGroupObject = self.constructModifierGroup(modifierGroupUuid=modifierGroupUuid,
                                                              modifierUuids=modifierUuids, name=modifierGroupName,
                                                              minimumNumberOfChoices=minimumNumberOfChoices,
                                                              maximumNumberOfChoices=maximumNumberOfChoices,
                                                              maxPerModifierSelectionQuantity=maxPerModifierSelectionQuantity)
            payload["variables"]["createMenuTemplateEntitiesInput"]["templateEntities"].append(modifierGroupObject)

            if self.published:
                storeEntity, _ = self.constructStoreEntity('store_modifier_group_create',
                                                           templateEntityId=modifierGroupUuid)
                payload["variables"]["createMenuTemplateEntityStoreConfigurationsInput"]["modifierGroups"] = [
                    storeEntity]

            res = self.req.post("https://api.tryotter.com/graphql", headers=self.headers, json=payload)
        return modifierGroupUuids

    def delete(self, templateEntityIds):
        with open("delete_payload.json", "r") as f:
            payload = json.load(f)

        payload["variables"]["templateId"] = self.menuTemplateUuid
        payload["variables"]["ids"] = templateEntityIds

        res = self.req.post("https://api.tryotter.com/graphql", headers=self.headers, json=payload)

    def deleteImage(self, imageUuid):
        with open("delete_photo_payload.json", "r") as f:
            payload = json.load(f)

        deleteData = payload["variables"]["input"]["inputs"][0]
        deleteData["brandId"] = self.brandUuid
        deleteData["photoId"] = imageUuid

        res = self.req.post("https://api.tryotter.com"
                            "/graphql", headers=self.headers, json=payload)

    def constructSku(self, skuid, name):
        with open("sku.json", "r") as f:
            sku = json.load(f)
        sku["id"] = skuid
        sku["brandId"] = self.brandUuid
        sku["name"] = name
        sku['organizationId'] = self.organizationUuid
        # TODO: skuSlug may have more rules
        skuSlug = ''
        for word in name.split():
            skuSlug += word + '-'
        skuSlug += 'a:' + self.brandUuid.replace("-", "") + '-' + str(uuid.uuid4())[0:4]
        sku["skuSlug"] = skuSlug
        return sku

    def constructItem(self, type, itemUuid, skuid, name, price, imageUuid=None, description=None, addCategoryUuids=None,
                      deleteCategoryUuids=None, modifierGroupUuids=None):
        with open("{}.json".format(type), "r") as f:
            item = json.load(f)

        item["id"] = itemUuid
        item["templateId"] = self.menuTemplateUuid

        menuEntity = item["data"]["menuEntity"]
        itemData = menuEntity["item"]
        itemData["id"] = itemUuid
        itemData["name"][0]['value'] = name
        self.modifyPrice(itemData["priceData"], price)
        itemData["skuId"] = skuid

        if type == "item_create" or type == "item_update":
            if imageUuid != None:
                menuEntity["attachedEntityIds"].append(imageUuid)
            itemData["description"][0]['value'] = description
            menuEntity["childrenIds"] = modifierGroupUuids

            for categoryUuid in addCategoryUuids:
                menuEntity["parentsToAdd"].append(categoryUuid)

            if type == "item_update":
                for categoryUuid in deleteCategoryUuids:
                    menuEntity["parentsToRemove"].append(categoryUuid)

        return item

    def constructModifierGroup(self, modifierGroupUuid, modifierUuids, name, minimumNumberOfChoices,
                               maximumNumberOfChoices, maxPerModifierSelectionQuantity):
        with open("modifier_group.json", "r") as f:
            modifierGroup = json.load(f)

        modifierGroup["id"] = modifierGroupUuid
        modifierGroup["templateId"] = self.menuTemplateUuid

        menuEntity = modifierGroup["data"]["menuEntity"]
        menuEntity["childrenIds"] = modifierUuids

        modifierGroupData = menuEntity["modifierGroup"]
        modifierGroupData["id"] = modifierGroupUuid
        modifierGroupData["name"][0]['value'] = name
        modifierGroupData["selectionData"]["minimumNumberOfChoices"] = minimumNumberOfChoices
        if maximumNumberOfChoices != 'inf':
            modifierGroupData["selectionData"]["maximumNumberOfChoices"] = maximumNumberOfChoices
        else:
            modifierGroupData["selectionData"]["maximumNumberOfChoices"] = 0
        if maxPerModifierSelectionQuantity != 1:
            if maxPerModifierSelectionQuantity == 'inf':
                modifierGroupData["selectionData"]["maxPerModifierSelectionQuantity"] = 0
            else:
                modifierGroupData["selectionData"]["maxPerModifierSelectionQuantity"] = maxPerModifierSelectionQuantity

        return modifierGroup

    def constructStoreEntity(self, type, templateEntityId=None, storeEntityUuid=None, price=None):
        with open("{}.json".format(type), "r") as f:
            storeEntity = json.load(f)

        storeEntity["storeId"] = self.storeUuid

        if type.endswith('create'):
            storeEntityUuid = str(uuid.uuid4())
            storeEntity["templateEntityId"] = templateEntityId

        if type != 'store_modifier_group_create':
            storeEntity["stationId"] = self.stationUuid

        storeEntity["id"] = storeEntityUuid

        if type == 'store_item_create' or type == 'store_item_update' or type == 'store_modifier_create':
            self.modifyPrice(storeEntity["priceData"], price)
            storeEntity["fulfillmentConfiguration"]["directFulfillmentConfiguration"]["stationId"] = self.stationUuid

        return storeEntity, storeEntityUuid

    def constructBulkUpdate(self, storeEntityUuid, name):
        with open("bulk_update.json", "r") as f:
            bulkUpdate = json.load(f)

        bulkUpdate["customerItemStoreConfigurationAndStoreId"]["entityId"] = storeEntityUuid
        bulkUpdate["customerItemStoreConfigurationAndStoreId"]["owningEntityId"] = self.storeUuid
        bulkUpdate["fulfillmentItemData"]["name"] = name
        bulkUpdate["fulfillmentItemData"]["stationId"] = self.stationUuid

        return bulkUpdate

    def modifyPrice(self, priceObject, price):
        dollars = int(price.split('.')[0])
        if len(price.split('.')[0]) > 1:
            cents = price.split('.')[1]
            if len(cents) == 1:
                cents += '0'
            cents = int(cents)
        else:
            cents = 0
        priceObject["price"]["units"] = dollars
        priceObject["price"]["nanos"] = cents * 10000000


def main():
    automation = Automation()
    automation.run()


if __name__ == "__main__":
    main()
