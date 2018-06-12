#change this to the location you want to save the retrieved files
save_dir = ""

import requests
import socket
import json
import os
from time import sleep
from jnpr.junos import Device
import jnpr.junos
#for user prompt to enter passwords 
from getpass import getpass
#used to parse the xml
from lxml import etree
import sys
from jnpr.junos.factory.factory_loader import FactoryLoader
import time
# used for the ssh/scp portion
import paramiko

#function to convert xml to string and strip some tags to make it emulate cli output
def convert_etree_to_string(etree_input):
	if isinstance(etree_input, basestring) == False:
		etree_input = etree.tostring(etree_input)
		etree_input = etree_input.replace('<output>', '')
		etree_input = etree_input.replace("</output>", "")
		etree_input = etree_input.replace("<configuration-text>", "")
		etree_input = etree_input.replace("</configuration-text>", "")
		#print contents
		return etree_input
	else:
		return etree_input		

def get_support_info(dev, ticket_ID):
# get support info and logs using rpc
	support_info = convert_etree_to_string(dev.rpc.get_support_information({'format':'text'}))
	logfilename = "/var/tmp/" + ticket_ID + " re0.tgz"
	dev.rpc.file_archive(compress = True, source = "/var/log/*", destination = logfilename)
	print "Created " + logfilename
	devicefacts = dev.facts
	hostname = devicefacts['hostname'].replace("'","")
	rsi_filename = directory + hostname + " " + "RSI"
	print rsi_filename
	with open(rsi_filename, "wb") as rsi_file:
		rsi_file.write(support_info)
		print "Wrote file " + rsi_file
		rsi_file.close()
		
#function to delete logs off router
def delete_logs(dev,ticket_ID):
	# delete support info and logs using rpc
	logfilename = "/var/tmp/" + ticket_ID + "re0.tgz"
	dev.rpc.file_delete(path = logfilename)
	print "Deleted " + logfilename
	
#paramiko stuff for ssh
def sftp_copy(router_address,user,passwd, ticket_ID):
	#make progress status 
	def printTotals(transferred, toBeTransferred):
		print "Transferred: {0}\tOut of: {1}".format(transferred, toBeTransferred)
	#set ssh client
	ssh_client = paramiko.SSHClient()
	#allow auto accept of remote ssh keys (otherwise connection will fail for new hosts)
	ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	#initiate the connection
	ssh_client.connect(hostname=router_address,username=user,password=passwd)
	ftp_client=ssh_client.open_sftp()
	#set the name of the file to copy from the router
	remotefilename = "/var/tmp/" + ticket_ID + " re0.tgz"
	#set name of file once its copied on box
	localfilename = str(directory) + "re0.tgz"
	print "local file name is ", localfilename
	#actually copy the file along with status
	ftp_client.get(remotefilename,localfilename,callback=printTotals)
	ftp_client.close()	
		
#function to connect to devices, and then run the check_interface function)			
def get_data(ipaddress, username, passwd,action):
	#check to see if netconf is reachable, otherwise timeout after the value (in seconds)
	Device.auto_probe = 1
	#create device object
	dev = Device(host=ipaddress, user=username, password=passwd, port = "22" )
	#connet to device
	try:
		dev.open()
		print("\nNETCONF connection to %s opened!" %ipaddress)
		print("Beginning data collection...\n")
		#either collect or delete data depending on what needs to be done
		if action == "create":
			get_support_info(dev,ticket_ID)
		elif action == "delete":
			delete_logs(dev,ticket_ID)
		
		print("\nOperation complete.")
		dev.close()
		print("NETCONF connection to %s is now closed.\n" %ipaddress)
	#if probe times out and raises a probe error
	except jnpr.junos.exception.ProbeError as e: 
		print("NETCONF connection to %s is not reachable, moving on.." %ipaddress)
	#any other error
	except Exception as e:
		print (e)

#user inputs
user = raw_input("Username: ")	
passwd = getpass("Device password: ")
ticket_ID = raw_input("Ticket ID: ")
router_address = raw_input("Router IP Address: ")

#check if directory exists, if not make it
directory = save_dir + ticket_ID + "/"
if not os.path.exists(directory):
    os.makedirs(directory)

#start timer for collection stats
start_time = time.time()

#run get_data function to actually get data
get_data(router_address,user,passwd,"create")
#run sftp copy function to copy data 
sftp_copy(router_address,user,passwd,ticket_ID)
#run get data function to remove log files from juniper
get_data(router_address,user,passwd,"delete")

#calculate time it took to collect data
print "Data collection took", round(time.time() - start_time,2), "seconds to run\n"
