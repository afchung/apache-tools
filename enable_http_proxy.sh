#!/bin/sh
sudo a2enmod proxy
sudo a2enmod proxy_balancer
sudo a2enmod proxy_http
sudo a2enmod lbmethod_*
sudo service apache2 restart