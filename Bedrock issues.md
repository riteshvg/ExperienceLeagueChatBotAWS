Amazon Bedrock now supports Anthropic Claude models in India through Global cross-Region inference (CRIS). This feature allows customers operating in ap-south-1 (Mumbai) and ap-south-2 (Hyderabad) regions to access Claude models by routing requests to commercial AWS regions globally.

ROOT CAUSE
The error occurs because Anthropic Claude models were not directly available in India regions. However, this has been resolved with the introduction of Global cross-Region inference profiles.

RESOLUTION STEPS

1.  USE GLOBAL INFERENCE PROFILES
    Instead of using region-specific model IDs, use the global inference profile IDs for Claude models:

- Claude Opus 4.6: global.anthropic.claude-opus-4-6-v1
- Claude Sonnet 4.6: global.anthropic.claude-sonnet-4-6
- Claude Haiku 4.5: global.anthropic.claude-haiku-4-[contact information removed]-v1:0
- Claude Sonnet 4.5: global.anthropic.claude-sonnet-4-[contact information removed]-v1:0
- Claude Opus 4.5: global.anthropic.claude-opus-4-[contact information removed]-v1:0

2.  CONFIGURE IAM PERMISSIONS
    Apply the required three-part AWS Identity and Access Management policy to enable Global cross-Region inference for your users. [1]

3.  ACCESS THROUGH BEDROCK CONSOLE

- Log in to AWS Console and select Asia Pacific (Mumbai) Region
- Navigate to Amazon Bedrock console
- Go to Inference profiles under the Infer section
- Look for global inference profiles (they start with "global")
- Select the desired Claude model and use "Open In Playground" to test

4.  PROGRAMMATIC ACCESS
    Use the global model IDs with standard Bedrock APIs:

- InvokeModel API
- InvokeModelWithResponseStream API
- Converse API
- ConverseStream API

The Global cross-Region inference automatically routes your requests from India regions (ap-south-1 and ap-south-2) to commercial AWS regions where Claude models are available, providing seamless access without requiring you to change regions or accounts.

This solution specifically addresses the India address account limitation by leveraging AWS global infrastructure to provide access to Claude models while maintaining your India-based account setup. [1]
