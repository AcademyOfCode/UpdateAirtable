import argparse
import os
import requests
import copy
import time
import dateutil.parser
import datetime
from datetime import timedelta
from builtins import any as b_any
from threading import BoundedSemaphore as BoundedSemaphore, Timer

parser = argparse.ArgumentParser()
parser.add_argument('squarespaceOrderApiKey')
parser.add_argument('squarespaceInventoryApiKey')
parser.add_argument('airtableApiKey')
args = parser.parse_args()

squarespaceOrderApiKey = args.squarespaceOrderApiKey
squarespaceOrderApiURL = 'https://api.squarespace.com/1.0/commerce/orders'
squarespaceInventoryApiKey = args.squarespaceInventoryApiKey
squarespaceInventoryApiURL = 'https://api.squarespace.com/1.0/commerce/inventory'

airtableApiKey = args.airtableApiKey

productNameIgnoreList = ['Custom payment amount']
airtableAppIdDict = {'Oatlands College': 'appw2m4IGMCCW2AFd', 'St Pauls College': 'app6TZs7NzO5dYIap', 'St. Colmcilles CS': 'appFA3WwPypeQgg4o', 'Castleknock Community College': 'appqieHXlKvWWSfB4', 'Newbridge College':'app8XtrD48LCTs1fr',
                     'Synge Street CBS':'appVkqUpJ3p5UzdTO', 'Virtual Venue': 'appeAMZ0zlOSKGOc0', 'Tech Clubs': 'appZONEatk4ekDGFP'}
nonTechClubClassList = ['Oatlands College', 'St Pauls College', 'St. Colmcilles CS', 'Castleknock Community College', 'Newbridge College', 'Synge Street CBS', 'Virtual Venue']

class RatedSemaphore(BoundedSemaphore):
    """Limit to 1 request per `period / value` seconds (over long run)."""
    def __init__(self, value=1, period=1):
        BoundedSemaphore.__init__(self, value)
        t = Timer(period, self._add_token_loop,kwargs=dict(time_delta=float(period)/value))
        t.daemon = True
        t.start()

    def _add_token_loop(self, time_delta):
        """Add token every time_delta seconds."""
        while True:
            try:
                BoundedSemaphore.release(self)
            except ValueError: # ignore if already max possible value
                pass
            time.sleep(time_delta)

    def release(self):
        pass # do nothing (only time-based release() is allowed)

def WriteLastGenerationDate(endDate):
    with open(os.path.dirname(os.path.abspath(__file__)) + '\LastClassListGenerationDate.txt', 'w') as file:
        file.write(endDate)

def ReadLastGenerationDate():
    with open(os.path.dirname(os.path.abspath(__file__)) + '\LastClassListGenerationDate.txt') as file:
        lastEndDate = dateutil.parser.parse(file.readlines()[0])
    startDate = lastEndDate + timedelta(microseconds=1)

    return startDate.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

def getRequestWithRateLimit(apiURL, headers=None, params=None):
    rateLimit = RatedSemaphore(120, 60)

    try:
        with rateLimit, requests.get(apiURL, headers=headers, params=params) as response:
            return response.json(), None
    except Exception as e:
        print(e)
        return None, e

def ExportAllOrders():
    pageNumber = 1
    orderList = []

    startDate = ReadLastGenerationDate()
    endDate = datetime.datetime.now()

    if time.daylight and time.localtime().tm_isdst > 0:
        endDate -= timedelta(hours=1)

    endDate = endDate.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    headers = {
        'Authorization': 'Bearer ' + squarespaceOrderApiKey,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'
    }

    params = [
        ('modifiedAfter', startDate),
        ('modifiedBefore', endDate),
        ('fulfillmentStatus', 'PENDING')
    ]

    responseJSON, error = getRequestWithRateLimit(squarespaceOrderApiURL, headers, params)

    for index in range(len(responseJSON['result'])):
        skipOrder = False
        for productName in productNameIgnoreList:
            if productName in responseJSON['result'][index]['lineItems'][0]['productName'] or responseJSON['result'][index]['lineItems'][0]['productName'] in productName:
                skipOrder = True
                break
        if not skipOrder and responseJSON['result'][index]['refundedTotal']['value'] == '0.00':
            orderList.append(responseJSON['result'][index])

    if responseJSON['result']:
        print('Page ' + str(pageNumber) + ' Order Request Completed.')

    while responseJSON['pagination']['hasNextPage'] == True:
        pageNumber += 1

        params = [
            ('cursor', responseJSON['pagination']['nextPageCursor'])
        ]

        responseJSON, error = getRequestWithRateLimit(squarespaceOrderApiURL, headers, params)

        for index in range(len(responseJSON['result'])):
            skipOrder = False
            for productName in productNameIgnoreList:
                if productName in responseJSON['result'][index]['lineItems'][0]['productName']:
                    skipOrder = True
                    break
            if not skipOrder and responseJSON['result'][index]['refundedTotal']['value'] == '0.00':
                orderList.append(responseJSON['result'][index])

        print('Page ' + str(pageNumber) + ' Order Request Completed.')

    return orderList, endDate

def ExportIndividualOrders(allOrdersList):
    orderCount = 1
    responseList = []
    seperatedNameOrderList = []

    headers = {
        'Authorization': 'Bearer ' + squarespaceOrderApiKey,
        'User-Agent': 	'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'
    }

    print('Exporting Individual Orders...')

    for order in allOrdersList:
        orderID = order['id']

        responseJSON, error = getRequestWithRateLimit(squarespaceOrderApiURL + '/' + orderID, headers)

        responseList.append(responseJSON)
        print('Order ' + str(orderCount) + ' Completed.')
        orderCount += 1

    for order in responseList:
        lineItemNumber = 0
        for lineItem in order['lineItems']:
            orderCopy = copy.deepcopy(order)
            lineItemCopy = copy.deepcopy(orderCopy['lineItems'])

            if (len(lineItem['customizations'][0]['value'].split()) > 1 and len(lineItem['customizations'][1]['value'].split()) > 1 and len(lineItem['customizations'][2]['value'].split()) == 0 and lineItem['quantity'] == 2) or \
               (len(lineItem['customizations'][0]['value'].split()) > 1 and len(lineItem['customizations'][1]['value'].split()) == 0 and len(lineItem['customizations'][2]['value'].split()) > 1 and lineItem['quantity'] == 2):
                seperatedNameOrderList.append(orderCopy)
            elif len(lineItem['customizations'][0]['value'].split()) > 1 and len(lineItem['customizations'][1]['value'].split()) > 1 and len(lineItem['customizations'][2]['value'].split()) > 1 and lineItem['quantity'] == 3:
                seperatedNameOrderList.append(orderCopy)
                seperatedNameOrderList.append(orderCopy)

            if type(lineItemCopy) is list:
                orderCopy['lineItems'] = lineItemCopy[lineItemNumber]
            else:
                orderCopy['lineItems'] = lineItemCopy
            seperatedNameOrderList.append(orderCopy)

            lineItemNumber += 1

    return seperatedNameOrderList

def retrieveInventory():
    pageNumber = 1
    inventoryList = []

    headers = {
        'Authorization': 'Bearer ' + squarespaceInventoryApiKey,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'
    }

    responseJSON, error = getRequestWithRateLimit(squarespaceInventoryApiURL, headers)

    for index in range(len(responseJSON['inventory'])):
        inventoryList.append(responseJSON['inventory'][index])

    print('Page ' + str(pageNumber) + ' Inventory Request Completed.')

    while responseJSON['pagination']['hasNextPage'] == True:
        pageNumber += 1

        params = [
            ('cursor', responseJSON['pagination']['nextPageCursor'])
        ]

        responseJSON, error = getRequestWithRateLimit(squarespaceInventoryApiURL, headers, params)

        for index in range(len(responseJSON['inventory'])):
            inventoryList.append(responseJSON['inventory'][index])

        print('Page ' + str(pageNumber) + ' Inventory Request Completed.')

    return inventoryList

def findCurrentTermInInventory(inventoryList):
    currentTermVariantList = []

    for i in range(len(inventoryList)):
        if 'Spring' in inventoryList[i]['descriptor'].split('[')[0] and ('\'20' in inventoryList[i]['descriptor'].split('[')[0] or '2020' in inventoryList[i]['descriptor'].split('[')[0]):
            currentTermVariant = inventoryList[i]['descriptor']

            if '\'20' in currentTermVariant:
                currentTermVariant = currentTermVariant.replace('\'20', '2020')

            if ', ' in currentTermVariant.split('- ')[1].split('[')[0]:
                currentTermVariant = currentTermVariant[0:currentTermVariant.index(',')] + ' ' + currentTermVariant[currentTermVariant.index('['):len(currentTermVariant)]

            if len(currentTermVariant.split(',')) > 3:
                if not b_any(currentTermVariant[0:currentTermVariant.rfind(',')] in x for x in currentTermVariantList):
                    currentTermVariantList.append(currentTermVariant)
            else:
                if not b_any(currentTermVariant in x for x in currentTermVariantList):
                    currentTermVariantList.append(currentTermVariant)

    return currentTermVariantList

def splitVariantLists(currentTermVariantList):
    grouped = {}
    for elem in currentTermVariantList:
        key = elem.split(' [')[0]
        grouped.setdefault(key, []).append(elem)
    grouped = list(grouped.values())

    return grouped

def splitVenueLists(ordersList):
    grouped = {}
    for elem in ordersList:
        key = elem['lineItems']['productName'].split('- ')[1].split(',')[0]
        grouped.setdefault(key, []).append(elem)
    grouped = list(grouped.values())

    return grouped

def updateAirtableClassInfo(currentTermVariantsList):
    print('\nUpdating Class Information on Airtable...')

    for venueVariants in currentTermVariantsList:
        from airtable import airtable

        if venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "") not in nonTechClubClassList:
            appId = airtableAppIdDict['Tech Clubs']
            airtableVenue = airtable.Airtable(appId, 'Venue', airtableApiKey)
        else:
            appId = airtableAppIdDict[venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "")]

        airtableClass = airtable.Airtable(appId, 'Class', airtableApiKey)

        for venueVariant in venueVariants:
            if appId == airtableAppIdDict['Tech Clubs']:
                if not airtableVenue.search('Name',venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "")):
                    airtableVenue.insert({'Name': venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "")})

            if not airtableClass.search('Class Name',  venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "") + ', ' + venueVariant.split('[')[1].split(',')[0] + ', ' + venueVariant.split(', ')[1].split(',')[0] + ', ' + venueVariant.split(', ')[2].split(']')[0] + ', ' + venueVariant.split(' - ')[0]):
                if appId == airtableAppIdDict['Tech Clubs']:
                    venue = airtableVenue.search('Name', venueVariants[0].split('- ')[1].split(' [')[0].replace("'", ""))
                    airtableClass.insert({'Term': venueVariant.split(' - ')[0],
                                          'Venue': [venue[0]['id']],
                                          'Day of the Week': venueVariant.split('[')[1].split(',')[0],
                                          'Time': venueVariant.split(', ')[1].split(',')[0],
                                          'Age Group': venueVariant.split(', ')[2].split(']')[0]})
                else:
                    airtableClass.insert({'Term': venueVariant.split(' - ')[0],
                                          'Venue': venueVariants[0].split('- ')[1].split(' [')[0].replace("'", ""),
                                          'Day of the Week': venueVariant.split('[')[1].split(',')[0],
                                          'Time': venueVariant.split(', ')[1].split(',')[0],
                                          'Age Group': venueVariant.split(', ')[2].split(']')[0]})

                print('Inserting "' + venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "") + ', ' + venueVariant.split('[')[1].split(',')[0] + ', ' + venueVariant.split(', ')[1].split(',')[0] + ', ' + venueVariant.split(', ')[2].split(']')[0] + ', ' + venueVariant.split(' - ')[0] + '" into Class Table')

def updateAirtableStudentInfo(groupedOrderList):
    print('\nUpdating Student Information on Airtable...')

    for venueOrderList in groupedOrderList:
        from airtable import airtable

        if venueOrderList[0]['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "") not in nonTechClubClassList:
            appId = airtableAppIdDict['Tech Clubs']
        else:
            appId = airtableAppIdDict[venueOrderList[0]['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "")]

        airtableStudent = airtable.Airtable(appId, 'Student', airtableApiKey)

        prevOrderID = 0
        thirdOrder = False
        keyList = list(airtableAppIdDict.keys())
        valList = list(airtableAppIdDict.values())

        for order in venueOrderList:
            if order['orderNumber'] == prevOrderID and (len(order['lineItems']['customizations'][1]['value'].split()) > 1 or len(order['lineItems']['customizations'][2]['value'].split()) > 1):
                if thirdOrder:
                    nameIndex = 2
                    dobIndex = 5
                    thirdOrder = False
                else:
                    nameIndex = 1
                    dobIndex = 4
                    thirdOrder = True
            else:
                nameIndex = 0
                dobIndex = 3
                thirdOrder = False

            name = order['lineItems']['customizations'][nameIndex]['value'].title().replace("\'", "")
            firstName = name.split()[0]

            if 'Mc' in name and 'Mc' not in firstName:
                index = name.find('Mc')
                name = name.replace("Mc", "").title()
                name = name[:index] + 'Mc' + name[index:]
            elif 'Mac' in name and 'Mac' not in firstName:
                index = name.find('Mac')
                name = name.replace("Mac", "").title()
                name = name[:index] + 'Mac' + name[index:]

            if not airtableStudent.search('Primary Key', name + ' (' + order['lineItems']['customizations'][dobIndex]['value'] + ')'):
                print('Inserting "' + name + '" into ' + keyList[valList.index(appId)] +' Student Table')

                airtableStudent.insert({'Name': name,'Date of Birth': order['lineItems']['customizations'][dobIndex]['value']})

            prevOrderID = order['orderNumber']

def updateAirtableStudentRegistrationInfo(groupedOrderList):
    print('\nUpdating Student Registration Information on Airtable...')

    for venueOrderList in groupedOrderList:
        from airtable import airtable

        if venueOrderList[0]['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "") not in nonTechClubClassList:
            appId = airtableAppIdDict['Tech Clubs']
        else:
            appId = airtableAppIdDict[venueOrderList[0]['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "")]

        airtableStudentReg = airtable.Airtable(appId, 'Student Registration', airtableApiKey)
        airtableStudent = airtable.Airtable(appId, 'Student', airtableApiKey)
        airtableClass = airtable.Airtable(appId, 'Class', airtableApiKey)

        prevOrderID = 0
        thirdOrder = False

        for order in venueOrderList:
            if 'I DO NOT' in order['lineItems']['customizations'][11]['value']:
                photographyConsent = 'No'
            else:
                photographyConsent = 'Yes'

            if 'Subscription' in order['lineItems']['productName'] or (len(order['lineItems']['variantOptions']) > 1 and 'Annual Fee' in order['lineItems']['variantOptions'][1]['value']):
                term = 'Spring 2020'
            else:
                if '\'20' in order['lineItems']['productName'].split(' -')[0].split(',')[0] or  '2020' in order['lineItems']['productName'].split(' -')[0].split(',')[0]:
                    term = order['lineItems']['productName'].split(' -')[0].split(',')[0].replace('\'20', '2020')
                else:
                    term = order['lineItems']['productName'].split(' -')[0].split(',')[0].replace('\'19', '2019')

            if 'Yes' in order['lineItems']['customizations'][7]['value']:
                returningStudent = 'Yes'
            else:
                returningStudent = ''

            if order['orderNumber'] == prevOrderID and (len(order['lineItems']['customizations'][1]['value'].split()) > 1 or len(order['lineItems']['customizations'][2]['value'].split()) > 1):
                if thirdOrder:
                    nameIndex = 2
                    dobIndex = 5
                    thirdOrder = False
                else:
                    nameIndex = 1
                    dobIndex = 4
                    thirdOrder = True
            else:
                nameIndex = 0
                dobIndex = 3
                thirdOrder = False

            # This IF statement is hard-coded for Synge Street
            if order['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "") + ', ' + order['lineItems']['variantOptions'][0]['value'].split(',')[0] + ', ' + order['lineItems']['variantOptions'][0]['value'].split(', ')[1] \
                                                   + ', ' + order['lineItems']['variantOptions'][0]['value'].split(', ')[2] + ', ' + term == 'Synge Street CBS, Wednesday, 18:30-19:30, 5th-6th Class, Spring 2020' or \
                                                   order['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "") + ', ' + order['lineItems']['variantOptions'][0]['value'].split(',')[0] + ', ' + order['lineItems']['variantOptions'][0]['value'].split(', ')[1] \
                                                   + ', ' + order['lineItems']['variantOptions'][0]['value'].split(', ')[2] + ', ' + term == 'Synge Street CBS, Wednesday, 17:30-18:30, 2nd-4th Class, Spring 2020':
                classLevel = '2nd-6th Class'
                time = '17:30-18:30'
            else:
                classLevel = order['lineItems']['variantOptions'][0]['value'].split(', ')[2].replace(' -','-')

                if 'Secondary' in classLevel:
                    classLevel = classLevel.title()
                time = order['lineItems']['variantOptions'][0]['value'].split(', ')[1].replace(' ', '')

            if 'to' in classLevel:
                classLevel = classLevel.replace(' to ', '-')

            name = order['lineItems']['customizations'][nameIndex]['value'].title().replace("\'", "")
            firstName = name.split()[0]

            if 'Mc' in name and 'Mc' not in firstName:
                index = name.find('Mc')
                name = name.replace("Mc", "").title()
                name = name[:index] + 'Mc' + name[index:]
            elif 'Mac' in name and 'Mac' not in firstName:
                index = name.find('Mac')
                name = name.replace("Mac", "").title()
                name = name[:index] + 'Mac' + name[index:]

            if not airtableStudentReg.search('Primary Key', name + ' (' + order['lineItems']['customizations'][dobIndex]['value'] + '), "' +
                                                           order['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "") + ', ' + order['lineItems']['variantOptions'][0]['value'].split(',')[0] + ', ' +
                                                           time + ', ' + classLevel + ', ' + term + '"'):

                print('Inserting ' + '"' + name + '", "' + order['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "") + ', ' + order['lineItems']['variantOptions'][0]['value'].split(',')[0] + ', ' +
                    time + ', ' + classLevel + ', ' + term + '" into Student Registration Table...')

                studentRecord = airtableStudent.search('Primary Key', name + ' (' +order['lineItems']['customizations'][dobIndex]['value'] + ')')

                classRecord = airtableClass.search('Class Name', order['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "") + ', ' + order['lineItems']['variantOptions'][0]['value'].split(',')[0] + ', ' + time
                                                   + ', ' + classLevel + ', ' + term)

                airtableStudentReg.insert({'Student': [studentRecord[0]['id']], 'Class': [classRecord[0]['id']], 'Contact Name': order['billingAddress']['firstName'].title() + ' ' + order['billingAddress']['lastName'].title(),
                                           'Contact Phone No.': order['billingAddress']['phone'],'Contact Email': order['customerEmail'], 'Other Details': order['lineItems']['customizations'][10]['value'], 'Photography Consent': photographyConsent,
                                           'Returning Student': returningStudent, 'School & Class': order['lineItems']['customizations'][6]['value']})

            prevOrderID = order['orderNumber']

def main():
    start = time.time()

    allOrdersList, endDate = ExportAllOrders()

    if allOrdersList:
        individualOrdersList = ExportIndividualOrders(allOrdersList)

        inventoryList = retrieveInventory()
        currentTermVariantList = findCurrentTermInInventory(inventoryList)
        groupedVariantList = splitVariantLists(currentTermVariantList)
        updateAirtableClassInfo(groupedVariantList)

        groupedOrderList = splitVenueLists(individualOrdersList)

        updateAirtableStudentInfo(groupedOrderList)
        updateAirtableStudentRegistrationInfo(groupedOrderList)

    print('\nAirtable is up to date')
    WriteLastGenerationDate(endDate)

    end = time.time()

    print(str(round(end - start, 2)) + ' secs')

if __name__ == '__main__':
    main()