# GCP Dash Deployment - For Kubernetes

This is the basic set of manifests needed to deploy this application in a generic Kubernetes cluster using direct Google ServiceAccount authentication.  That is, you create a secret with a typical Google SA JSON and it works as you'd expect.

For the OpenShift version of this pattern, see the `../openshift` folder.

For GKE-based deployments where Workload Identity is enabled, see the `../gke` folder.

For the Zero Trust Workload Identity Management example, see the `../ztwim` folder.

## Prerequisites

In this folder is a [secret.example.yaml](./secret.example.yaml) file that needs to be created with the contents of a Google Service Account JSON authentication key.

```bash
# Create a namespace
kubectl create namespace gcp-dash

# Create a Secret
kubectl apply -n gcp-dash -f - <<EOF
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
kubectl apply -n gcp-dash -k deploy/kubernetes/
```

> Note: An Ingress is not created - this depends on the Ingress Controller implementation often, but here's an example that targets the Service on port 8080:

```bash
kubectl apply -n gcp-dash -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: gcp-dash
spec:
  rules:
  - http:
      paths:
      - path: /*
        backend:
          service:
            name: gcp-dash
            port:
              number: 8080
EOF
```