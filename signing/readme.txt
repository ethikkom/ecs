setup signing

#patch pdf-as.war
mkdir patch_pdfas
cd patch_pdfas
unzip ../pdf-as.war.original
patch -p0 < ../pdf-as.patch
zip -r ../pdf-as.war *
cd ..
rm -r patch_pdfas

#creat tomcat instance under ~/ecs-signing
tomcat6-instance-create -p 4780 -c 4705 ~/ecs-signing
#first port , control port (first port should be tunneld via apache-ajp)
#both ports should only listen to localhost (but not important, because firewall config will snap in in case of failure)

#copy the patched wars to ~/ecs-signing/webapps
cp pdf-as.war ~/ecs-signing/webapps
cp bkuonline.war ~/ecs-signing/webapps

#copy pdf-as subdir to ~/ecs-signing/conf
cp -ar pdf-as ~/ecs-signing/conf/

#apply config.patch 
cp config.patch ~/ecs-signing
cd ~/ecs-signing/
patch -p0 < config.patch

# enable proxy_ajp
a2enmod proxy_ajp

#create /etc/apache2/conf/ecs-signing.conf
----
ProxyPass /bkuonline  ajp://localhost:4780/bkuonline
ProxyPass /pdf-as ajp://localhost:4780/pdf-as
----

#create upstart.conf
#see upstart.conf template in signing dir
