# GCP Dash Deployment - For GKE with Workload Identity Federation

This set of manifests deploys the application on a GKE cluster with WIF enabled.

Before doing so, a few steps must be taken:

## Prerequisites

```bash
# Set the region of your GKE cluster
REGION="us-central1"
# Set the name for your GKE cluster
GKE_NAME="autopilot-cluster-1"

# Set the Kubernetes Namespace we'll deploy the app to
K8S_NS="gcp-dash"
# Set the Kubernetes ServiceAccount Name
K8S_SA="gcp-dash"

# Google Service Account Name - This must match general prereq setup steps
GOOGLE_SA_NAME="gcp-dash"

PROJECT=$(gcloud config get-value project)
PROJECT_ID=$(gcloud config get-value project) # This is the same in some envs
# Or if it's the Project Number
# PROJECT_ID=$(gcloud projects describe $PROJECT --format="value(projectNumber)")

# Easy Var
GOOGLE_SA_ID="${GOOGLE_SA_NAME}@${PROJECT}.iam.gserviceaccount.com"

# Authenticate to your GKE cluster
gcloud container clusters get-credentials ${GKE_NAME} --region ${REGION} --project ${PROJECT} --dns-endpoint

# Get Workload Identity Discovery Endpoint from GKE cluster
WID_ENDPOINT=$(gcloud container clusters describe ${GKE_NAME} --region=${REGION} --format="value(workloadIdentityConfig.workloadPool)")

# Add Impersonation ability IAM Binding to the workload we'll deploy
gcloud iam service-accounts add-iam-policy-binding ${GOOGLE_SA_ID} \
  --role=roles/iam.workloadIdentityUser \
  --member="serviceAccount:${WID_ENDPOINT}[${K8S_NS}/${K8S_SA}]"
```

## Deploy

Now that the GKE Namespace and ServiceAccount have been given permission to impersonate the Google Service Account, we can deploy the application with a little

```bash
# Deploy the GKE workload
kubectl apply -k deploy/gke

# Annotate the ServiceAccount
# There is a default placeholder, overwrite
kubectl annotate serviceaccount ${K8S_SA} -n ${K8S_NS} iam.gke.io/gcp-service-account=${GOOGLE_SA_ID} --overwrite

# Bounce the Pods
kubectl rollout restart -n ${K8S_NS} deployment/gcp-dash
```

The default GKE deployment creates an Ingress as well as a Gateway and HTTPRoute.  It takes a while for them to spin up so whichever gets there first really I guess...

## Extras

In the `deploy/gke` folder there is a `deny-netpol.yaml` file - this denies all traffic to the workload pods, in case you want to keep the application scaled up but not accessible from the public Internet for a while.  It's wild out there and the container can burn CPU, so useful when testing and importantly when not actively testing.
