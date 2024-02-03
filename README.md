AFL-watchdog

a simple little script that checks for various error conditions on AFL-automation APIServers, and sends a slack alert

expects to have environment variables set:

AFL_SYSTEM_SERIAL: the serial name of the AFL platform, to include in alerts

SLACK_TOKEN: Slack API token

Slack token needs to be generated as a bot/webhook app, the app needs to be added to the channel the alerts go to, and the channel ID set in the template message.

If the bot has read permissions on channel, im, mpim, and groups, you can mute it by posting a message containing just the string "SHUT UP" to its channel.  To unmute, delete or edit your message so it no longer is exactly that string.
