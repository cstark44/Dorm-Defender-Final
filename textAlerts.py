import os
import twilio
from twilio.rest import Client

account_sid = ""
auth_token = ""

def sendMessage(to, message):
  to = "+1" + to
  client = Client(account_sid, auth_token)
  message = client.messages.create(
    body=message,
    from_="",
    to=to
  )
