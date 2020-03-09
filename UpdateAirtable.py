import argparse
import os
import string
import requests
import copy
import time
import dateutil.parser
import datetime

from datetime import timedelta
from builtins import any as b_any

from airtable_wrapper.Airtable import Airtable
from google_drive.GoogleDrive import GoogleDrive
from order.OrderPage import OrderPage
from order.OrderPages import OrderPages
from request.RequestLimit import RequestLimit
from squarespace.Squarespace import Squarespace
from squarespace.inventory.InventoryRetriever import InventoryRetriever

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

product_names_to_ignore = ['Custom payment amount']
airtable_base_key_dict = {'Oatlands College': 'appw2m4IGMCCW2AFd', 'St Pauls College': 'app6TZs7NzO5dYIap', 'St. Colmcilles CS': 'appFA3WwPypeQgg4o', 'Castleknock Community College': 'appqieHXlKvWWSfB4', 'Newbridge College':'app8XtrD48LCTs1fr',
                     'Synge Street CBS':'appVkqUpJ3p5UzdTO', 'Virtual Venue': 'appeAMZ0zlOSKGOc0', 'Tech Clubs': 'appZONEatk4ekDGFP', 'Subscriptions': 'app6o8RdxKplDEzuk', 'Summer Camps 2020': 'appgyHx1HXJGzLlfk'}
nonTechClubBases = ['Oatlands College', 'St Pauls College', 'St. Colmcilles CS', 'Castleknock Community College', 'Newbridge College', 'Synge Street CBS', 'Virtual Venue', 'Summer Camps 2020']

lastUpdateDateFilePath = os.path.dirname(os.path.abspath(__file__)) + '\LastClassListUpdateDate.txt'
lastUpdateDateID = '1JqP_9XCoeb8B8dlhyTYcuRRltr24CwSCnXyAfckAoPA'

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

def write_end_date_to_file(end_date, google_drive):
    with open(lastUpdateDateFilePath, 'w') as file:
        file.write(end_date)

    google_drive.editFile(lastUpdateDateFilePath, lastUpdateDateID, "application/vnd.google-apps.document")

def get_start_date(google_drive):
    google_drive.download_file(lastUpdateDateID, "text/plain", lastUpdateDateFilePath)

    with open(lastUpdateDateFilePath) as file:
        lastEndDate = dateutil.parser.parse(''.join([x for x in file.readlines()[0] if x in string.printable]))

    startDate = lastEndDate + timedelta(microseconds=1)

    return startDate.strftime(DATE_FORMAT)

def get_end_date():
    endDate = datetime.datetime.now()

    if time.daylight and time.localtime().tm_isdst > 0:
        endDate -= timedelta(hours=1)

    return endDate.strftime(DATE_FORMAT)

def getRequestWithRateLimit(apiURL, headers=None, params=None):
    requestLimit = RequestLimit(120, 60)

    try:
        with requestLimit, requests.get(apiURL, headers=headers, params=params) as response:
            return response.json(), None
    except Exception as e:
        print(e)
        return None, e

def ExportAllOrders(drive):
    pageNumber = 1
    orderList = []

    startDate = get_start_date(drive)
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
        for productName in product_names_to_ignore:
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
            for productName in product_names_to_ignore:
                if productName in responseJSON['result'][index]['lineItems'][0]['productName']:
                    skipOrder = True
                    break
            if not skipOrder and responseJSON['result'][index]['refundedTotal']['value'] == '0.00':
                orderList.append(responseJSON['result'][index])

        print('Page ' + str(pageNumber) + ' Order Request Completed.')

    return orderList, endDate

def organize_orders(allOrdersList):
    seperatedNameOrderList = []

    for order in allOrdersList:
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

def get_inventory():
    page_number = 1
    sign_up_class_list = []

    headers = {
        'Authorization': 'Bearer ' + squarespaceInventoryApiKey,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'
    }

    responseJSON, error = getRequestWithRateLimit(squarespaceInventoryApiURL, headers)

    for index in range(len(responseJSON['inventory'])):
        sign_up_class_list.append(responseJSON['inventory'][index])

    print('Page ' + str(page_number) + ' Inventory Request Completed.')

    while responseJSON['pagination']['hasNextPage'] == True:
        page_number += 1

        params = [
            ('cursor', responseJSON['pagination']['nextPageCursor'])
        ]

        responseJSON, error = getRequestWithRateLimit(squarespaceInventoryApiURL, headers, params)

        for index in range(len(responseJSON['inventory'])):
            sign_up_class_list.append(responseJSON['inventory'][index])

        print('Page ' + str(page_number) + ' Inventory Request Completed.')

    return sign_up_class_list

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

    return list(grouped.values())

def splitVenueLists(ordersList):
    grouped = {}
    for elem in ordersList:
        if "Summer" in elem['lineItems']['productName']:
            key = "Summer"
        else:
            key = elem['lineItems']['productName'].split('- ')[1].split(',')[0]
        grouped.setdefault(key, []).append(elem)

    return list(grouped.values())

def updateClassTable(currentTermVariantsList):
    print('\nUpdating Class Information on Airtable...')

    for venueVariants in currentTermVariantsList:

        if 'Summer' in venueVariants[0].split(' - ')[0]:
            venue_name = 'Summer Camps 2020'
            airtable_venue_table = Airtable(base_key, 'Venue', airtableApiKey)
        elif venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "") not in nonTechClubBases:
            venue_name = 'Tech Clubs'
            airtable_venue_table = Airtable(base_key, 'Venue', airtableApiKey)
        else:
            venue_name = venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "")
        
        base_key = airtable_base_key_dict[venue_name]

        airtable_class_table = Airtable(base_key, 'Class', airtableApiKey)

        for venueVariant in venueVariants:
            if base_key == airtable_base_key_dict['Tech Clubs'] or base_key == airtable_base_key_dict['Summer Camps 2020']:
                field_name = 'Name'
                field_value = venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "")
                if not airtable_venue_table.search(field_name, field_value):
                    airtable_venue_table.insert({field_name: field_value})

            if 'Summer' in venueVariant:
                field_name = "Class Name"
                field_value = venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "") + ', ' \
                              + venueVariant.split('[')[1].split(',')[0] + ', ' \
                              + venueVariant.split(', ')[1].split(' (')[0] + ', ' \
                              + venueVariant.split(', ')[1].split('(')[1].split(')')[0] + ', ' \
                              + venueVariant.split(' - ')[0]
                if not airtable_class_table.search(field_name, field_value):
                    field_name = 'Name'
                    field_value = venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "")
                    venue = airtable_venue_table.search(field_name, field_value)
                    
                    fields = {'Term': venueVariant.split(' - ')[0],
                              'Venue': [venue[0]['id']],
                              'Week': venueVariant.split('[')[1].split(',')[0],
                              'Time': venueVariant.split(', ')[1].split(' (')[0],
                              'Age Group': venueVariant.split(', ')[1].split('(')[1].split(')')[0]
                              }
                    airtable_class_table.insert(fields)
                    print('Inserting "' + venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "") + ', ' + venueVariant.split('[')[1].split(',')[0] + ', ' + venueVariant.split(', ')[1].split(' (')[0] + ', ' + venueVariant.split(', ')[1].split('(')[1].split(')')[0] + ', ' + venueVariant.split(' - ')[0] + '" into Class Table')
            else:
                field_name = "Class Name"
                field_value = venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "") + ', ' \
                              + venueVariant.split('[')[1].split(',')[0] + ', ' \
                              + venueVariant.split(', ')[1].split(',')[0] + ', ' \
                              + venueVariant.split(', ')[2].split(']')[0] + ', ' \
                              + venueVariant.split(' - ')[0]
                if not airtable_class_table.search(field_name, field_value):
                    if base_key == airtable_base_key_dict['Tech Clubs']:
                        venue = airtable_venue_table.search('Name',venueVariants[0].split('- ')[1].split(' [')[0].replace("'",""))
                        
                        fields = {'Term': venueVariant.split(' - ')[0],
                                  'Venue': [venue[0]['id']],
                                  'Day of the Week': venueVariant.split('[')[1].split(',')[0],
                                  'Time': venueVariant.split(', ')[1].split(',')[0],
                                  'Age Group': venueVariant.split(', ')[2].split(']')[0]
                                  }
                    else:
                        fields = {'Term': venueVariant.split(' - ')[0],
                                  'Venue': venueVariants[0].split('- ')[1].split(' [')[0].replace("'",""),
                                  'Day of the Week': venueVariant.split('[')[1].split(',')[0],
                                  'Time': venueVariant.split(', ')[1].split(',')[0],
                                  'Age Group': venueVariant.split(', ')[2].split(']')[0]
                                  }
                    
                    airtable_class_table.insert(fields)

                    print('Inserting "' + venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "") + ', ' + venueVariant.split('[')[1].split(',')[0] + ', ' + venueVariant.split(', ')[1].split(',')[0] + ', ' + venueVariant.split(', ')[2].split(']')[0] + ', ' + venueVariant.split(' - ')[0] + '" into Class Table')

def updateStudentTable(groupedOrderList):
    print('\nUpdating Student Information on Airtable...')

    for venueOrderList in groupedOrderList:
        if 'Summer' in venueOrderList[0]['lineItems']['productName']:
            venue_name = 'Summer Camps 2020'
        elif venueOrderList[0]['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "") not in nonTechClubBases:
            venue_name = 'Tech Clubs'
        else:
            venue_name = venueOrderList[0]['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "")
        
        base_key = airtable_base_key_dict[venue_name]

        airtable_student_table = Airtable(base_key, 'Student', airtableApiKey)

        prevOrderID = 0
        thirdOrder = False
        keyList = list(airtable_base_key_dict.keys())
        valList = list(airtable_base_key_dict.values())

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
            dateOfBirth = order['lineItems']['customizations'][dobIndex]['value']

            field_name = 'Primary Key' 
            field_value = name + ' (' + dateOfBirth + ')'
            if not airtable_student_table.search(field_name, field_value):
                print('Inserting "' + name + '" into ' + keyList[valList.index(base_key)] + ' Student Table')

                fields = {'Name': name,
                          'Date of Birth': dateOfBirth
                          }
                airtable_student_table.insert(fields)

            prevOrderID = order['orderNumber']

def updateStudentRegistrationTable(orderList, subscriptionDetails, subscriptionTerm):
    print('\nUpdating Student Registration Information on Airtable...')

    addAnOrder = False

    for venueOrderList in orderList:
        if 'Summer' in venueOrderList[0]['lineItems']['productName']:
            venue_name = 'Summer Camps 2020'
        elif venueOrderList[0]['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "") not in nonTechClubBases:
            venue_name = 'Tech Clubs'
        else:
            venue_name = venueOrderList[0]['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "")
        base_key = airtable_base_key_dict[venue_name]

        airtable_student_registration_table = Airtable(base_key, 'Student Registration', airtableApiKey)
        airtable_student_table = Airtable(base_key, 'Student', airtableApiKey)
        airtable_class_table = Airtable(base_key, 'Class', airtableApiKey)

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

            if not airtable_student_registration_table.search('Primary Key', name + ' (' + dateOfBirth + '), "' + venue + ', ' + day + ', ' + time + ', ' + classLevel + ', ' + term + '"'):
                studentDetailList = []
                studentDetailList.append(name + ' (' + dateOfBirth + ')')
                studentDetailList.append(venue)
                studentDetailList.append(time)
                studentDetailList.append(day)
                if studentDetailList not in subscriptionDetails and [term] not in subscriptionTerm:
                    print('Inserting ' + '"' + name + '", "' + venue + ', ' + day + ', ' + time + ', ' + classLevel + ', ' + term + '" into Student Registration Table...')

                    addAnOrder = True

                    studentRecord = airtable_student_table.search('Primary Key', name + ' (' + order['lineItems']['customizations'][dobIndex]['value'] + ')')

                    classRecord = airtable_class_table.search('Class Name', venue + ', ' + day + ', ' + time + ', ' + classLevel + ', ' + term)

                    airtable_student_registration_table.insert({'Student': [studentRecord[0]['id']], 'Class': [classRecord[0]['id']], 'Contact Name': order['billingAddress']['firstName'].title() + ' ' + order['billingAddress']['lastName'].title(),
                                               'Contact Phone No.': order['billingAddress']['phone'],'Contact Email': order['customerEmail'], 'Other Details': order['lineItems']['customizations'][10]['value'], 'Photography Consent': photographyConsent,
                                               'Returning Student': returningStudent, 'School & Class': order['lineItems']['customizations'][6]['value']})

            prevOrderID = order['orderNumber']

    return addAnOrder

def updateSubscriptionsTable(orderList):
    print('\nUpdating Subscription Information on Airtable...')

    for venueOrderList in orderList:
        from airtable import airtable

        appId = airtable_base_key_dict['Subscriptions']

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

def getSubscriptionDetails():
    base_key = airtable_base_key_dict['Subscriptions']
    airtable_subscriptions_table = Airtable(base_key, 'Subscriptions', airtableApiKey)

    subscriptions = airtable_subscriptions_table.get_all()

    subscriptionDetails = [subscription["fields"]["Primary Key"].split(', ')[0:4] for subscription in subscriptions]
    subscriptionTerm = [subscription["fields"]["Primary Key"].split(', ')[4] for subscription in subscriptions]

    return subscriptionDetails, subscriptionTerm

def main():
    start = time.time()

    google_drive = GoogleDrive()

    squarespace = Squarespace(squarespaceOrderApiKey, squarespaceInventoryApiKey)
    orders = squarespace.get_orders_by_date(get_start_date(google_drive), get_end_date())

    if orders:
        inventory_retriever = InventoryRetriever()
        inventory = inventory_retriever.get_inventory()
        updateClassTable(inventory)

        groupedOrderList = splitVenueLists(orders)

        updateStudentTable(groupedOrderList)

        subscriptionDetails, subscriptionTerm = getSubscriptionDetails()
        if updateStudentRegistrationTable(groupedOrderList, subscriptionDetails, subscriptionTerm):
            updateSubscriptionsTable(groupedOrderList)

    print('\nAirtable is up to date')

    # write_end_date_to_file(endDate, googleDrive)
    #
    # endDate = datetime.datetime.strptime(endDate, '%Y-%m-%dT%H:%M:%S.%fZ')
    #
    # slack = Slack(args.slackApiKey)
    # slack.sendMessage('#airtable-last-updated', 'Last Update: ' + endDate.strftime("%m/%d/%Y, %H:%M:%S"))

    end = time.time()
    print(str(round(end - start, 2)) + ' secs')

if __name__ == '__main__':
    main()
