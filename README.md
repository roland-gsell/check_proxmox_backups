# check_proxmox_backups
Icinga/Nagios-Check to test all Proxmox backups in one check

There were already bash scripts available, which can do the same thing for a single backup. However, if you add a new VM and forget to add another check in your monitoring environment, this new backup won't be checked.  
Also changes in the backup schedule will not be taken into account with an ordinary bash script solution.

So, basically this check will test all log file of all VMs, which are listed in the backup schedule of Proxmox.  
You need to setup this schedule still by yourself, though. ;-)  
If any changes are done inside of Proxmox (new VMs, removal of old VMs, backup schedule update, ..) the check doesn't need to be updated. It will automatically do the right thing the next time it runs.

This check is designed to run on the proxmox server itself.

You can change the option in the config file however (e.g. host = 192.168.0.1), but in this case you need to make sure that the machine which executes the check need to have access to the directory where the backups are. You can use a NFS share for example. At the moment the mount point must be exactly the same as on the proxmox server.

THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY APPLICABLE LAW. EXCEPT WHEN OTHERWISE STATED IN WRITING THE COPYRIGHT HOLDERS AND/OR OTHER PARTIES PROVIDE THE PROGRAM “AS IS” WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM IS WITH YOU. SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY SERVICING, REPAIR OR CORRECTION.

IN NO EVENT UNLESS REQUIRED BY APPLICABLE LAW OR AGREED TO IN WRITING WILL ANY COPYRIGHT HOLDER, OR ANY OTHER PARTY WHO MODIFIES AND/OR CONVEYS THE PROGRAM AS PERMITTED ABOVE, BE LIABLE TO YOU FOR DAMAGES, INCLUDING ANY GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OR INABILITY TO USE THE PROGRAM (INCLUDING BUT NOT LIMITED TO LOSS OF DATA OR DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD PARTIES OR A FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER PROGRAMS), EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.

Installation
============

First you clone this repository to whereever you want it to be. I recommend choosing a different location than the place where the actual check will be performed. I'll explain why later on.  
For example:

mkdir -p /opt/git && cd /opt/git  
git clone https://github.com/roland-gsell/check_proxmox_backups.git

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

When you execute the install script, it will copy the python program to its final location, setting the debug mode to False.

The next thing you need to do in Icinga or Nagios is set up the check in your monitoring environment.  
Here are some examples of the command and the check definition:


define command{  
        command_name    check_ssh_pvebackups  
        command_line    $USER1$/check_by_ssh -H $HOSTADDRESS$ -t 60 -C "/usr/bin/python /usr/local/icinga/libexec/check_proxmox_backup.py -f /usr/local/icinga/libexec/proxmox_api.conf"  
}  

define service{  
        use                             generic-service  
        host_name                       pve01  
        service_description             All defined VM backups  
        check_command                   check_ssh_pvebackups  
        }
