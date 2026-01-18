# OrderOctopus 🐙

Chat-based restaurant ordering system for F&B SMEs in Singapore, Vietnam, and Philippines.

## Overview

OrderOctopus enables restaurants to accept orders via familiar messaging platforms (Facebook Messenger initially) using natural language conversations. Customers scan a QR code, chat with the bot, and place orders that flow through staff approval to the kitchen.

**Key Features:**
- Natural language + structured menu ordering
- PDF menu import with LLM-powered parsing
- Staff approval workflow with kitchen routing
- Credit-based pricing (1 credit per order)
- Multilingual support (EN, TL, VI, ZH, MS)
- Platform adapter architecture for multi-channel expansion

## Project Structure

```
OrderOctopus/
├── backend/
│   ├── adapters/       # Platform adapters (Messenger, WhatsApp, Telegram)
│   ├── core/           # Business logic (order processing, menu management)
│   ├── models/         # Database models and schemas
│   ├── services/       # External services (LLM, Stripe, PDF processing)
│   ├── utils/          # Utilities and helpers
│   ├── config.py       # Application configuration
│   └── main.py         # FastAPI application entry point
├── tests/
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
├── docs/
│   └── plans/          # Design documents and plans
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment variables
└── README.md
```

## Prerequisites

- Python 3.11+
- PostgreSQL (via Supabase)
- Meta Business Account (for Facebook Messenger)
- Stripe Account
- Anthropic or OpenAI API key

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/martijnmoret-ds/OrderOctopus.git
cd OrderOctopus
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

**Database (Supabase):**
- Create account at [supabase.com](https://supabase.com)
- Create new project
- Copy URL and anon key to `.env`

**Facebook Messenger:**
- Create Meta Business Account
- Create Facebook App, add Messenger product
- Generate Page Access Token
- Set webhook verify token (custom string)

**LLM Provider:**
- Get API key from [Anthropic](https://console.anthropic.com) or [OpenAI](https://platform.openai.com)

**Stripe:**
- Create account at [stripe.com](https://stripe.com)
- Get API keys from dashboard
- Configure webhook endpoint

### 5. Set Up Database

Run database migrations (once implemented):

```bash
# Coming soon: alembic upgrade head
```

For now, create tables manually in Supabase following schema in `docs/plans/2026-01-18-orderoctopus-mvp-design.md`.

### 6. Run the Application

```bash
python backend/main.py
```

Or with uvicorn:

```bash
uvicorn backend.main:app --reload
```

The API will be available at `http://localhost:8000`.

### 7. Test the Setup

```bash
curl http://localhost:8000/health
```

Should return: `{"status": "healthy"}`

## Development

### Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=backend --cov-report=html
```

### Code Formatting

```bash
black backend/ tests/
```

### Type Checking

```bash
mypy backend/
```

### Linting

```bash
flake8 backend/
```

## Deployment

### Railway

1. Create account at [railway.app](https://railway.app)
2. Connect GitHub repository
3. Add environment variables from `.env`
4. Deploy

### Render

1. Create account at [render.com](https://render.com)
2. Create new Web Service
3. Connect GitHub repository
4. Add environment variables
5. Deploy

## Meta Business Setup

Before going live, complete Meta verification:

1. **Create Meta Business Account**
   - Visit [business.facebook.com](https://business.facebook.com)
   - Complete business verification (requires documents)

2. **Create Facebook App**
   - Visit [developers.facebook.com](https://developers.facebook.com)
   - Create new app → Business type
   - Add Messenger product

3. **Configure Webhooks**
   - Set webhook URL: `https://yourdomain.com/webhook`
   - Set verify token (matches `.env`)
   - Subscribe to: `messages`, `messaging_postbacks`

4. **Submit for Review**
   - Request `pages_messaging` permission
   - Provide testing instructions
   - Wait for approval (1-2 weeks)

## Stripe Setup

1. Create Stripe account
2. Configure products for credit packages:
   - 100 credits - $20
   - 500 credits - $85
   - 1000 credits - $150
3. Set webhook endpoint: `https://yourdomain.com/stripe-webhook`
4. Subscribe to: `payment_intent.succeeded`

## Documentation

- [MVP Design Document](docs/plans/2026-01-18-orderoctopus-mvp-design.md)

## Tech Stack

- **Backend:** Python 3.11, FastAPI
- **Database:** PostgreSQL (Supabase)
- **Messaging:** Facebook Messenger Platform API
- **LLM:** Anthropic Claude / OpenAI GPT
- **PDF Processing:** pdfplumber + LLM Vision
- **Payments:** Stripe
- **Hosting:** Railway / Render

## Contributing

This is currently a private project. Contact the maintainer for collaboration opportunities.

## License

Proprietary - All rights reserved

## Support

For issues or questions, contact: [Your contact information]

---

Built with ❤️ for F&B SMEs
