#!/bin/bash

CHROOT=$1

# create required directories, if neede and mount them
for dir in proc sys dev dev/pts dev/shm; do
    test -d "${CHROOT}/${dir}" || mkdir "${CHROOT}/${dir}"
done
mount -t proc proc "${CHROOT}/proc"
mount -t sysfs sysfs "${CHROOT}/sys"
mount -o bind /dev "${CHROOT}/dev"
mount -o bind /dev/pts "${CHROOT}/dev/pts"
mount -o bind /dev/shm "${CHROOT}/dev/shm"

cp "src-%(revision)s.tar.bz2" "${CHROOT}/src.tar.bz2"
cp "%(apacheconfigtarball)s" "${CHROOT}/%(apacheconfigtarball)s"
cp "%(ssleayconfig)s" "${CHROOT}/root/%(ssleayconfig)s"

cat <<'ECS_SETUP_EOF' > "${CHROOT}/ecs_setup.sh"
#!/bin/bash -x

# disable password login
sed -i -r "s/^(%(vm_user)s:)[^:]+/\\1\*/" /etc/shadow

# enable passwordless sudo
echo "%(vm_user)s ALL=NOPASSWD: ALL" >> /etc/sudoers

# quickfix: add the short hostname in /etc/hosts, elsewhise rabbitmq-server does not start
echo -e "/`hostname -s`\na\n`hostname -s`\n.\n.-1\njoin\nx\n"| ex /etc/hosts

for app in %(applications)s; do
    useradd -m ${app} -G adm -p '*' -U -s /bin/bash
    echo "${app} ALL=NOPASSWD: ALL" >> /etc/sudoers

    cat <<EOF > /home/${app}/setup.sh
#!/bin/bash -x
cd ~
mkdir src
cd src
tar xjf /src.tar.bz2 --strip=1
./bootstrap.py ../environment
. ../environment/bin/activate
fab appreq:${app},flavor=system   # install dependencies
fab appenv:${app},flavor=system   # setup environment
EOF
    su - ${app} -c '/bin/bash ~/setup.sh'
    rm "/home/${app}/setup.sh"
done
rm /src.tar.bz2

tar xjpf /%(apacheconfigtarball)s -C /etc 
rm /%(apacheconfigtarball)s

for app in %(applications)s; do
    su - ${app} -c "cd src; . ../environment/bin/activate; fab appsys:${app},hostname=%(hostname)s,ip=%(ip)s"
done

/etc/init.d/apache2 restart

cat <<'EOF' > /home/%(vm_user)s/start-working.sh
#!/bin/bash

hg clone https://ecsdev.ep3.at/hg/ecs src
cd src
./bootstrap.py ../environment
. ../environment/bin/activate
fab appenv:ecs,flavor=developer
less README
EOF
chown %(vm_user)s:%(vm_user)s /home/%(vm_user)s/start-working.sh
chmod a+x /home/%(vm_user)s/start-working.sh
ECS_SETUP_EOF
chmod a+x "${CHROOT}/ecs_setup.sh"

cat <<'RC_LOCAL_EOF' > "${CHROOT}/etc/rc.local"
#!/bin/sh -e

/ecs_setup.sh > /home/%(vm_user)s/setup.log 2>&1
chown %(vm_user)s:%(vm_user)s /home/%(vm_user)s/setup.log
rm /ecs_setup.sh

cat <<'EOF' > /etc/rc.local
#!/bin/sh -e
exit 0
EOF

exit 0
RC_LOCAL_EOF

for dir in dev/shm dev/pts dev sys proc; do
    umount "${CHROOT}/${dir}" || umount -l "${CHROOT}/${dir}"
done

