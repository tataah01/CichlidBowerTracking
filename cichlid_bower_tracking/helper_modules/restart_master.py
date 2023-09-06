import platform, sys, os, shutil, datetime, subprocess, pdb, time, sendgrid, psutil
from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM
from cichlid_bower_tracking.helper_modules.googleController import GoogleController as GC
import csv

'''
when started
open error_log.txt
determine if error required restart
if error required restart
    determine pi ID
    check google controller sheet for PI ID
        if status is awaiting command, set to running. Append comment - "edited controller sheet"
    append date/time of completion. Append "nothing to do" if comment not "edited controller sheet"
'''
class RestartMaster():
    def __init__(self):
        
        self.fileManager = FM()
        self.fileManager.downloadData(self.fileManager.localCredentialDir)
        self.googleController = GC(self.fileManager.localCredentialSpreadsheet)
        self.tankID = self.googleController.tankID
        
        is_restarted = self.open_logs # 1 true 0 false
        comment = 'Nothing to do'
        
        if is_restarted == True:
            command, projectID, analysisID = self._returnCommand()
            if command == 'AwaitingCommand':
                self.googleController.modifyPiGS('Status', 'Running')
                comment = 'Edited controller sheet'
                
        self.write_logs(comment)

    def open_logs(self):
        with open(self.fileManager.localPiErrorFile, 'r', encoding='UTF8') as f:
            f.seek(-2,2)
            var = f.read(1)
        if var == 1:
            return True
        else:
            return False
        
    def write_logs(self,comment):
        time = time.time()
        data = [time, comment]
        with open(self.fileManager.localPiErrorFile, 'w', encoding='UTF8') as f:
            writer = csv.writer(f)
            writer.writerow(data)
        
    def _returnCommand(self): #this is a copy from cichlid_tracker. Could be better
        command, projectID, analysisID = self.googleController.getPiGS(['Command','ProjectID','AnalysisID'])
        return command, projectID, analysisID