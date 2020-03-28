import argparse
import io
import os
import string
import requests
import copy
import time
import dateutil.parser
import datetime
import pickle
import slack
from googleapiclient import errors, http
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import timedelta
from builtins import any as b_any
from threading import BoundedSemaphore as BoundedSemaphore, Timer

parser = argparse.ArgumentParser()
parser.add_argument('squarespaceOrderApiKey')
parser.add_argument('squarespaceInventoryApiKey')
parser.add_argument('airtableApiKey')
parser.add_argument('slackApiKey')
args = parser.parse_args()

squarespaceOrderApiKey = args.squarespaceOrderApiKey
squarespaceOrderApiURL = 'https://api.squarespace.com/1.0/commerce/orders'
squarespaceInventoryApiKey = args.squarespaceInventoryApiKey
squarespaceInventoryApiURL = 'https://api.squarespace.com/1.0/commerce/inventory'

airtableApiKey = args.airtableApiKey

slackClient = slack.WebClient(token=args.slackApiKey)

productNameIgnoreList = ['Custom payment amount', 'Online mini-camps']
airtableAppIdDict = {'Oatlands College': 'appw2m4IGMCCW2AFd', 'St Pauls College': 'app6TZs7NzO5dYIap', 'St. Colmcilles CS': 'appFA3WwPypeQgg4o', 'Castleknock Community College': 'appqieHXlKvWWSfB4', 'Newbridge College':'app8XtrD48LCTs1fr',
                     'Synge Street CBS':'appVkqUpJ3p5UzdTO', 'Virtual Venue': 'appeAMZ0zlOSKGOc0', 'Virtual Venue Mini-Camps': 'appeAMZ0zlOSKGOc0', 'Tech Clubs': 'appZONEatk4ekDGFP', 'Subscriptions': 'app6o8RdxKplDEzuk', 'Summer Camps 2020': 'appgyHx1HXJGzLlfk'}
nonTechClubBases = ['Oatlands College', 'St Pauls College', 'St. Colmcilles CS', 'Castleknock Community College', 'Newbridge College', 'Synge Street CBS', 'Virtual Venue', 'Virtual Venue Mini-Camps', 'Summer Camps 2020']

lastUpdateDateFileName = os.path.dirname(os.path.abspath(__file__)) + '\LastClassListUpdateDate.txt'
lastUpdateDateID = '1JqP_9XCoeb8B8dlhyTYcuRRltr24CwSCnXyAfckAoPA'

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

def WriteLastGenerationDate(endDate, drive):
    with open(lastUpdateDateFileName, 'w') as file:
        file.write(endDate)

    EditLastClassListGenerationDateFile(drive)

def ReadLastGenerationDate(drive):

    DownloadFromGoogleDrive(drive)

    with open(lastUpdateDateFileName) as file:
        lastEndDate = dateutil.parser.parse(''.join([x for x in file.readlines()[0] if x in string.printable]))

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

def ExportAllOrders(drive):
    pageNumber = 1
    orderList = []

    startDate = ReadLastGenerationDate(drive)
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

    if not responseJSON['result']:
        return None, endDate

    for index in range(len(responseJSON['result'])):
        skipOrder = False
        for productName in productNameIgnoreList:
            if productName in responseJSON['result'][index]['lineItems'][0]['productName'] or responseJSON['result'][index]['lineItems'][0]['productName'] in productName:
                skipOrder = True
                break
        if not skipOrder and responseJSON['result'][index]['refundedTotal']['value'] == '0.00':
            orderList.append(responseJSON['result'][index])

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
        if ('Spring' in inventoryList[i]['descriptor'].split('[')[0] or 'Summer' in inventoryList[i]['descriptor'].split('[')[0]) and ('\'20' in inventoryList[i]['descriptor'].split('[')[0] or '2020' in inventoryList[i]['descriptor'].split('[')[0]):
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
        if "Summer" in elem['lineItems']['productName']:
            key = "Summer"
        else:
            key = elem['lineItems']['productName'].split('- ')[1].split(',')[0]
        grouped.setdefault(key, []).append(elem)
    grouped = list(grouped.values())

    return grouped

def updateClassTable(currentTermVariantsList):
    print('\nUpdating Class Information on Airtable...')

    for venueVariants in currentTermVariantsList:
        from airtable import airtable

        if 'Summer' in venueVariants[0].split(' - ')[0]:
            appId = airtableAppIdDict['Summer Camps 2020']
            airtableVenue = airtable.Airtable(appId, 'Venue', airtableApiKey)
        elif venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "") not in nonTechClubBases:
            appId = airtableAppIdDict['Tech Clubs']
            airtableVenue = airtable.Airtable(appId, 'Venue', airtableApiKey)
        else:
            appId = airtableAppIdDict[venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "")]

        airtableClass = airtable.Airtable(appId, 'Class', airtableApiKey)

        for venueVariant in venueVariants:
            if appId == airtableAppIdDict['Tech Clubs'] or appId == airtableAppIdDict['Summer Camps 2020']:
                if not airtableVenue.search('Name',venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "")):
                    airtableVenue.insert({'Name': venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "")})

            if 'Summer' in venueVariant:
                if not airtableClass.search('Class Name',  venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "") + ', ' + venueVariant.split('[')[1].split(',')[0] + ', ' + venueVariant.split(', ')[1].split(' (')[0] + ', ' + venueVariant.split(', ')[1].split('(')[1].split(')')[0] + ', ' + venueVariant.split(' - ')[0]):
                    venue = airtableVenue.search('Name', venueVariants[0].split('- ')[1].split(' [')[0].replace("'", ""))
                    airtableClass.insert({'Term': venueVariant.split(' - ')[0],
                                          'Venue': [venue[0]['id']],
                                          'Week': venueVariant.split('[')[1].split(',')[0],
                                          'Time': venueVariant.split(', ')[1].split(' (')[0],
                                          'Age Group': venueVariant.split(', ')[1].split('(')[1].split(')')[0]})
                    print('Inserting "' + venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "") + ', ' + venueVariant.split('[')[1].split(',')[0] + ', ' + venueVariant.split(', ')[1].split(' (')[0] + ', ' + venueVariant.split(', ')[1].split('(')[1].split(')')[0] + ', ' + venueVariant.split(' - ')[0] + '" into Class Table')
            else:
                if not airtableClass.search('Class Name',
                                            venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "") + ', ' +
                                            venueVariant.split('[')[1].split(',')[0] + ', ' +
                                            venueVariant.split(', ')[1].split(',')[0] + ', ' +
                                            venueVariant.split(', ')[2].split(']')[0] + ', ' +
                                            venueVariant.split(' - ')[0]):
                    if appId == airtableAppIdDict['Tech Clubs']:
                        venue = airtableVenue.search('Name',
                                                     venueVariants[0].split('- ')[1].split(' [')[0].replace("'",
                                                                                                            ""))
                        airtableClass.insert({'Term': venueVariant.split(' - ')[0],
                                              'Venue': [venue[0]['id']],
                                              'Day of the Week': venueVariant.split('[')[1].split(',')[0],
                                              'Time': venueVariant.split(', ')[1].split(',')[0],
                                              'Age Group': venueVariant.split(', ')[2].split(']')[0]})
                    else:
                        airtableClass.insert({'Term': venueVariant.split(' - ')[0],
                                              'Venue': venueVariants[0].split('- ')[1].split(' [')[0].replace("'",
                                                                                                              ""),
                                              'Day of the Week': venueVariant.split('[')[1].split(',')[0],
                                              'Time': venueVariant.split(', ')[1].split(',')[0],
                                              'Age Group': venueVariant.split(', ')[2].split(']')[0]})

                    print('Inserting "' + venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "") + ', ' + venueVariant.split('[')[1].split(',')[0] + ', ' + venueVariant.split(', ')[1].split(',')[0] + ', ' + venueVariant.split(', ')[2].split(']')[0] + ', ' + venueVariant.split(' - ')[0] + '" into Class Table')

def updateStudentTable(groupedOrderList):
    print('\nUpdating Student Information on Airtable...')

    for venueOrderList in groupedOrderList:
        from airtable import airtable

        if 'Summer' in venueOrderList[0]['lineItems']['productName']:
            appId = airtableAppIdDict['Summer Camps 2020']
        elif venueOrderList[0]['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "") not in nonTechClubBases:
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
            name = handleSpecialNameCases(name)

            if not airtableStudent.search('Primary Key', name + ' (' + order['lineItems']['customizations'][dobIndex]['value'] + ')'):
                print('Inserting "' + name + '" into ' + keyList[valList.index(appId)] + ' Student Table')

                airtableStudent.insert({'Name': name,'Date of Birth': order['lineItems']['customizations'][dobIndex]['value']})

            prevOrderID = order['orderNumber']

def updateStudentRegistrationTable(orderList, subscriptionDetails, subscriptionTerm):
    print('\nUpdating Student Registration Information on Airtable...')

    addAnOrder = False

    for venueOrderList in orderList:
        from airtable import airtable

        if 'Summer' in venueOrderList[0]['lineItems']['productName']:
            appId = airtableAppIdDict['Summer Camps 2020']
        elif venueOrderList[0]['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "") not in nonTechClubBases:
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
            name = handleSpecialNameCases(name)

            dateOfBirth = order['lineItems']['customizations'][dobIndex]['value']
            venue = order['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "")
            day = order['lineItems']['variantOptions'][0]['value'].split(',')[0]

            if 'Virtual Venue Mini-Camps' in order['lineItems']['productName']:
                day = 'All Week'
                time = order['lineItems']['variantOptions'][0]['value'].split(', ')[0]
                if '11:00-12:00' in time:
                    time = '12:00-13:00'
                classLevel = order['lineItems']['variantOptions'][0]['value'].split(', ')[1]
                if 'Secondary School Students' in classLevel:
                    classLevel = 'Secondary School'

            if not airtableStudentReg.search('Primary Key', name + ' (' + dateOfBirth + '), "' + venue + ', ' + day + ', ' + time + ', ' + classLevel + ', ' + term + '"'):
                studentDetailList = []
                studentDetailList.append(name + ' (' + dateOfBirth + ')')
                studentDetailList.append(venue)
                studentDetailList.append(time)
                studentDetailList.append(day)
                if studentDetailList not in subscriptionDetails and [term] not in subscriptionTerm:
                    print('Inserting ' + '"' + name + '", "' + venue + ', ' + day + ', ' + time + ', ' + classLevel + ', ' + term + '" into Student Registration Table...')

                    addAnOrder = True

                    studentRecord = airtableStudent.search('Primary Key', name + ' (' + order['lineItems']['customizations'][dobIndex]['value'] + ')')

                    classRecord = airtableClass.search('Class Name', venue + ', ' + day + ', ' + time + ', ' + classLevel + ', ' + term)

                    airtableStudentReg.insert({'Student': [studentRecord[0]['id']], 'Class': [classRecord[0]['id']], 'Contact Name': order['billingAddress']['firstName'].title() + ' ' + order['billingAddress']['lastName'].title(),
                                               'Contact Phone No.': order['billingAddress']['phone'],'Contact Email': order['customerEmail'], 'Other Details': order['lineItems']['customizations'][10]['value'], 'Photography Consent': photographyConsent,
                                               'Returning Student': returningStudent, 'School & Class': order['lineItems']['customizations'][6]['value']})

            prevOrderID = order['orderNumber']

    return addAnOrder

def updateSubscriptionsTable(orderList):
    print('\nUpdating Subscription Information on Airtable...')

    for venueOrderList in orderList:
        from airtable import airtable

        appId = airtableAppIdDict['Subscriptions']

        airtableSubscriptions = airtable.Airtable(appId, 'Subscriptions', airtableApiKey)

        prevOrderID = 0
        thirdOrder = False

        for order in venueOrderList:
            if 'Subscription' in order['lineItems']['productName']:
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
                name = handleSpecialNameCases(name)

                dateOfBirth = order['lineItems']['customizations'][dobIndex]['value']

                time = order['lineItems']['variantOptions'][0]['value'].split(', ')[1].replace(' ', '')

                classLevel = order['lineItems']['variantOptions'][0]['value'].split(', ')[2].replace(' -', '-')

                if 'Secondary' in classLevel:
                    classLevel = classLevel.title()

                if 'to' in classLevel:
                    classLevel = classLevel.replace(' to ', '-')

                day = order['lineItems']['variantOptions'][0]['value'].split(',')[0]

                venue = order['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "")

                if ('Autumn 2019' in order['lineItems']['productName'] and 'Spring 2020' in order['lineItems']['productName']) or ('Autumn \'19' in order['lineItems']['productName'] and 'Spring \'20' in order['lineItems']['productName']):
                    term = 'Autumn 2019 / Spring 2020'
                elif 'Autumn 2019' in order['lineItems']['productName'] or 'Autumn \'19' in order['lineItems']['productName']:
                    term = 'Autumn 2019'
                elif 'Spring 2020' in order['lineItems']['productName'] or 'Spring \'20' in order['lineItems']['productName']:
                    term = 'Spring 2020'

                if not airtableSubscriptions.search('Primary Key', name + ' (' + dateOfBirth + '), ' + venue + ', ' + time + ', ' + day + ', ' + term):
                    print('Inserting ' + '"' + name + ' (' + dateOfBirth + '), ' + venue + ', ' + time + ', ' + day + ', ' + term + '" into Subscriptions Table...')

                    airtableSubscriptions.insert({'Name': name,
                                                  'Date Of Birth': dateOfBirth,
                                                  'Term': term,
                                                  'Day of the Week': day,
                                                  'Time': time,
                                                  'Age Group': classLevel,
                                                  'Venue': venue})

def handleSpecialNameCases(name):
    firstName = name.split()[0]

    if 'Mc' in name and 'Mc' not in firstName:
        index = name.find('Mc')
        name = name.replace("Mc", "").title()
        name = name[:index] + 'Mc' + name[index:]
    elif 'Mac' in name and 'Mac' not in firstName:
        index = name.find('Mac')
        name = name.replace("Mac", "").title()
        name = name[:index] + 'Mac' + name[index:]

    return name

def AccessGoogleDrive():
    creds = None

    SCOPES = ['https://www.googleapis.com/auth/drive']

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

def UploadToGoogleDrive(drive):
    file_metadata = {'name': lastUpdateDateFileName}
    media = MediaFileUpload(lastUpdateDateFileName,
                            mimetype='text/plain')
    drive.files().create(body=file_metadata, media_body=media, fields='id').execute()

def EditLastClassListGenerationDateFile(drive):
    file_metadata = {'name': 'LastClassListUpdateDate'}
    media = MediaFileUpload(lastUpdateDateFileName,
                            mimetype='application/vnd.google-apps.document')

    file = drive.files().update(fileId=lastUpdateDateID, body=file_metadata, media_body=media).execute()

def DownloadFromGoogleDrive(drive):
    request = drive.files().export(fileId=lastUpdateDateID, mimeType='text/plain')

    localFD = io.FileIO(lastUpdateDateFileName, mode='wb')

    mediaRequest = http.MediaIoBaseDownload(localFD, request)

    while True:
        try:
            downloadProgress, done = mediaRequest.next_chunk()
        except errors.HttpError as error:
            print('An error occurred: %s' % error)
            return
        if downloadProgress:
            print('Download Progress: %d%%' % int(downloadProgress.progress() * 100))
        if done:
            print('Download Complete')
            return

def sendSlackMessage(channel, message):
    print('\nSending slack message: ' + message)

    response = slackClient.chat_postMessage(channel=channel,text=message)

def getSubscriptionDetails():
    from airtable import airtable

    appId = airtableAppIdDict['Subscriptions']

    airtableSubscriptions = airtable.Airtable(appId, 'Subscriptions', airtableApiKey)

    subscriptions = airtableSubscriptions.get_all()

    subscriptionDetails = [subscription["fields"]["Primary Key"].split(', ')[0:4] for subscription in subscriptions]
    subscriptionTerm = [subscription["fields"]["Primary Key"].split(', ')[4] for subscription in subscriptions]

    return subscriptionDetails, subscriptionTerm

def main():
    start = time.time()

    drive = AccessGoogleDrive()

    allOrdersList, endDate = ExportAllOrders(drive)

    if allOrdersList:
        inventoryList = retrieveInventory()
        currentTermVariantList = findCurrentTermInInventory(inventoryList)
        groupedVariantList = splitVariantLists(currentTermVariantList)
        updateClassTable(groupedVariantList)

        individualOrdersList = ExportIndividualOrders(allOrdersList)
        groupedOrderList = splitVenueLists(individualOrdersList)

        updateStudentTable(groupedOrderList)

        subscriptionDetails, subscriptionTerm = getSubscriptionDetails()
        if updateStudentRegistrationTable(groupedOrderList, subscriptionDetails, subscriptionTerm):
            updateSubscriptionsTable(groupedOrderList)

    print('\nAirtable is up to date')

    WriteLastGenerationDate(endDate, drive)

    endDate = datetime.datetime.strptime(endDate, '%Y-%m-%dT%H:%M:%S.%fZ')
    sendSlackMessage('#airtable-last-updated', 'Last Update: ' + endDate.strftime("%m/%d/%Y, %H:%M:%S"))

    end = time.time()

    print(str(round(end - start, 2)) + ' secs')

if __name__ == '__main__':
    main()
