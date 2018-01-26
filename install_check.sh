#!/bin/bash

cp check_proxmox_backup.py check_proxmox_backup.py.bak
sed -i 's/debug = True/debug = False/g' check_proxmox_backup.py.bak
mkdir -p /usr/local/icinga/libexec/
mv check_proxmox_backup.py.bak /usr/local/icinga/libexec/check_proxmox_backup.py
cp pyproxmox.py /usr/local/icinga/libexec/

echo "Check installed"
echo " "
echo "If this is the first time you install the script and you are using a config file, execute now:"
echo "cp proxmox_api.conf /usr/local/icinga/libexec/"
echo " "
echo "and modify it accordingly:"
echo "vim /usr/local/icinga/libexec/proxmox_api.conf"
echo " "
echo "The define command on the watchbox should look like this:"
echo "/usr/local/icinga/etc/objects/general/commands_pve.cfg"
echo " "
echo " [...]"
echo "define command{"
echo "    command_name    check_ssh_pvebackups"
echo '    command_line    $USER1$/check_by_ssh -H $HOSTADDRESS$ -t 60 -C "sudo /usr/bin/python /usr/local/icinga/libexec/check_proxmox_backup.py -f /usr/local/icinga/libexec/proxmox_api.conf"'
echo "}"
echo " "
echo " "
echo " "
