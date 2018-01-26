"""
Tool for checking all VM-Backups for Proxmox at once.

It reads the current backup schedule and storage config
to check the relevant backup logs.

Author: Roland Gsell
E-Mail: roland.gsell@siedl.net

2017 by Siedl Networks

"""

from pyproxmox import prox_auth, pyproxmox
import urllib3
from datetime import datetime, date, timedelta
import fnmatch
import os
from optparse import OptionParser
import string

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

UNKNOWN = -1
OK = 0
WARNING = 1
CRITICAL = 2

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
(options, args) = parser.parse_args()

debug = True


def printdebug(string):
    if debug:
        print(string)


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


def readlogfile(path, vmid, date, oneday2old=False):
    found = False
    backupok = False
    code = ''
    for filename in os.listdir(path):
        if fnmatch.fnmatch(filename, 'vzdump-qemu-' + str(vmid) + '-' + date + '*.log'):
            printdebug('Checking Filename: ' + filename)
            try:
                f = open(path + '/' + filename, 'r')
                found = True
                if oneday2old:
                    printdebug("WARNING - Found backup, but 1 day older than expected: " + str(vmid))
                printdebug('Found and could open: ' + filename)
                try:
                    lastline = f.readlines()[-1]
                    printdebug(lastline)
                    if 'INFO: Finished Backup' in lastline:
                        printdebug("OK")
                        backupok = True
                        code = 'ok'
                    elif 'INFO: status:' in lastline:
                        if not backupok:
                            code = 'running'
                            printdebug("Backup currently running")
                    else:
                        if not backupok:
                            code = 'nobak'
                            printdebug("Error: " + str(vmid))
                finally:
                    f.close()
            except Exception:
                printdebug("Cant open file")
    return code, found


today = date.today()
datetimetoday = datetime.today()

# These values will be altered later, depending if a backup should be done today or not
weekdaynumber = today.weekday()
weekday = getweekday(weekdaynumber)

# These values won't be altered later on
weekdaynumber_today = weekdaynumber
weekday_today = weekday

printdebug("Today      : " + weekday)

host = ''
user = ''
password = ''

if options.apifile != '':
    with open(options.apifile, 'r') as f:
        for line in f:
            if line.startswith('hostaddress'):
                host = line[12:-1]
            if line.startswith('user'):
                user = line[5:-1]
            if line.startswith('pass'):
                password = line[5:-1]
    if user == '' or password == '' or host == '':
        print 'UNKNOWN - Problem with api conf file'
        raise SystemExit("UNKNOWN")
else:
    if options.user == '':
        print 'UNKNOWN - No username given, use -u'
        raise SystemExit("UNKNOWN")
    else:
        user = options.user

    if options.password == '':
        print 'UNKNOWN - No Password given, use -p'
        raise SystemExit("UNKNOWN")
    else:
        password = options.password

    if options.host == '':
        print 'UNKNOWN - No host given, use -s'
        raise SystemExit("UNKNOWN")
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

vmid_status = {}
for i in schedule['data']:
    if i['enabled'] == '1':
        try:
            if i['all'] == 1:
                for j in resources['data']:
                    try:
                        vmid_status[int(j['vmid'])] = 'nochk'
                    except Exception:
                        pass
        except Exception:
            for vmid in i['vmid'].split(","):
                vmid_status[int(vmid)] = 'nochk'

for i in schedule['data']:
    if i['enabled'] == '1':
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
    printdebug("------------")
    printdebug("Storage         : " + i['storage'])
    printdebug("Weekdays        : " + i['dow'])
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

    # printdebug("VM-IDs          : " + str(vmids))
    printdebug("Days of backup  : " + str(nrdays))
    printdebug("Highest day     : " + str(max(nrdays)))
    if weekday in i['dow']:
        printdebug("Weekday found: " + weekday)
        printdebug("Date to check:     " + str(date_to_check))
    else:
        printdebug("Today no backup should be done.")
        days_to_go_back = 7 - max(nrdays) + weekdaynumber_today
        if days_to_go_back >= 7:
            days_to_go_back -= 7
        printdebug("Days to go back:  " + str(days_to_go_back))
        date_to_check = date.today() - timedelta(days=days_to_go_back)
        printdebug("Date to check:    " + str(date_to_check))
    storage = prox.getStorageConfig(i['storage'])
    printdebug("Storage-Config: " + str(storage))
    if options.path == '':
        path = storage['data']['path'] + '/dump'
    else:
        path = options.path
    for (vmid, status) in vmid_status.iteritems():
        printdebug("Checking VM-ID: " + str(vmid))
        date_underscore = string.replace(str(date_to_check), '-', '_')
        printdebug('Date with underscores: ' + date_underscore)

        if vmid_status[int(vmid)] != 'ok':
            vmid_status[int(vmid)], found = readlogfile(path, vmid, date_underscore)
        else:
            printdebug("log file already checked in another schedule and is ok: " + str(vmid))
            found = True

        if not found:
            # No luck?
            # Lets see if we find a backup, which is one day older and return a warning instead
            date_to_check_again = date_to_check - timedelta(days=1)
            date_underscore_again = string.replace(str(date_to_check_again), '-', '_')

            if vmid_status[int(vmid)] != 'ok':
                vmid_status[int(vmid)], found = readlogfile(path, vmid, date_underscore_again, True)
                if vmid_status[int(vmid)] == 'ok':
                    vmid_status[int(vmid)] = '1day2old'
                else:
                    found = False

        if not found:
            # didn't find anything
            # So let's find any backup which is newer
            date_to_check_again = date_to_check + timedelta(days=1)
            while date_to_check_again < date.today():
                # print(type(date_to_check_again))
                printdebug('Checking the next day: ' + str(date_to_check_again))
                date_underscore_again = string.replace(str(date_to_check_again), '-', '_')

                if vmid_status[int(vmid)] != 'ok':
                    vmid_status[int(vmid)], found = readlogfile(path, vmid, date_underscore_again)
                date_to_check_again = date_to_check_again + timedelta(days=1)

            # I tried my best, but no logfile here :(
            if not found:
                if vmid_status[int(vmid)] != 'ok':
                    vmid_status[int(vmid)] = 'nolog'
                    printdebug("Error - no log file found: " + str(vmid))

    printdebug("Storage-Path: " + storage['data']['path'])
    printdebug("------------")
# print " "

# print vmid_status

OK_STATUS = True
UNKNOWN_STATUS = False
WARNING_STATUS = False
CRITICAL_STATUS = False

nagios_response = {'ok': '', 'nobak': '', 'nolog': '', 'running': '', 'nochk': '', '1day2old': ''}
for vmid, status in vmid_status.iteritems():
    printdebug(str(vmid) + status)
    vmid = str(vmid)
    if status == 'ok':
        nagios_response['ok'] += vmid + ','
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
    elif status == '1day2old':
        OK_STATUS = False
        WARNING_STATUS = True
        nagios_response['1day2old'] += vmid + ','
    elif status == 'nochk':
        OK_STATUS = False
        CRITICAL_STATUS = True
        nagios_response['nochk'] += vmid + ','
    else:
        OK_STATUS = False
        UNKNOWN_STATUS = True

# clean up unused key-value-pairs
new_nagios_response = {}
for key, value in nagios_response.iteritems():
    if value != '':
        new_nagios_response[key] = value

if UNKNOWN_STATUS:
    print 'UNKNOWN - Cannot read backup status - %s' % (new_nagios_response)
    raise SystemExit()
elif CRITICAL_STATUS:
    print 'CRITICAL - At least one backup did not work - %s' % (new_nagios_response)
    raise SystemExit()
elif WARNING_STATUS:
    print 'WARNING - At least one backup is not finished yet or 1 day older than expected - %s' % (new_nagios_response)
    raise SystemExit()
else:
    print 'OK - %s' % (new_nagios_response)
    raise SystemExit()
