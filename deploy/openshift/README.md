# GCP Dash Deployment for OpenShift - DIY Google SA

This set of manifests deploys the GCP Dashboard application using direct Google ServiceAccount authentication.  That is, you create a secret with a typical Google SA JSON and it works as you'd expect.

There are inclusions for OpenShift such as a **Route**.

This is NOT the Zero Trust Workload Identity Management example on OpenShift - this is simply to validate the application's expected functions.  The ZTWIM example is in the `../ztwim` folder.