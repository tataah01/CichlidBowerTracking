import platform, sys, os, shutil, datetime, subprocess, pdb, time, sendgrid, psutil
from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM
from cichlid_bower_tracking.helper_modules.log_parser import LogParser as LP
from cichlid_bower_tracking.helper_modules.googleController import GoogleController as GC
import pandas as pd
import numpy as np
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import *

import warnings
warnings.filterwarnings('ignore')
from PIL import Image
import matplotlib.image

sys.path.append(sys.path[0] + '/unit_scripts')
sys.path.append(sys.path[0] + '/helper_modules')

class CichlidTracker:
    def __init__(self):

        # Create email server
        with open(self.fileManager.localEmailCredentialFile) as f:
            my_api_key = [x.strip() for x in f.readlines()][0]

        self.sg = sendgrid.SendGridAPIClient(api_key=my_api_key)
       # self.personalization = sendgrid.Personalization()
       # self.personalization.add_to(sendgrid.To('bshi42@gatech.edu'))
       # for email in ['bshi42@gatech.edu', 'jtata6@gatech.edu']:
       #     self.personalization.add_bcc(sendgrid.Bcc(email))

        # 9: Await instructions
        
    def email_test(self):
        
            new_email = sendgrid.Mail(
                from_email='themcgrathlab@gmail.com', 
                subject= self.tankID + 'Test email', 
                html_content= 'Check the Controller sheet'
            )
            new_email.add_personalization(self.personalization)

            # Get a JSON-ready representation of the Mail object
            # Send an HTTP POST request to /mail/send
            response = self.sg.send(new_email)
