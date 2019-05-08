# user-reconcile

Reconcile Slack user accounts with GWS group membership. Disables users not present in the group, reenables existing users that may come back. (Slack with SAML auto-provisions new users based on GWS group specified in IDP so there is no need for this script to do any provisioning.)

This script suitable for systemd deployment or Container

Configuration is required and expected in file "/user-reconcile.cfg" or in the file specified in environment variable, CONFIG_FILE, See example user-reconcile.cfg.

## Building container
Google Cloud Build build this directory for use in Managed Container Infrastructure

This Requires credentials in uwit-mci-svcs or service account

```gcloud --project uwit-mci-svcs builds submit --tag gcr.io/uwit-mci-svcs/user-reconcile:$(date "+%Y%m%d%H%M") .```
