# OrderOctopus MVP Design

**Date:** 2026-01-18
**Version:** 1.0
**Target Markets:** Singapore, Vietnam, Philippines

## Executive Summary

OrderOctopus is a chat-based restaurant ordering system that solves the "app ordering takes 8 minutes vs 2 minutes IRL" problem. Customers scan a QR code to order via familiar messaging apps, using natural conversation instead of clunky app interfaces. Orders flow through staff approval before reaching the kitchen.

**MVP Scope:**
- Facebook Messenger as primary platform (best market fit for target regions)
- Platform adapter architecture for future multi-channel expansion
- PDF menu import with LLM-powered parsing
- Hybrid ordering (natural language + structured menus)
- Credit-based pricing model (1 credit per order)
- Multilingual support (EN, TL, VI, ZH, MS)

---

## Business Model

**Target Audience:** F&B SME owners in Singapore, Vietnam, Philippines

**Pricing:**
- 25 free order credits on signup
- 1 credit per approved order (~$0.15-0.20 per order)
- 0.5 credits for rejected orders (covers LLM conversation costs)
- 15 credits per additional menu import (after first 3 free)
- Credit packages via Stripe:
  - 100 credits - $20 ($0.20/order)
  - 500 credits - $85 ($0.17/order)
  - 1000 credits - $150 ($0.15/order)

**Free Features:**
- 3 menu imports (PDF parsing)
- Unlimited menu updates (sold-out items, availability)
- 20 price changes per month

---

## System Architecture

### Core Components

**Backend Stack:**
- **Language:** Python 3.11+
- **Framework:** FastAPI (async webhook handling)
- **Messaging:** Facebook Messenger Platform API
- **Database:** Supabase (PostgreSQL)
- **LLM:** Anthropic Claude or OpenAI GPT (for natural language understanding)
- **PDF Processing:** pdfplumber + LLM vision model (Claude Vision)
- **Payments:** Stripe (credit purchases)
- **Hosting:** Railway or Render

### Platform Adapter Architecture

Multi-channel support via abstraction layer:

```
Customer → Platform Adapter (Messenger/Telegram/WhatsApp/etc.)
         → Message Router
         → Business Logic (Order Processing, Menu, LLM)
         → Response Builder
         → Platform Adapter → Customer
```

**Key Abstractions:**
- `Message`: Normalized message object (text, user_id, venue_context, attachments)
- `Response`: Platform-agnostic response (text, buttons, images) that adapter converts to platform format
- `UserSession`: Tracks conversation state independent of platform

**Benefits:**
- Business logic stays platform-independent
- Adding WhatsApp/Telegram requires only new adapter implementation
- Testing simplified (mock platform adapters)

### Multi-Tenancy

- Single bot serves all restaurants
- QR codes contain venue context: `m.me/orderoctopus?ref=venue_abc_table5`
- Bot extracts `venue_id` and `table_number`, loads correct menu
- Data isolation via venue_id filtering in all queries

---

## Data Model

### Database Schema (Supabase/PostgreSQL)

**venues**
```sql
id                          uuid PRIMARY KEY
name                        text NOT NULL
location                    text
language                    text NOT NULL -- Owner's preferred language
business_hours              jsonb -- {"monday": {"open": "11:00", "close": "22:00"}, ...}
status                      enum(active, paused, suspended) DEFAULT 'active'
credits_remaining           integer DEFAULT 25
max_menu_parses_remaining   integer DEFAULT 3
approval_group_id           text NOT NULL -- Messenger group/thread ID
kitchen_group_id            text -- Separate kitchen destination if configured
created_at                  timestamp
updated_at                  timestamp
```

**menu_items**
```sql
id                      uuid PRIMARY KEY
venue_id                uuid REFERENCES venues(id)
category                text NOT NULL -- Appetizers, Mains, Drinks, etc.
name                    text NOT NULL
description             text
base_price              decimal(10,2) NOT NULL
options                 jsonb -- [{"name": "Protein", "choices": [{"value": "beef", "price": 0}]}]
modifications_allowed   text[] -- ["spice level", "no onions", "extra cheese"]
dietary_tags            text[] -- ["vegetarian", "gluten-free", "spicy"]
available               boolean DEFAULT true
created_at              timestamp
updated_at              timestamp
```

**orders**
```sql
id                      uuid PRIMARY KEY
venue_id                uuid REFERENCES venues(id)
order_number            integer NOT NULL -- Daily counter per venue
table_number            text
customer_messenger_id   text NOT NULL
customer_name           text
items                   jsonb NOT NULL -- Full order details with modifications
total_amount            decimal(10,2) NOT NULL
status                  enum(pending, approved, rejected) DEFAULT 'pending'
approved_by             text -- Staff username
rejected_reason         text
created_at              timestamp
approved_at             timestamp
updated_at              timestamp
```

**customer_profiles** (for future marketing)
```sql
messenger_id        text PRIMARY KEY
first_name          text
last_name           text
order_count         integer DEFAULT 0
last_order_at       timestamp
created_at          timestamp
```

**credit_transactions**
```sql
id                  uuid PRIMARY KEY
venue_id            uuid REFERENCES venues(id)
amount              integer NOT NULL -- Credits +/-
type                enum(purchase, order_charge, menu_import, bonus, refund)
stripe_payment_id   text -- For purchases
order_id            uuid REFERENCES orders(id) -- For order charges
created_at          timestamp
```

---

## User Flows

### 1. Owner Onboarding Flow

**Goal:** Restaurant owner goes from signup to live menu in under 15 minutes.

**Steps:**

1. **Registration**
   - Owner starts conversation with OrderOctopus bot on Messenger
   - Bot asks: Restaurant name, location, business hours
   - Owner selects venue language: [English] [Tagalog] [Vietnamese] [中文] [Bahasa Melayu]
   - Bot creates venue record, generates 25 free credits
   - Bot asks: "How many tables do you have?"
   - Generates unique QR codes for each table

2. **Setup Approval & Kitchen Groups**
   - Bot: "Add me to your staff approval group (the group where orders should be reviewed)"
   - Owner creates Messenger group, adds bot + staff members
   - Bot receives group ID, stores as `approval_group_id`
   - Bot asks: "Should approved orders go to this same group, or a different kitchen group?"
   - If different, owner adds bot to kitchen group → stores `kitchen_group_id`

3. **Menu Import**
   - Bot offers: "Upload menu PDF" or "Enter items manually"
   - **PDF Path:**
     - Owner uploads PDF
     - Bot processes with pdfplumber + Claude Vision API
     - Extracts sections, items, prices, options, descriptions
     - Generates structured menu JSON
   - **Manual Path:**
     - Bot guides through adding categories and items
     - Asks for: name, price, options, dietary tags

4. **Menu Verification**
   - Bot presents parsed menu section by section
   - Asks targeted questions: "I found 'Burger - $12 (beef/chicken)' - are beef and chicken the same price?"
   - Owner confirms, corrects, adds missing details
   - Bot persists verified menu to database

5. **Go Live**
   - Bot: "Your menu is ready! Here are your table QR codes."
   - Provides downloadable QR code images (PNG with table numbers)
   - Venue status set to "active"
   - Owner can now receive orders

---

### 2. Customer Ordering Flow

**Goal:** Customer goes from scanning QR code to confirmed order in under 2 minutes.

**Entry:**
- Customer scans QR code at table
- Opens Messenger with deep link: `m.me/orderoctopus?ref=venue_abc_table5`
- Bot extracts `venue_id` and `table_number`
- Loads venue menu, creates session

**Conversation:**

1. **Greeting & Language Detection**
   - Bot detects customer language from first message
   - Greets in customer language: "Welcome to Cafe Latte! 🐙"
   - Asks: "What are you craving today?"
   - Buttons: ["Show me the menu", "I know what I want"]

2. **Hybrid Ordering**
   - **Structured Path:**
     - Bot shows category buttons: [Appetizers] [Mains] [Drinks]
     - Customer taps category → sees items with prices
     - Taps item → bot asks clarifying questions
   - **Natural Language Path:**
     - Customer types: "I want a burger with no onions"
     - LLM identifies item, extracts modifications
     - Bot confirms: "Got it! One Burger (no onions). Beef or chicken patty?"
   - Customer can switch modes: "Actually show me desserts"

3. **Order Building**
   - Bot asks clarifying questions based on menu options:
     - "Beef or chicken patty?"
     - "Would you like to make it a combo? +$3 for fries and drink"
   - Handles modifications naturally: "make it spicy", "extra cheese"
   - LLM extracts and structures modifications

4. **Order Summary**
   - Bot shows complete order:
     ```
     Your order:
     1x Burger (beef, no onions, extra cheese) - $12
     1x Coke - $3
     Total: $15

     This is order #47 for today
     ```
   - Buttons: [Confirm Order] [Modify] [Cancel]

5. **Confirmation**
   - Customer taps "Confirm Order"
   - Bot: "Order confirmed! Your order is being reviewed by the kitchen. You're order #47 today."
   - Order sent to approval group
   - If customer tries to modify: "Your order is with the kitchen! Please speak to staff for changes."

---

### 3. Approval & Kitchen Flow

**Order Submission:**

When customer confirms, bot sends to approval group:

```
🆕 ORDER #47 | Table 5 | 2:35 PM

1x Burger (beef, no onions, extra cheese) - $12
1x Coke - $3
Total: $15 | Pay at counter

[✅ Approve] [❌ Reject]
```

**Approval:**
- Any group member taps "Approve"
- Message edited to:
  ```
  ✅ ORDER #47 | Table 5 | 2:35 PM
  Approved by @staffname at 2:36 PM

  1x Burger (beef, no onions, extra cheese) - $12
  1x Coke - $3
  Total: $15
  ```
- **Credit deduction:** 1.0 credit charged
- Customer notified: "Your order has been approved! Food will be ready soon."
- If separate kitchen group configured, order forwarded:
  ```
  🍳 #47 | Table 5 | 2:36 PM

  1x Burger (beef, no onions, extra cheese)
  1x Coke
  ```

**Rejection:**
- Staff member taps "Reject"
- Bot asks: "Why are you rejecting?" (out of stock, customer issue, etc.)
- **Credit deduction:** 0.5 credits charged
- Customer notified: "Sorry, we can't fulfill your order right now. [Reason]. Please speak to staff."

**Credit Management:**
- If credits hit 0: Bot pauses new orders, messages owner: "You're out of credits. Orders are paused. [Buy Credits]"
- Credits ≤5: Warning message to owner

---

## Feature Details

### Multilingual Support

**Venue Language (Owner-Controlled):**
- Owner sets during onboarding: "What language should I use for your team?"
- Options: English, Tagalog, Vietnamese, 中文, Bahasa Melayu
- Stored in `venues.language`
- All staff-facing content uses this language:
  - Approval group messages
  - Kitchen notifications
  - Bot responses to owner
- Can be changed: `/language Vietnamese`

**Customer Language (Auto-Detected):**
- Bot detects from customer's first message via LLM
- All customer responses in detected language
- Customer can switch: "English please" → LLM detects and updates session

**Menu Items:**
- Stored in venue's language (no translation)
- Dish names shown in original language to avoid food accuracy issues
- Surrounding bot text translated to customer language

**Order Processing:**
- Customer modifications translated to venue language for approval group
- Example: Customer says "không xương" (no bones in Vietnamese) → order to English venue shows "no bones"

**Supported Languages:**
- English (default)
- Tagalog/Filipino
- Vietnamese
- Mandarin/Simplified Chinese
- Bahasa Melayu

---

### Menu Management

**Owner Commands:**

**Sold-out Management (Free):**
- `/soldout Burger` - Mark single item unavailable
- `/soldout Burger, Fries, Coke` - Bulk update
- `/available Burger` - Restore availability
- Natural language: "We're out of burgers" → bot understands
- `/soldout list` - Show currently unavailable items
- Items immediately hidden from customer menu

**Price Updates (20 free/month):**
- Owner: "Change Burger price to $15"
- Bot confirms and updates
- Beyond 20 changes/month: 0.5 credits per change

**Menu Re-import:**
- `/import menu` - Trigger new PDF upload
- First 3 imports: Free
- Additional imports: 15 credits each
- If credits < 15: "Not enough credits. [Buy Credits]"

**Business Hours (Free):**
- `/hours` - View current hours
- Owner: "Change hours to 10am-11pm daily"
- Bot updates, orders blocked outside hours

**Credit Management:**
- `/credits` - Show remaining credits
- `/buy credits` - Stripe checkout link

**Order History:**
- `/orders today` - All orders with status
- `/orders 47` - Specific order details

---

### Credit System

**Credit Economy:**
- 25 free credits on signup
- 1 credit per approved order
- 0.5 credits per rejected order (covers LLM costs)
- 15 credits per menu import (after first 3 free)
- Free: menu updates, business hours, 20 price changes/month

**Purchase Flow:**
- Credits ≤5: Bot warns owner
- Credits = 0: New orders paused
- Owner: `/buy credits` → Stripe Checkout link
- After payment: Credits added, bot confirms

**Stripe Integration:**
- Backend creates Checkout Session with `venue_id` in metadata
- Webhook `payment_intent.succeeded` → add credits to venue
- Transaction logged in `credit_transactions`
- Atomic credit operations prevent race conditions

---

### Business Hours Enforcement

**Configuration:**
- Stored as JSONB: `{"monday": {"open": "11:00", "close": "22:00"}, ...}`
- Owner sets during onboarding
- Can update anytime via bot commands

**Enforcement:**
- Before showing menu, bot checks current time vs venue hours
- If closed: "We're closed right now! Our hours are Mon-Sun 11am-10pm." (in customer language)
- No ordering allowed outside hours

---

## Error Handling & Edge Cases

**LLM API Failures:**
- Timeout/rate limit → fallback to structured menu buttons
- Customer sees: "Let me show you our menu" + category buttons
- Retry with exponential backoff for transient errors
- Log all failures for monitoring

**Payment Failures:**
- Stripe retries webhooks automatically
- Check for duplicate events using `stripe_event_id`
- If credit addition fails, log to admin alert
- Owner can retry purchase

**Database Issues:**
- Connection pooling via Supabase
- Retry transient errors
- If database down: "Sorry, technical difficulties. Try again shortly."

**Race Conditions:**
- Order approval: Database transaction + status check (first action wins)
- Credit deduction: Atomic decrement `UPDATE venues SET credits_remaining = credits_remaining - 1 WHERE id = ? AND credits_remaining >= 1`
- If update affects 0 rows: Order blocked, owner notified

**Menu Parse Failures:**
- If PDF unreadable: "I'm having trouble with this PDF. Try uploading again or enter manually?"
- Still counts against 3 parse limit (prevents spam)

---

## Security & Compliance

**Data Privacy:**
- Store: Messenger ID, name, order history
- Retention: 90 days, then archive
- Deletion: Owner can request via `/delete customer <id>`
- Privacy policy required, linked in bot About section

**Authentication:**
- Owner verification via Meta Business Account
- Group verification: Bot checks admin permissions
- Venue isolation: All queries filter by `venue_id`

**Input Validation:**
- Sanitize all user inputs
- Parameterized queries (SQL injection prevention)
- No shell commands with user input
- Validate prices (positive, reasonable limits)

**API Security:**
- Verify Meta and Stripe webhook signatures
- Rate limiting per venue
- All credentials in environment variables
- HTTPS only

**Financial Security:**
- Stripe handles PCI compliance
- Audit trail for all credit transactions
- Monitor for chargebacks/fraud
- Manual refund process documented

---

## Testing Strategy

**Unit Tests:**
- Platform adapter (message normalization)
- LLM response parsing
- Credit deduction logic
- Menu PDF processing

**Integration Tests:**
- Messenger webhook handling
- Supabase operations
- Stripe webhook processing
- LLM API calls

**Manual Testing (Critical Flows):**
1. Owner onboarding end-to-end
2. Customer order + approval
3. Order rejection (verify 0.5 credit)
4. Sold-out items (verify hidden)
5. Credit purchase via Stripe
6. Multi-language customer ordering
7. Business hours enforcement

**Test Venues:**
- English menu, same approval/kitchen group
- Vietnamese menu, separate kitchen group
- Mixed language scenarios

**Beta Testing:**
- 2-3 friendly F&B owners
- Free credits during testing
- Gather feedback on UX, accuracy, flow

---

## Deployment

**Hosting (Railway/Render):**
- Python backend with FastAPI
- Deploy from GitHub (auto-deploy on push to main)
- Environment variables:
  - `FACEBOOK_PAGE_ACCESS_TOKEN`
  - `FACEBOOK_VERIFY_TOKEN`
  - `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
  - `SUPABASE_URL`, `SUPABASE_KEY`
  - `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
  - `VENUE_LANGUAGE_DEFAULT`

**Database (Supabase):**
- Free tier (500MB) for MVP
- Row Level Security enabled
- Automated backups
- Connection pooling (max 20)

**Meta Business Setup (Pre-Launch):**
1. Create Meta Business Account
2. Verify business (1-2 weeks, requires documents)
3. Create Facebook App, add Messenger product
4. Submit app review (Pages Messaging permission)
5. Generate Page Access Token
6. Configure webhook: `https://yourapp.railway.app/webhook`

**Stripe Setup:**
1. Create account
2. Configure credit packages
3. Set webhook: `https://yourapp.railway.app/stripe-webhook`
4. Test in test mode, then go live

**Monitoring:**
- Railway/Render logs
- Sentry for exception tracking
- UptimeRobot for endpoint health
- Admin alerts to Telegram/Slack

**Cost Estimates (Monthly):**
- Hosting: $5-20 (scales with usage)
- Supabase: Free tier
- LLM API: ~$0.01-0.05 per order (covered by credit revenue)
- Stripe: 2.9% + $0.30 per purchase
- **Total: ~$50-100/month** (excluding LLM costs)

---

## Success Metrics (Post-Launch)

**Product Metrics:**
- Owner onboarding completion rate (target: >80%)
- Average time to complete first order (target: <2 min)
- Order approval rate (target: >90%)
- Customer return rate (target: >40% order again)

**Business Metrics:**
- Active venues (paying customers)
- Orders per venue per day
- Credit purchase rate
- Revenue vs LLM API costs

**Quality Metrics:**
- Menu parse accuracy (target: >95% correct items)
- LLM understanding accuracy (target: >90% correct orders)
- Customer satisfaction (survey after order)

---

## Future Enhancements (Post-MVP)

**Phase 2 (After validating MVP):**
- WhatsApp integration (critical for market fit)
- Instagram DM support
- Payment integration (Stripe payment links for customers)
- Marketing campaigns (broadcast to past customers)
- Owner web dashboard (order analytics, menu management)

**Phase 3 (Scaling):**
- Kitchen display system integration (API/webhooks)
- Receipt printer integration
- POS system integrations
- Multi-location support for restaurant chains
- Advanced order status tracking ("Preparing", "Ready")

**Phase 4 (Advanced Features):**
- Reservation system
- Loyalty programs
- Inventory management integration
- Predictive ordering (suggest based on history)
- Voice ordering support

---

## Open Questions & Decisions Needed

1. **LLM Provider:** Anthropic Claude vs OpenAI GPT
   - Claude: Better at following instructions, newer models
   - GPT: Slightly cheaper, wider adoption
   - **Recommendation:** Start with Claude, easy to switch later

2. **Table Number Approach:**
   - Option A: QR per table (best UX)
   - Option B: Single QR, ask table number (cheaper)
   - **Recommendation:** QR per table for MVP

3. **Payment Integration Timing:**
   - MVP: Pay at counter (simplest)
   - v2: Add Stripe payment links
   - **Recommendation:** Skip payment integration for MVP

4. **Beta Launch Strategy:**
   - Find 2-3 friendly restaurant owners
   - Offer free credits + white-glove onboarding
   - Iterate based on feedback

---

## Conclusion

OrderOctopus MVP focuses on solving the core problem: slow, clunky app ordering. By using familiar chat interfaces (Facebook Messenger initially), natural language understanding, and a streamlined approval workflow, we enable restaurants to provide fast ordering experiences without building custom apps.

The platform adapter architecture ensures we can expand to WhatsApp, Telegram, and other channels quickly once we validate the concept with Messenger.

**Next Steps:**
1. Set up development environment (Python, Supabase, Meta Developer account)
2. Implement platform adapter + core business logic
3. Build owner onboarding flow
4. Integrate LLM for menu parsing and customer conversations
5. Add Stripe credit system
6. Deploy to Railway/Render
7. Beta test with 2-3 restaurants
8. Iterate and launch

**Timeline Estimate:** 6-8 weeks for functional MVP with beta testing.
