import subprocess, gspread, pdb
from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM
import pandas as pd
# Requires ttab https://www.npmjs.com/package/ttab#manual-installation

fileManager = FM()

fileManager.downloadData(fileManager.localCredentialDir)
gs = gspread.service_account(filename=fileManager.localCredentialSpreadsheet)
controllerGS = gs.open('Controller')
pi_ws = controllerGS.worksheet('RaspberryPi')
data = pi_ws.get_all_values()
dt = pd.DataFrame(data[1:], columns = data[0])

for row in dt.RaspberryPiID:
	print(row)
	subprocess.run(['ssh-keygen', '-t', 'rsa', '-f', '~/.ssh/id_rsa'])
	subprocess.run(['ssh-copy-id', 'pi@' + row + '.biosci.gatech.edu'])

#for row in dt.RaspberryPiID:
#	subprocess.run(['ttab', '-t', row, 'ssh', 'pi@' + row + '.biosci.gatech.edu'])
#ssh-keygen 
#ssh-copy-id pi@bt-t001.biosci.gatech.edu