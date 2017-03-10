#!//bin/bash

find /opt/kaptive/uploads/ -type d -mtime +7 -exec rm -r {} +

