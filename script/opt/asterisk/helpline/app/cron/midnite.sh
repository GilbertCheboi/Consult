#!/bin/sh
# Get a random sequence for this cron run

EXTENID=`curl http://localhost/random.php`

# Create call file
cat <<EOF> /opt/asterisk/CHLCore/callFiles/$EXTENID.call
Channel: LOCAL/$EXTENID@CHLBridge
Context: MidniteClock
Extension: $EXTENID
Priority: 1
EOF

#change file ownership to asterisk
mv /opt/asterisk/CHLCore/callFiles/$EXTENID.call /opt/asterisk/CHLCore/callFiles/cron
