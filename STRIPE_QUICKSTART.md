# Stripe Integration - Quick Start Guide

Diese Anleitung hilft dir, die Stripe-Integration in wenigen Minuten einzurichten.

## Voraussetzungen

- Stripe Account (https://dashboard.stripe.com)
- Stripe CLI installiert (`brew install stripe/stripe-cli/stripe` auf macOS)
- Docker & Docker Compose installiert
- Development Environment läuft (`./start-dev.sh --full`)

## 🚀 Schnellstart (5 Minuten)

### Schritt 1: Stripe Produkte erstellen (2 Minuten)

1. Öffne https://dashboard.stripe.com/test/products
2. Klicke auf **"Add Product"**

#### Produkt 1: Starter Plan
```
Name: ExamCraft Starter
Description: For serious exam creators
Price: €19.00 EUR / month
Billing: Recurring / Monthly
```
Kopiere die **Price ID** (beginnt mit `price_...`)

#### Produkt 2: Professional Plan
```
Name: ExamCraft Professional
Description: Unlimited power for professional exam creation
Price: €149.00 EUR / month
Billing: Recurring / Monthly
```
Kopiere die **Price ID** (beginnt mit `price_...`)

### Schritt 2: API Keys kopieren (1 Minute)

1. Öffne https://dashboard.stripe.com/test/apikeys
2. Kopiere den **Secret key** (beginnt mit `sk_test_`)

### Schritt 3: Environment Variables setzen (1 Minute)

Füge folgende Zeilen zu deiner `.env` Datei hinzu:

```env
# Stripe Configuration
STRIPE_SECRET_KEY=<YOUR_STRIPE_SECRET_KEY>        # Dein Secret Key
STRIPE_WEBHOOK_SECRET=<YOUR_STRIPE_WEBHOOK_SECRET>  # Wird im nächsten Schritt generiert
REACT_APP_STRIPE_PRICE_STARTER=price_...         # Starter Price ID
REACT_APP_STRIPE_PRICE_PROFESSIONAL=price_...    # Professional Price ID
```

### Schritt 4: Lokales Webhook Testing starten (1 Minute)

Öffne ein **neues Terminal** und führe aus:

```bash
./scripts/stripe-webhook-test.sh
```

Das Script wird:
- Stripe CLI mit deinem Backend verbinden
- Einen **Webhook Signing Secret** generieren
- Diesen Secret als `whsec_<SECRET>` ausgeben

**WICHTIG:** Kopiere den Webhook Secret und füge ihn zu `.env` hinzu:

```env
STRIPE_WEBHOOK_SECRET=<YOUR_STRIPE_WEBHOOK_SECRET>  # Der generierte Secret
```

Starte dann das Backend neu:

```bash
docker compose --env-file .env -f docker-compose.full.yml restart backend
```

### Schritt 5: Testen! (1 Minute)

1. Öffne http://localhost:3000/billing
2. Klicke auf **"Subscribe"** beim Starter Plan
3. Du wirst zu Stripe Checkout weitergeleitet
4. Verwende Test Card:
   ```
   Card Number: 4242 4242 4242 4242
   Expiry: 12/25
   CVC: 123
   ZIP: 12345
   ```
5. Nach erfolgreicher Zahlung:
   - Du wirst auf `/billing/success` weitergeleitet
   - Der Webhook wird empfangen (siehe Terminal mit `stripe listen`)
   - Eine Subscription wird in der Datenbank erstellt

### Datenbank prüfen

```bash
docker exec -it examcraft-postgres-1 psql -U examcraft -d examcraft -c "SELECT * FROM subscriptions;"
```

## 🎉 Fertig!

Deine Stripe-Integration ist nun voll funktionsfähig!

## 📚 Weitere Ressourcen

- Ausführliche Anleitung: `STRIPE_SETUP_GUIDE.md`
- Test Events triggern: `./scripts/stripe-trigger-test-events.sh`
- Stripe Dashboard: https://dashboard.stripe.com
- Stripe API Docs: https://stripe.com/docs/api

## ⚙️ Konfiguration

### Frontend Price IDs

Price IDs können auf zwei Arten konfiguriert werden:

**Option 1: Environment Variables (Empfohlen für Production)**
```env
REACT_APP_STRIPE_PRICE_STARTER=price_...
REACT_APP_STRIPE_PRICE_PROFESSIONAL=price_...
```

**Option 2: Direkt im Code (Für Development)**
Editiere `packages/core/frontend/src/config/stripe.config.ts`:
```typescript
export const STRIPE_PRICES: StripePriceConfig = {
  starter: 'price_...',
  professional: 'price_...',
};
```

### Tier Mapping (Backend)

Wenn du mehrere Pläne hast, aktualisiere das Tier Mapping in `packages/core/backend/api/v1/webhooks.py`:

```python
tier_mapping = {
    "price_1abc...": "starter",
    "price_1xyz...": "professional",
}
```

## 🐛 Troubleshooting

### Problem: "Payment service is not configured"
**Lösung:** `STRIPE_SECRET_KEY` fehlt in `.env`. Backend neu starten.

### Problem: Webhook wird nicht empfangen
**Lösung:**
- Stelle sicher, dass `stripe listen` läuft
- Überprüfe `STRIPE_WEBHOOK_SECRET` in `.env`
- Backend neu starten

### Problem: "Invalid signature" bei Webhook
**Lösung:**
- Der Webhook Secret stimmt nicht überein
- Verwende den Secret aus dem `stripe listen` Output
- Backend neu starten

### Problem: "User must be associated with an institution"
**Lösung:**
- User muss einer Institution zugeordnet sein
- Admin UI verwenden, um Institution zu erstellen und User zuzuweisen

## 🚀 Production Deployment

Für Production:

1. **Verwende Live Mode Keys** (nicht Test Mode)
   ```env
   STRIPE_SECRET_KEY=<YOUR_STRIPE_LIVE_SECRET_KEY>
   ```

2. **Erstelle Webhook im Dashboard**
   - URL: `https://your-domain.com/api/v1/webhooks/stripe`
   - Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
   - Kopiere den Signing Secret

3. **Setze Production Environment Variables**
   ```env
   STRIPE_SECRET_KEY=<YOUR_STRIPE_LIVE_SECRET_KEY>
   STRIPE_WEBHOOK_SECRET=<YOUR_STRIPE_WEBHOOK_SECRET>  # Aus Stripe Dashboard
   REACT_APP_STRIPE_PRICE_STARTER=price_...
   REACT_APP_STRIPE_PRICE_PROFESSIONAL=price_...
   ```

4. **Deploy**
   - Stelle sicher, dass der Webhook Endpoint öffentlich erreichbar ist (HTTPS!)
   - Teste mit echten Zahlungen oder Stripe Test Mode

## 📝 Nächste Schritte

Nach erfolgreicher Integration:

- [ ] Customer Portal für Subscription Management
- [ ] Email-Benachrichtigungen bei Subscription Events
- [ ] Upgrade/Downgrade zwischen Tiers
- [ ] Rechnungs-History für Kunden
- [ ] Automatische Trial Period
- [ ] Coupon/Discount Codes
