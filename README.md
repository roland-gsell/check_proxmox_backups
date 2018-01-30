# check_proxmox_backups
Icinga/Nagios-Check to test all Proxmox backups in one check

This check is designed to run on the proxmox server itself.
You can change the option in the config file however (e.g. host = 192.168.0.1), but in this case you need to make sure, that the machine which executes the check need to have access to the directory where the backups are. You can use a NFS share for example. At the moment the mount point must be exactly the same as on the proxmox server.

Installation
============

First you clone this repository to whereever you want it to be. I recommend choosing a different location than the place where the actual check will be performed. I'll explain why later on.
For example:

mkdir -p /opt/git && cd /opt/git
git clone ...

Next you can try the script right away, after you modified the configuration file:

vi proxmox_api.conf    # change to access your environment

I'm always using root@pam, because the normal proxmox monitoring user doesn't seem to have access to all the information I need.
If you know a solution for that, please contact me.

Then execute the script:
python check_proxmox_backup.py -f proxmox_api.conf

You will get much debug information. The last line should give you the check result - something like that:
OK - {'ok': '100,101,102,103,104,106,107,109,110,111,112,113,114,115,116,122,126,'}

Then you might want to inspect the install script for the check.
By default it will be installed in:
/usr/local/icinga/libexec

If you want to change that, edit the install script accordingly.

When you execute the install script, it will copy the python program to it's final location, setting the debug mode to False.

