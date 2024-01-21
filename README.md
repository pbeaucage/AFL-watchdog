AFL-watchdog

a simple little script that checks for various error conditions on AFL-automation APIServers, and sends a slack alert

expects to have environment variables set:
AFL_SYSTEM_SERIAL: the serial name of the AFL platform, to include in alerts
SLACK_TOKEN: Slack API token
