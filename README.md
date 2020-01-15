# Slack User Reconcile

Reconcile Slack user accounts with UW Groups Service group membership. Run as a periodic task, user-reconcile disables users not present in the specified group, and re-enables existing users that may come back. Actions taken are posted into the configured Slack channel.

At UW, Slack is configured with SAML auth using the UW IdP and IdP-enforced conditional access, ie allowing only members of a UW group configured in the IdP. In this configuration, new Slack users are auto-provisioned in Slack upon first SAML login. Thus the user-reconcile script does not need to do any provisioning, only disable and re-enable.

This script suitable for deployment under systemd without a container or containerized to be run under Docker or in another orchestrator.

## Configuration
Configuration is required and expected in file "/user-reconcile.cfg" or in the file specified in environment variable, CONFIG_FILE, See example user-reconcile.cfg.

## Building container
Container can be built with `docker` command and the supplied Dockerfile.

To build a container with Google Cloud Build, use a command similar to:

```gcloud --project uwit-mci-ueteam builds submit --tag gcr.io/uwit-mci-ueteam-reg/user-reconcile:$(date "+%Y%m%d%H%M") .```

Note: this obviously requires credentials in uwit-mci-ueteam, use your own project as required.
