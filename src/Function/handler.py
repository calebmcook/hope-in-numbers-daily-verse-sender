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
     subscribers = clients_table.scan(FilterExpression=Attr('current_status').eq('HOPE-SMS')|Attr('current_status').eq('ALL'))
     subscriber_numbers = [k['phone_number'] for k in subscribers['Items']]

     #pick subject, copy, and verse
     #subject = verses['Items'][0]['Subject']
     copy = daily_verse['Items'][0]['copy']
     verse = daily_verse['Items'][0]['verse']

     #access twilio credentials through environment variables
     #get twilio auth token from AWS systems manager parameter store
     ssm = boto3.client('ssm')
     account_sid = ssm.get_parameter(
          Name='/twilio/isiaccount/twilio_account_sid',
          WithDecryption=True
     )['Parameter']['Value']

     auth_token = ssm.get_parameter(
          Name='/twilio/isiaccount/twilio_auth_token',
          WithDecryption=True
     )['Parameter']['Value']

     #create twilio client and create message
     #client = Client(api_key, api_secret, account_sid)
     client = Client(account_sid, auth_token)
     
     for phone_num in subscriber_numbers:
          try: 
               message = client.messages.create(
                        messaging_service_sid='MGe8378c0c9e461b6c628995ba22ed4444',
                        body='[Hope In Numbers]\n{}\n{}\n"STOP-SERVICES" to unsubscribe. Try "DAILY-IMAGE" or "HOPE-SMS"'.format(copy, verse),
                        send_as_mms=True,
                        to=phone_num
               )
               logger.warning(message)
               pass

          except Exception as err:
               logger.warning("Couldn't send message to number %s.",
                        phone_num)
               continue

     return {
          'statusCode': 200
     }