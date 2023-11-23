from openai import OpenAI
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
    #get twilio auth token from AWS systems manager parameter store
    ssm = boto3.client('ssm')

    twilio_account_sid = ssm.get_parameter(
        Name='/twilio/isiaccount/twilio_account_sid',
        WithDecryption=True
    )['Parameter']['Value']

    twilio_auth_token = ssm.get_parameter(
        Name='/twilio/isiaccount/twilio_auth_token',
        WithDecryption=True
    )['Parameter']['Value']

    openai_organization_id = ssm.get_parameter(
        Name='/openai/isi_devo_gpt/organization_id',
    )['Parameter']['Value']

    openai_organization_id = ssm.get_parameter(
            Name='/openai/isi_devo_gpt/organization_id',
        )['Parameter']['Value']
    
    openai_api_key = ssm.get_parameter(
            Name='/openai/isi_devo_gpt/api_key',
            WithDecryption=True
        )['Parameter']['Value']

    # start OpenAI interaction
    openai_client = OpenAI(
        organization=openai_organization_id,
        api_key=openai_api_key
    )

    # create Twilio client
    twilio_client = Client(twilio_account_sid, twilio_auth_token)

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
    devo_msg = get_devo(openai_client, verse, copy)

    for phone_num in subscriber_numbers:
         try: 
              message = twilio_client.messages.create(
                        messaging_service_sid='MGe8378c0c9e461b6c628995ba22ed4444',
                        body='[Hope In Numbers]\n\n{}\n{}\n\n{}\n\n"STOP-SERVICES" to unsubscribe. Try "DAILY-IMAGE" or "DAILY-SMS"'.format(copy, verse, devo_msg),
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

def get_devo(openai_client, verse, copy):
    # This code is for v1 of the openai package: pypi.org/project/openai

    response = openai_client.chat.completions.create(
    model="gpt-4-1106-preview",
    messages=[
        {
        "role": "system",
        "content": "You are an experienced Christian leader."
        },
        {
        "role": "user",
        "content": f"Short devotional (max 7 sentences) on Bible verse: {copy} {verse}"
        }
    ],
    temperature=1,
    max_tokens=512,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0
    )

    devo_msg = response.choices[0].message.content
    return devo_msg
