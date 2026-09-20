# GCP Dash Deployment - For Kubernetes

This is the basic set of manifests needed to deploy this application in a generic Kubernetes cluster using direct Google ServiceAccount authentication.  That is, you create a secret with a typical Google SA JSON and it works as you'd expect.

For the OpenShift version of this pattern, see the `../openshift` folder.

For GKE-based deployments where Workload Identity is enabled, see the `../gke` folder.

For the Zero Trust Workload Identity Management example, see the `../ztwim` folder.