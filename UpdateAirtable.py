import argparse
import os
import string
import time
import dateutil.parser
import datetime

from datetime import timedelta

from airtable_wrapper.Airtable import Airtable
from database.dao.DAO import DAO
from google_drive.GoogleDrive import GoogleDrive
from squarespace.Squarespace import Squarespace

parser = argparse.ArgumentParser()
parser.add_argument('squarespaceOrderApiKey')
parser.add_argument('squarespaceInventoryApiKey')
parser.add_argument('airtableApiKey')
parser.add_argument('slackApiKey')
args = parser.parse_args()

squarespaceOrderApiKey = args.squarespaceOrderApiKey
squarespaceInventoryApiKey = args.squarespaceInventoryApiKey

airtableApiKey = args.airtableApiKey

product_names_to_ignore = ['Custom payment amount', 'Online mini-camps']
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

def split_venue_lists(ordersList):
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
                if not DAO.search(airtable_venue_table, field_name, field_value):
                    DAO.insert(airtable_venue_table, {field_name: field_value})

            if 'Summer' in venueVariant:
                field_name = "Class Name"
                field_value = venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "") + ', ' \
                              + venueVariant.split('[')[1].split(',')[0] + ', ' \
                              + venueVariant.split(', ')[1].split(' (')[0] + ', ' \
                              + venueVariant.split(', ')[1].split('(')[1].split(')')[0] + ', ' \
                              + venueVariant.split(' - ')[0]
                if not DAO.search(airtable_class_table, field_name, field_value):
                    field_name = 'Name'
                    field_value = venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "")
                    venue = DAO.search(airtable_venue_table, field_name, field_value)
                    
                    fields = {'Term': venueVariant.split(' - ')[0],
                              'Venue': [venue[0]['id']],
                              'Week': venueVariant.split('[')[1].split(',')[0],
                              'Time': venueVariant.split(', ')[1].split(' (')[0],
                              'Age Group': venueVariant.split(', ')[1].split('(')[1].split(')')[0]
                              }
                    DAO.insert(airtable_class_table, fields)
                    print('Inserting "' + venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "") + ', ' + venueVariant.split('[')[1].split(',')[0] + ', ' + venueVariant.split(', ')[1].split(' (')[0] + ', ' + venueVariant.split(', ')[1].split('(')[1].split(')')[0] + ', ' + venueVariant.split(' - ')[0] + '" into Class Table')
            else:
                field_name = "Class Name"
                field_value = venueVariants[0].split('- ')[1].split(' [')[0].replace("'", "") + ', ' \
                              + venueVariant.split('[')[1].split(',')[0] + ', ' \
                              + venueVariant.split(', ')[1].split(',')[0] + ', ' \
                              + venueVariant.split(', ')[2].split(']')[0] + ', ' \
                              + venueVariant.split(' - ')[0]
                if not DAO.search(airtable_class_table, field_name, field_value):
                    if base_key == airtable_base_key_dict['Tech Clubs']:
                        venue = DAO.search(airtable_venue_table, 'Name', venueVariants[0].split('- ')[1].split(' [')[0].replace("'",""))
                        
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

                    DAO.insert(airtable_class_table, fields)

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
            name = handle_special_name_cases(name)
            dateOfBirth = order['lineItems']['customizations'][dobIndex]['value']

            field_name = 'Primary Key' 
            field_value = name + ' (' + dateOfBirth + ')'
            if not DAO.search(airtable_student_table, field_name, field_value):
                print('Inserting "' + name + '" into ' + keyList[valList.index(base_key)] + ' Student Table')

                fields = {'Name': name,
                          'Date of Birth': dateOfBirth
                          }
                DAO.insert(airtable_student_table, fields)

            prevOrderID = order['orderNumber']

def updateStudentRegistrationTable(orderList, subscriptionDetails, subscriptionTerm):
    print('\nUpdating Student Registration Information on Airtable...')

    added_order = False

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
            name = handle_special_name_cases(name)

            dateOfBirth = order['lineItems']['customizations'][dobIndex]['value']
            venue = order['lineItems']['productName'].split('- ')[1].split(',')[0].replace("'", "")
            day = order['lineItems']['variantOptions'][0]['value'].split(',')[0]

            if not DAO.search(airtable_student_registration_table, 'Primary Key', name + ' (' + dateOfBirth + '), "' + venue + ', ' + day + ', ' + time + ', ' + classLevel + ', ' + term + '"'):
                studentDetailList = []
                studentDetailList.append(name + ' (' + dateOfBirth + ')')
                studentDetailList.append(venue)
                studentDetailList.append(time)
                studentDetailList.append(day)
                if studentDetailList not in subscriptionDetails and [term] not in subscriptionTerm:
                    print('Inserting ' + '"' + name + '", "' + venue + ', ' + day + ', ' + time + ', ' + classLevel + ', ' + term + '" into Student Registration Table...')

                    added_order = True

                    studentRecord = airtable_student_table.search('Primary Key', name + ' (' + order['lineItems']['customizations'][dobIndex]['value'] + ')')

                    classRecord = airtable_class_table.search('Class Name', venue + ', ' + day + ', ' + time + ', ' + classLevel + ', ' + term)

                    DAO.insert(airtable_student_registration_table, {'Student': [studentRecord[0]['id']], 'Class': [classRecord[0]['id']], 'Contact Name': order['billingAddress']['firstName'].title() + ' ' + order['billingAddress']['lastName'].title(),
                                               'Contact Phone No.': order['billingAddress']['phone'],'Contact Email': order['customerEmail'], 'Other Details': order['lineItems']['customizations'][10]['value'], 'Photography Consent': photographyConsent,
                                               'Returning Student': returningStudent, 'School & Class': order['lineItems']['customizations'][6]['value']})

            prevOrderID = order['orderNumber']

    return added_order

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
                name = handle_special_name_cases(name)

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

                if not DAO.search(airtableSubscriptions, 'Primary Key', name + ' (' + dateOfBirth + '), ' + venue + ', ' + time + ', ' + day + ', ' + term):
                    print('Inserting ' + '"' + name + ' (' + dateOfBirth + '), ' + venue + ', ' + time + ', ' + day + ', ' + term + '" into Subscriptions Table...')

                    DAO.insert(airtableSubscriptions, {'Name': name,
                                                  'Date Of Birth': dateOfBirth,
                                                  'Term': term,
                                                  'Day of the Week': day,
                                                  'Time': time,
                                                  'Age Group': classLevel,
                                                  'Venue': venue})

def handle_special_name_cases(name):
    first_name = name.split()[0]

    if 'Mc' in name and 'Mc' not in first_name:
        index = name.find('Mc')
        name = name.replace("Mc", "").title()
        name = name[:index] + 'Mc' + name[index:]
    elif 'Mac' in name and 'Mac' not in first_name:
        index = name.find('Mac')
        name = name.replace("Mac", "").title()
        name = name[:index] + 'Mac' + name[index:]

    return name

def get_subscription_details():
    base_key = airtable_base_key_dict['Subscriptions']
    airtable_subscriptions_table = Airtable(base_key, 'Subscriptions', airtableApiKey)

    subscriptions = DAO.get_all(airtable_subscriptions_table)

    subscription_details = [subscription["fields"]["Primary Key"].split(', ')[0:4] for subscription in subscriptions]
    subscription_term = [subscription["fields"]["Primary Key"].split(', ')[4] for subscription in subscriptions]

    return subscription_details, subscription_term

def main():
    start = time.time()

    google_drive = GoogleDrive()

    squarespace = Squarespace(squarespaceOrderApiKey, squarespaceInventoryApiKey)
    orders = squarespace.get_orders_by_date(get_start_date(google_drive), get_end_date())

    if orders:
        inventory = squarespace.get_inventory()
        updateClassTable(inventory)

        orders = split_venue_lists(orders)

        updateStudentTable(orders)

        subscriptionDetails, subscriptionTerm = get_subscription_details()
        if updateStudentRegistrationTable(orders, subscriptionDetails, subscriptionTerm):
            updateSubscriptionsTable(orders)

    print('\nAirtable is up to date')

    write_end_date_to_file(get_end_date(), google_drive)

    slack = Slack(args.slackApiKey)
    slack.send_message('#airtable-last-updated', 'Last Update: ' + get_end_date())

    end = time.time()
    print(str(round(end - start, 2)) + ' secs')

if __name__ == '__main__':
    main()
