# External Setup Guide

This guide covers the one-time tooling and authentication setup required to build, run, and deploy any of the agents in this repository from **outside** of Google Cloud.

---

## Prerequisites

| Tool | Minimum Version | Install |
|------|----------------|---------|
| [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk/docs/install) | 450+ | See below |
| [Docker](https://docs.docker.com/get-docker/) | 24+ | <https://docs.docker.com/get-docker/> |
| [Python](https://www.python.org/downloads/) | 3.11+ | <https://www.python.org/downloads/> |
| [Node.js](https://nodejs.org/) | 20 LTS | <https://nodejs.org/> |
| [Terraform](https://developer.hashicorp.com/terraform/install) | 1.7+ | Optional – only for infra changes |

---

## 1. Install the Google Cloud SDK

```bash
# macOS (Homebrew)
brew install --cask google-cloud-sdk

# Debian / Ubuntu
sudo apt-get install google-cloud-cli

# Windows (PowerShell, as Administrator)
(New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")
& $env:Temp\GoogleCloudSDKInstaller.exe
```

Verify the install:

```bash
gcloud version
```

---

## 2. Authenticate

### Interactive / developer login

```bash
# Log in with your Google account
gcloud auth login

# Set up Application Default Credentials (ADC) for local SDKs
gcloud auth application-default login
```

### Service account (CI / automated pipelines)

1. Download a JSON key for the appropriate service account from the GCP Console.
2. Store the key securely (e.g. in a secrets manager – **never commit it to Git**).
3. Point the environment variable at the key file:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

---

## 3. Configure the Default Project

Switch between projects by setting the active configuration:

```bash
# Samantha
gcloud config set project samantha-493919

# Nora
gcloud config set project nora-agent

# Sloane
gcloud config set project sloane-agent
```

Or use the `GOOGLE_CLOUD_PROJECT` env var to override without changing the global config:

```bash
GOOGLE_CLOUD_PROJECT=nora-agent python main.py
```

---

## 4. Enable Required APIs

Run once per project after switching to it:

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com \
  --project="$GOOGLE_CLOUD_PROJECT"
```

---

## 5. Configure Docker for Artifact Registry

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

---

## 6. Clone Environment Variables

```bash
cp .env.example .env
# Fill in the values specific to the project you are targeting
```

See [.env.example](.env.example) for a full list of variables.

---

## Common Issues

| Error | Fix |
|-------|-----|
| `PERMISSION_DENIED` | Ensure your account/service account has the right IAM role for the project |
| `API not enabled` | Run the `gcloud services enable …` command from step 4 |
| Docker push fails | Re-run `gcloud auth configure-docker` |
| ADC errors in code | Run `gcloud auth application-default login` again |
