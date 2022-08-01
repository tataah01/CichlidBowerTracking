import subprocess,gspread,pdb, time
import pandas as pd

subprocess.call(['rclone', 'copy', 'cichlidVideo:McGrath/Apps/CichlidPiData/__CredentialFiles/','.'])

#from oauth2client.service_account import ServiceAccountCredentials


credentialFile = 'SAcredentials.json'

gs = gspread.service_account(filename=credentialFile)

controllerGS = gs.open('Controller')

column_name = 'Command'
tankID = 't001'

try:
	pi_ws = controllerGS.worksheet('RaspberryPi')
except gspread.exceptions.APIError as e:
	if e.response.status_code == 429:
		# Read requests per minute exceeded
		print('Read requests per minue exceeded')
		time.sleep(20) # How long to wait for read requests to exceed?
	else:
		print('gspread error of unknown nature')
		print(e)

while True:
	try:	
		data = pi_ws.get_all_values()
	except gspread.exceptions.APIError as e:
		if e.response.status_code == 429:
			# Read requests per minute exceeded
			print('Read requests per minue exceeded')
			time.sleep(20) # How long to wait for read requests to exceed?
		else:
			print('gspread error of unknown nature')
			print(e)

	dt = pd.DataFrame(data[1:], columns = data[0])
	if column_name not in dt.columns:
		print('Cant find column name in Controller: ' + column_name)
	if tankID not in dt.TankID.values:
		print('Cant find tankID')
	data = dt.loc[dt.TankID == 't001','Command']
	if len(data) > 1:
		print('TankID listed multiple times')
	print(data.values[0])
	pdb.set_trace()
	time.sleep(400)