# AWS Deployment Flow

```
S3 Bucket (uploads/)
  ↓ (Event)
Lambda (orchestrator)
  ↓
Step Functions:
  1. Audio? → Whisper Lambda
  2. PDF? → Textract Lambda
  3. Extract → Bedrock/LLM
  4. OASIS Prefill → DynamoDB
  ↓
API Gateway --> Review UI (S3/CloudFront)
```

## Services
- S3: Audio/PDF storage
- Lambda: Whisper/Textract processing
- Step Functions: Workflow orchestration
- DynamoDB: Prefills
- Cognito: Auth
```

