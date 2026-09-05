# Security Policy

## Reporting a vulnerability

Please do not publish credentials, payment details or an exploitable vulnerability
in a public issue. Contact the repository owner privately through their GitHub
profile and include the affected component, reproduction steps and potential impact.

## Security model

- API keys and payment secrets are backend-only environment variables.
- Merchant routes require a signed session.
- Buyer requests are scoped to an HTTP-only session cookie.
- Commercial authorization is deterministic and fail-closed.
- Razorpay responses require server-side signature and captured-payment verification.
- The default checkout experience is an explicitly labelled simulation and does not
  move real money.

This buildathon prototype has not undergone an external security audit. Use test
credentials and test-mode payments during evaluation.
