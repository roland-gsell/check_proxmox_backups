#!/usr/bin/env python3
"""
Tool for checking all VM-Backups for Proxmox at once.

It reads the current backup schedule and storage config
to check the relevant backup logs.

Author: Roland Gsell
E-Mail: roland.gsell@siedl.net

2017 by Siedl Networks

enhanced by: IT-Native <support@it-native.com>

"""

from pyproxmox import prox_auth, pyproxmox
import urllib3
from datetime import datetime, date, timedelta
import fnmatch
import os
from optparse import OptionParser
import configparser
import string
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Nagios:
    ok = (0, 'OK')
    warning = (1, 'WARNING')
    critical = (2, 'CRITICAL')
    unknown = (3, 'UNKNOWN')


nagios = Nagios()


def nagiosExit(exit_code, msg=None):
    """Exit script with a str() message and an integer 'nagios_code', which is a sys.exit level."""
    if msg:
        print(exit_code[0], exit_code[1] + " - " + str(msg))
    sys.exit(exit_code[0])


parser = OptionParser()
parser.add_option("-u",
                  "--user",
                  dest="user",
                  default='',
                  help="User to connect to PVE")
parser.add_option("-p",
                  "--password",
                  dest="password",
                  default='',
                  help="Password for the API-User")
parser.add_option("-s",
                  "--host",
                  dest="host",
                  default='',
                  help="PVE-Server")
parser.add_option("-P",
                  "--path",
                  dest="path",
                  default='',
                  help="Path to VM Backup")
parser.add_option("-f",
                  "--file",
                  dest="apifile",
                  default='',
                  help="Path to API Configuration File")
parser.add_option("-d",
                  "--debug",
                  dest="debug",
                  default=False,
                  action="store_true",
                  help="Turn on debug mode")
(options, args) = parser.parse_args()


def printdebug(string):
    if options.debug:
        print(string)

def parse_days(days: str) -> list:
    # https://pve.proxmox.com/pve-docs/pve-admin-guide.html#chapter_calendar_events
    #check if contains weekday
    days_of_week = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    if days == '*':
        days = ','.join(days_of_week)
    
    if any(ext in days for ext in days_of_week):
        days = days.split(',')
        if len(days) == 1:
            days = days[0].split('..')
            start = days_of_week.index(days[0])
            end = days_of_week.index(days[1])
            if end < start:
                days = days_of_week[start : ] + days_of_week[ : end+1 ]
            else:
                days = days_of_week[start : end +1]
        return(days)
    else:
        printdebug("Not a valid day input!")


def parse_time(time: str) -> tuple[int,int]:
    # https://pve.proxmox.com/pve-docs/pve-admin-guide.html#chapter_calendar_events
    time = time.split('..')
    if len(time) == 2:
        print("range", time)
    else:
        time = time[0].split(',')
        if len(time) == 2:
            print("list", time)
        else:
            time = time[0].split(':')
            hours = int(time[0])
            minutes = int(time[1])
            if 0 <= hours < 24 and 0 <= minutes < 60:
                return (hours, minutes)
    #.split('/')

def getweekday(weekdaynumber):
    weekday = ''
    if weekdaynumber == 0:
        weekday = 'mon'
    elif weekdaynumber == 1:
        weekday = 'tue'
    elif weekdaynumber == 2:
        weekday = 'wed'
    elif weekdaynumber == 3:
        weekday = 'thu'
    elif weekdaynumber == 4:
        weekday = 'fri'
    elif weekdaynumber == 5:
        weekday = 'sat'
    elif weekdaynumber == 6:
        weekday = 'sun'
    return weekday


errorcodes = ['nobak', 'failed', 'running', '2old']
okcodes = ['ok']


def readlogfile(path, vmid, date, oneday2old=False):
    found = False
    backupok = False
    code = ''
    printdebug('Checking this pattern: ' + path + '/' + 'vzdump-*' + str(vmid) + '-' + date + '*.log')
    for filename in os.listdir(path):
        if fnmatch.fnmatch(filename, 'vzdump-*' + str(vmid) + '-' + date + '*.log'):
            printdebug('Checking Filename: ' + filename)
            try:
                with open(path + '/' + filename, 'r') as f:
                    found = True
                    if oneday2old:
                        printdebug("WARNING - Found backup, but older than expected: " + str(vmid))
                    printdebug('Found and could open: ' + filename)
                    try:
                        lastline = f.readlines()[-1]
                        printdebug(lastline)
                        if 'INFO: Finished Backup' in lastline:
                            printdebug("OK")
                            backupok = True
                            code = 'ok'
                        elif 'ERROR: ' in lastline:
                            if not backupok:
                                code = 'failed'
                                printdebug("Backup failed")
                        elif 'INFO: status:' in lastline:
                            if not backupok:
                                code = 'running'
                                printdebug("Backup currently running")
                        else:
                            if not backupok:
                                code = 'nobak'
                                printdebug("Error: " + str(vmid))
                    except Exception:
                        printdebug("Cant read file")
            except Exception:
                printdebug("Cant open file")
    return code, found


today = date.today()
datetimetoday = datetime.today()

# These values won't be altered later on
weekdaynumber_today = today.weekday()
weekday_today = getweekday(weekdaynumber_today)

printdebug("Today      : " + weekday_today)

host = ''
user = ''
password = ''

if options.apifile != '':
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(options.apifile)

    try:
        host = config.get('global', 'host')
        user = config.get('global', 'user')
        password = config.get('global', 'password')
    except Exception:
        message = 'Problem with api conf file'
        nagiosExit(nagios.unknown, str(message))
else:
    if options.user == '':
        message = 'No username given, use -u'
        nagiosExit(nagios.unknown, str(message))
    else:
        user = options.user

    if options.password == '':
        message = 'No Password given, use -p'
        nagiosExit(nagios.unknown, str(message))
    else:
        password = options.password

    if options.host == '':
        message = 'No host given, use -s'
        nagiosExit(nagios.unknown, str(message))
    else:
        host = options.host

auth = prox_auth(host, user, password)
prox = pyproxmox(auth)

# status = prox.getClusterStatus()
# print status
# config = prox.getClusterConfig()
# print config
# nextid = prox.getClusterVmNextId()
# print nextid

schedule = prox.getClusterBackupSchedule()
printdebug("Schedule(s):")
printdebug(str(schedule))
resources = prox.getClusterResources()

backup_all = False

vmid_status = {}
for i in schedule['data']:
    if i['enabled'] == 1:
        try:
            if i['all'] == 1:
                backup_all = True
                for j in resources['data']:
                    try:
                        vmid_status[int(j['vmid'])] = 'nochk'
                    except Exception:
                        pass
        except Exception:
            for vmid in i['vmid'].split(","):
                vmid_status[int(vmid)] = 'nochk'

for i in schedule['data']:
    if i['enabled'] == 1:
        try:
            if i['all'] == 1:
                try:
                    for exclude in i['exclude'].split(","):
                        vmid_status.pop(int(exclude), 0)
                except Exception:
                    pass
        except Exception:
            pass

# Debug: Add a non-existent VM
# vmid_status[200] = 'nochk'

# printdebug("VMID status before: " + str(vmid_status))

# Iterate over all schedules
for i in schedule['data']:
    weekdaynumber = today.weekday()
    weekday = getweekday(weekdaynumber)
    printdebug("------------")
    printdebug("Storage         : " + i['storage'])
    #check if dow or schedule is there
    if hasattr(i, 'dow') and hasattr(i, 'starttime'):
        printdebug('Weekdays        : ' + i['dow'])
            
        starttimetoday = datetime(datetimetoday.year,
                                datetimetoday.month,
                                datetimetoday.day,
                                int(i['starttime'][:2]),
                                int(i['starttime'][3:]))
        now = datetime(datetimetoday.year,
                    datetimetoday.month,
                    datetimetoday.day,
                    datetimetoday.hour,
                    datetimetoday.minute)
        printdebug("Start time      : " + str(i['starttime']))
        printdebug("Now             : " + str(now))
        if now < starttimetoday:
            printdebug("Start time not reached today - going back one day")
            if weekdaynumber == 0:
                weekdaynumber = 6
            else:
                weekdaynumber -= 1
            weekday = getweekday(weekdaynumber)
            date_to_check = date.today() - timedelta(days=1)
        else:
            printdebug("Start time reached today")
            date_to_check = date.today()

        try:
            printdebug("VM-IDs          : " + i['vmid'])
        except Exception:
            pass
        days = i['dow'].split(",")
        nrdays = []
        for day in days:
            if day == 'mon':
                backup_weekdaynumber = 0
            elif day == 'tue':
                backup_weekdaynumber = 1
            elif day == 'wed':
                backup_weekdaynumber = 2
            elif day == 'thu':
                backup_weekdaynumber = 3
            elif day == 'fri':
                backup_weekdaynumber = 4
            elif day == 'sat':
                backup_weekdaynumber = 5
            elif day == 'sun':
                backup_weekdaynumber = 6
            nrdays.append(backup_weekdaynumber)
        vmids = []

        # Debug: Add a non-existent VM
        # vmids.append(200)

        printdebug("Days of backup  : " + str(nrdays))
        if weekday in i['dow']:
            printdebug("Weekday found: " + weekday)
            printdebug("Date to check:     " + str(date_to_check))
        else:
            printdebug("Today no backup should be done.")
            days_to_go_back = 0
            for _ in range(7):
                # going back up to 7 times to find the first matching day to do the backup
                days_to_go_back += 1
                weekdaynumber -= 1
                if weekdaynumber < 0:
                    weekdaynumber = 6
                weekday = getweekday(weekdaynumber) #TODO better solution?
                if weekday in i['dow']:
                    printdebug("Weekday found: " + weekday)
                    date_to_check = date.today() - timedelta(days=days_to_go_back)
                    printdebug("Days to go back:  " + str(days_to_go_back))
                    printdebug("Date to check:     " + str(date_to_check))
                    break

    else:
        printdebug('PVE version >=7 backup definition')
        sched = i['schedule']
        sched = sched.split(' ')
        if len(sched) == 2:
            days = sched[0]
            days = parse_days(days)
            time = sched[1]
            time = parse_time(time)
        else:
            sched = sched[0]
            days = parse_days(sched)
            if days is None:
                days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
                time = parse_time(sched)

        starttimetoday = datetime(datetimetoday.year,
                                    datetimetoday.month,
                                    datetimetoday.day,
                                    int(time[0]),
                                    int(time[1]))
        now = datetime(datetimetoday.year,
                    datetimetoday.month,
                    datetimetoday.day,
                    datetimetoday.hour,
                    datetimetoday.minute)
        printdebug("Start time      : " + str(starttimetoday))
        printdebug("Now             : " + str(now))
        if now < starttimetoday:
            printdebug("Start time not reached today - going back one day")
            if weekdaynumber == 0:
                weekdaynumber = 6
            else:
                weekdaynumber -= 1
            weekday = getweekday(weekdaynumber)
            date_to_check = date.today() - timedelta(days=1)
        else:
            printdebug("Start time reached today")
            date_to_check = date.today()

        try:
            printdebug("VM-IDs          : " + i['vmid'])
        except Exception:
            pass
        nrdays = []
        for day in days:
            if day == 'mon':
                backup_weekdaynumber = 0
            elif day == 'tue':
                backup_weekdaynumber = 1
            elif day == 'wed':
                backup_weekdaynumber = 2
            elif day == 'thu':
                backup_weekdaynumber = 3
            elif day == 'fri':
                backup_weekdaynumber = 4
            elif day == 'sat':
                backup_weekdaynumber = 5
            elif day == 'sun':
                backup_weekdaynumber = 6
            nrdays.append(backup_weekdaynumber)
        vmids = []

        #Debug: Add a non-existent VM
        #vmids.append(200)

        printdebug("Days of backup  : " + str(nrdays))
        if weekday in days:
            printdebug("Weekday found: " + weekday)
            printdebug("Date to check:     " + str(date_to_check))
        else:
            printdebug("Today no backup should be done.")
            days_to_go_back = 0
            for _ in range(7):
                # going back up to 7 times to find the first matching day to do the backup
                days_to_go_back += 1
                weekdaynumber -= 1
                if weekdaynumber < 0:
                    weekdaynumber = 6
                weekday = getweekday(weekdaynumber) #TODO better solution?
                if weekday in days:
                    printdebug("Weekday found: " + weekday)
                    date_to_check = date.today() - timedelta(days=days_to_go_back)
                    printdebug("Days to go back:  " + str(days_to_go_back))
                    printdebug("Date to check:     " + str(date_to_check))
                    break

    storage = prox.getStorageConfig(i['storage'])
    printdebug("Storage-Config: " + str(storage))
    if options.path == '':
        path = storage['data']['path'] + '/dump'
    else:
        path = options.path
    for (vmid, status) in vmid_status.items():
        if not backup_all:
            # get the VM ids of the specific schedule:
            vmids_schedule = []

            for sched in i['vmid'].split(','):
                vmids_schedule.append(int(sched))

            # and check only those
            if vmid not in vmids_schedule:
                continue

        printdebug(" ")
        printdebug("Checking VM-ID: " + str(vmid))
        printdebug("Checking Path : " + str(path))
        date_underscore = (str(date_to_check)).replace( '-', '_')
        printdebug('Date with underscores: ' + date_underscore)

        if vmid_status[int(vmid)] != 'ok':
            vmid_status[int(vmid)], found = readlogfile(path, vmid, date_underscore)
        else:
            printdebug("log file already checked in another schedule and is ok: " + str(vmid))
            found = True

        if not found:
            # No luck?
            # Lets see if we find a backup, which is older and return a warning instead
            for j in range(1, 8):
                date_to_check_again = date_to_check - timedelta(days=j)
                date_underscore_again = (str(date_to_check_again)).replace('-', '_')

                if vmid_status[int(vmid)] != 'ok':
                    vmid_status[int(vmid)], found = readlogfile(path, vmid, date_underscore_again, True)
                    if vmid_status[int(vmid)] == 'ok':
                        vmid_status[int(vmid)] = '2old'
                        break
                    else:
                        found = False

        if not found or vmid_status[int(vmid)] not in okcodes:
            # didn't find anything or found a broken one
            # So let's find any backup which is newer and worked
            date_to_check_again = date_to_check + timedelta(days=1)
            while date_to_check_again <= date.today():
                # print(type(date_to_check_again))
                printdebug('Checking the next day: ' + str(date_to_check_again))
                date_underscore_again = str(date_to_check_again).replace('-', '_')

                if vmid_status[int(vmid)] != 'ok':
                    code_from_last_day = vmid_status[int(vmid)]
                    vmid_status[int(vmid)], found = readlogfile(path, vmid, date_underscore_again)
                # Didnt find a working backup on the next day, so keep the old status
                if vmid_status[int(vmid)] != 'ok':
                    vmid_status[int(vmid)] = code_from_last_day
                date_to_check_again = date_to_check_again + timedelta(days=1)

            # I tried my best, but no logfile here :(
            if not found:
                if vmid_status[int(vmid)] != 'ok' and vmid_status[int(vmid)] not in errorcodes:
                    vmid_status[int(vmid)] = 'nolog'
                    printdebug("Error - no log file found: " + str(vmid))

    printdebug("Storage-Path: " + path)
    printdebug("------------")
# print " "

# print vmid_status

OK_STATUS = True
UNKNOWN_STATUS = False
WARNING_STATUS = False
CRITICAL_STATUS = False

nagios_response = {'ok': '', 'failed': '', 'nobak': '', 'nolog': '', 'running': '', 'nochk': '', '2old': ''}
for vmid, status in vmid_status.items():
    printdebug(str(vmid) + status)
    vmid = str(vmid)
    if status == 'ok':
        nagios_response['ok'] += vmid + ','
    elif status == 'failed':
        OK_STATUS = False
        CRITICAL_STATUS = True
        nagios_response['failed'] += vmid + ','
    elif status == 'nobak':
        OK_STATUS = False
        CRITICAL_STATUS = True
        nagios_response['nobak'] += vmid + ','
    elif status == 'nolog':
        OK_STATUS = False
        CRITICAL_STATUS = True
        nagios_response['nolog'] += vmid + ','
    elif status == 'running':
        OK_STATUS = False
        WARNING_STATUS = True
        nagios_response['running'] += vmid + ','
    elif status == '2old':
        OK_STATUS = False
        WARNING_STATUS = True
        nagios_response['2old'] += vmid + ','
    elif status == 'nochk':
        OK_STATUS = False
        CRITICAL_STATUS = True
        nagios_response['nochk'] += vmid + ','
    else:
        OK_STATUS = False
        UNKNOWN_STATUS = True

# clean up unused key-value-pairs
new_nagios_response = {}
for key, value in nagios_response.items():
    if value != '':
        new_nagios_response[key] = value

if UNKNOWN_STATUS:
    message = 'Cannot read backup status - %s' % (new_nagios_response)
    nagiosExit(nagios.unknown, str(message))
elif CRITICAL_STATUS:
    message = 'At least one backup did not work - %s' % (new_nagios_response)
    nagiosExit(nagios.critical, str(message))
elif WARNING_STATUS:
    message = 'At least one backup is not finished yet or older than expected - %s' % (new_nagios_response)
    nagiosExit(nagios.warning, str(message))
else:
    message = '%s' % (new_nagios_response)
    nagiosExit(nagios.ok, str(message))
