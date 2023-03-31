import os
import json
from twilio.rest import Client
import boto3
from boto3.dynamodb.conditions import Attr, Key
import logging
from datetime import date

logger = logging.getLogger(__name__)

##LAMBDA CODE###
def handler(event, context):
     #query all the object locations from dynamodb table
     #dynamodb = boto3.client('dynamodb', region_name='us-east-1')

     dynamodb = boto3.resource('dynamodb')
     verses_table = dynamodb.Table('hope-in-numbers-daily-verses')
     clients_table = dynamodb.Table('isi-bible-verse-clients-db3-dev')
     #scan for a random verse
     
     today = date.today().strftime("%-m/%-d")
     daily_verse = verses_table.query(KeyConditionExpression=Key('month-day').eq(today))

     #scan for only subscribers to hope in numbers and pull out their phone numbers
     subscribers = clients_table.scan(FilterExpression=Attr('current_status').eq('HOPE-SMS'))
     subscriber_numbers = [k['phone_number'] for k in subscribers['Items']]

     #pick subject, copy, and verse
     #subject = verses['Items'][0]['Subject']
     copy = daily_verse['Items'][0]['copy']
     verse = daily_verse['Items'][0]['verse']

     #access twilio credentials through environment variables
     #get twilio auth token from AWS systems manager parameter store
     ssm = boto3.client('ssm')
     account_sid = ssm.get_parameter(
          Name='/twilio/garretson_technology_isi_subaccount/twilio_account_sid',
          WithDecryption=True
     )['Parameter']['Value']

     auth_token = ssm.get_parameter(
          Name='/twilio/garretson_technology_isi_subaccount/twilio_auth_token',
          WithDecryption=True
     )['Parameter']['Value']

     #create twilio client and create message
     #client = Client(api_key, api_secret, account_sid)
     client = Client(account_sid, auth_token)
     
     for phone_num in subscriber_numbers:
          try: 
               message = client.messages.create(
                         body='[Hope In Numbers]\n{}\n{}\nSTOP-SERVICES to unsubscribe'.format(copy, verse),
                         #from_='+19287678011',
                         from_='+16022231114',
                         send_as_mms=True,
                         #media_url=image_url,
                         to=phone_num
                    )
               logger.warning(message)

          except Exception as err:
               logger.warning("Couldn't send message to number %s.",
                        phone_num)
               #logger.warning(message)
               continue

     return {
          'statusCode': 200,
     }