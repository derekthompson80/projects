import requests

def send_text_message(phone_number, message):
    """
    Sends a text message to the specified phone number using Twilio.
    
    :param phone_number: Phone number to receive the message (e.g., '3025980093')
    :param message: Message content
    """
    # Replace with your actual Twilio credentials and phone numbers
    account_sid = 'ACe3919848fbc0df5a57cf4c645d9b796b'
    auth_token = '3e18320742c6a710afc1c7898bce9fa0'
    twilio_phone_number = '+18339875421'

    url = "https://api.twilio.com/2010-04-01/Accounts/{0}/Messages.json".format(account_sid)
    
    payload = {
        'To': phone_number,
        'From': twilio_phone_number,
        'Body': message
    }
    
    headers = {
        "Authorization": "Basic " + (account_sid + ":" + auth_token).encode('ascii').decode('base64'),
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(url, data=payload, headers=headers)
    
    if response.status_code == 201:
        print("Text message sent successfully.")
    else:
        print("Failed to send text message. Status code:", response.status_code)
        print(response.text)