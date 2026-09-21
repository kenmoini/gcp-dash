# GCP Dash Deployment for OpenShift - DIY Google SA

This set of manifests deploys the GCP Dashboard application using direct Google ServiceAccount authentication.  That is, you create a secret with a typical Google SA JSON and it works as you'd expect.

There are inclusions for OpenShift such as a **Route**.

This is NOT the Zero Trust Workload Identity Management example on OpenShift - this is simply to validate the application's expected functions.  The ZTWIM example is in the `../ztwim` folder.

## Prerequisites

In this folder is a [secret.example.yaml](./secret.example.yaml) file that needs to be created with the contents of a Google Service Account JSON authentication key.

```bash
# Create a namespace
oc create namespace gcp-dash

# Create a Secret
oc apply -n gcp-dash -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: gcp-dash-sa-key
type: Opaque
stringData:
  key.json: |
    { "type": "service_account", "...": "paste the service-account key here" }
EOF
```

## Deploy

With the Secret created you can easily deploy the Kustomization base folder:

```bash
# Deploy the Kustomize patch
oc apply -n gcp-dash -k deploy/openshift/

# Get the Route
echo "https://$(oc get route gcp-dash -n gcp-dash -o jsonpath='{.spec.host}')"
```