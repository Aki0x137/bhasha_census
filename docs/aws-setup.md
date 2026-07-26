# AWS Console Setup Guide — Bhasaha Census MVP

This guide walks you through everything you need to do in the AWS Management Console (and CLI) before running the Bedrock-powered verdict explainer locally.

---

## Prerequisites

- An AWS account ([sign up free](https://aws.amazon.com/free/))
- AWS CLI installed: `pip install awscli` or via your package manager
- Python 3.11+ with `boto3` available (`pip install boto3`)

---

## Step 1 — Choose a Region

This project uses **Mumbai (`ap-south-1`)** for lowest latency from India.

| Priority | Region | Notes |
|----------|--------|-------|
| **1st (this project)** | `ap-south-1` (Mumbai) | Default; enable Amazon Nova / Titan here |
| 2nd | `us-east-1` (N. Virginia) | Broader catalogue if a model is missing in Mumbai |
| 3rd | `us-west-2` (Oregon) | Fallback only |

**Set this in your `.env`:**
```
AWS_REGION=ap-south-1
# or AWS_DEFAULT_REGION=ap-south-1
```

> Important: Enable model access **in the same region** you set in `.env`.

---

## Step 2 — Create an IAM User (Programmatic Access)

You need credentials for `boto3` to call Bedrock from your laptop.

1. Go to **IAM → Users → Create user**
2. Name it something like `bhasaha-census-dev`
3. Select **"Programmatic access"** (generate access key)
4. On the **Permissions** step, choose **"Attach policies directly"** and add:

   | Policy | Why |
   |--------|-----|
   | `AmazonBedrockFullAccess` | Invoke Bedrock models |

   > For production you'd use a tighter custom policy — for the hackathon MVP `AmazonBedrockFullAccess` is fine.

5. Complete creation. On the last screen, **download the CSV** or copy:
   - **Access key ID** → `AWS_ACCESS_KEY_ID` in `.env`
   - **Secret access key** → `AWS_SECRET_ACCESS_KEY` in `.env`

   > You can only view the secret key once. Save it now.

---

## Step 3 — Enable Bedrock Model Access (skip Claude)

Claude models require Anthropic’s use-case form (often needs a company). **Skip Claude.** Use Amazon-owned models instead — they do **not** need that form.

1. Open the [Amazon Bedrock console](https://console.aws.amazon.com/bedrock) in region **Asia Pacific (Mumbai) `ap-south-1`**
2. Open **Model access** / **Model catalog**
3. Enable one of these (pick the first that shows as available):

   | Priority | Model | Model ID | Notes |
   |----------|-------|----------|-------|
   | **Recommended** | Amazon Nova Micro | `amazon.nova-micro-v1:0` | Cheapest Amazon text model; no company form |
   | Good | Amazon Nova Lite | `amazon.nova-lite-v1:0` | Better quality; still Amazon-owned |
   | Fallback | Amazon Titan Text Express | `amazon.titan-text-express-v1` | Older but widely available |
   | Optional | Meta Llama 3.1 8B Instruct | `meta.llama3-1-8b-instruct-v1:0` | Usually no Anthropic-style company form; check console |

   > Avoid Anthropic Claude unless you can submit the company use-case form.

4. Once the model is usable in Playground (or shows **"Access granted"**), copy the **exact** model ID into `.env`:
   ```
   BEDROCK_MODEL_ID=amazon.nova-micro-v1:0
   ```

---

## Step 4 — Verify Access from CLI

```bash
# Configure the AWS CLI with your credentials
aws configure
# Enter: Access Key ID, Secret Access Key, Region (ap-south-1), output format (json)

# List Amazon Nova / Titan text models in Mumbai
aws bedrock list-foundation-models --region ap-south-1 \
  --query 'modelSummaries[?contains(modelId, `nova`) || contains(modelId, `titan-text`)].modelId'
```

Example output:
```json
[
  "amazon.nova-micro-v1:0",
  "amazon.nova-lite-v1:0",
  "amazon.titan-text-express-v1"
]
```

If this returns an empty list or an error, check:
- You are in `ap-south-1` in the console and CLI
- Your IAM user has `AmazonBedrockFullAccess`
- The model is enabled / available in Model access

---

## Step 5 — Quick Python Smoke Test (Nova Micro)

```python
import boto3, json

client = boto3.client("bedrock-runtime", region_name="ap-south-1")

body = {
    "messages": [
        {"role": "user", "content": [{"text": "Say hello in one sentence."}]}
    ],
    "inferenceConfig": {"maxTokens": 64},
}

resp = client.invoke_model(
    modelId="amazon.nova-micro-v1:0",
    body=json.dumps(body),
    contentType="application/json",
    accept="application/json",
)
result = json.loads(resp["body"].read())
print(result["output"]["message"]["content"][0]["text"])
```

If this prints a greeting, **Bedrock is working**.

Titan Text Express smoke test (if Nova is unavailable):

```python
body = {
    "inputText": "Say hello in one sentence.",
    "textGenerationConfig": {"maxTokenCount": 64},
}
resp = client.invoke_model(
    modelId="amazon.titan-text-express-v1",
    body=json.dumps(body),
    contentType="application/json",
    accept="application/json",
)
result = json.loads(resp["body"].read())
print(result["results"][0]["outputText"])
```

---

## Step 6 — Set `.env` Values

```ini
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=AKIA...your key...
AWS_SECRET_ACCESS_KEY=...your secret...
BEDROCK_MODEL_ID=amazon.nova-micro-v1:0
BEDROCK_MAX_TOKENS=512
```

---

## Step 7 — Kognition API Key

Kognition is a separate, non-AWS service.

1. Sign up at **[https://www.kognition.ai](https://www.kognition.ai)**
2. Navigate to your dashboard → **API Keys** → **Create key**
3. Copy the key and put it in `.env`:
   ```
   KOGNITION_API_KEY=kognition_live_XXXXXXXXXXXX
   KOGNITION_BASE_URL=https://api.kognition.ai/v1
   ```
4. If you don't have a Kognition key yet, the plugin **runs in offline stub mode** automatically — set:
   ```
   KOGNITION_OFFLINE=true
   ```
   This is the default when `KOGNITION_API_KEY` is empty.

---

## Step 8 — Other Credentials (Optional for MVP)

| Service | Variable | Where to get it |
|---------|----------|----------------|
| Telegram bot | `TELEGRAM_BOT_TOKEN` | Chat [@BotFather](https://t.me/BotFather) on Telegram, `/newbot` |
| Sarvam STT/OCR | `SARVAM_API_KEY` | [https://dashboard.sarvam.ai](https://dashboard.sarvam.ai) |

Both services have offline stub modes (`SARVAM_OFFLINE=true`) so you can run the video pipeline without them.

---

## Cost Estimates (Hackathon/Demo Scale)

| Service | Usage | Estimated cost |
|---------|-------|----------------|
| Bedrock Nova Micro | 1,000 short explanations | typically a few cents |
| Kognition | Check their pricing page | Varies |
| AWS data transfer | <1 GB demo traffic | < $0.01 |

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `AccessDeniedException: You don't have access to the model` | Enable **Nova Micro** (or Titan) in Bedrock console for `ap-south-1` — do not use Claude if you can't complete Anthropic's company form |
| `NoCredentialsError` | Run `aws configure` or check `.env` is loaded (`python-dotenv`) |
| `EndpointResolutionError` | Wrong region — check `AWS_REGION` / `AWS_DEFAULT_REGION` matches where you enabled model access |
| `ValidationException: The provided model identifier is invalid` | Double-check `BEDROCK_MODEL_ID` — copy exact string from Bedrock console |
| Kognition `401 Unauthorized` | Check `KOGNITION_API_KEY` is correct; set `KOGNITION_OFFLINE=true` for local dev |

---

## Security Reminders

- **Never commit `.env`** — the repo's `.gitignore` already excludes it.
- For the hackathon, IAM user credentials are fine. In production, use **IAM roles** (EC2 instance profile or ECS task role) — no long-lived keys.
- Rotate your access key after the hackathon if you've shared your machine.
