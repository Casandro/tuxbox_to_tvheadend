### Purpose
This script allows you to update your tvheadend transponder lists from the tuxbox ones. As they are updated once per day, you should ideally be able to run this in a daily cron job.

*WARNING* This code still is experimental.

### Usage

Create a new admin user limited to the IP-Adress you want to update it from.

The Configuration happens via environment variables. This makes it work in Docker if you with. (Docker by no means required)

The environment variables are:
  * `TVHEADEND_IP`: The IP-Adress of tv-headend. Example: 192.168.5.5
  * `TVHEADEND_PORT`: The Port of tv-headend. Default 9981
  * `TVHEADEND_USER`: Username of an admin user, do not use your normal one
  * `TVHEADEND_PASS`: Password of that user

### `delete_double_transponders.py`
This script deletes transponders which are identical. Use this as a kind of cleanup script
