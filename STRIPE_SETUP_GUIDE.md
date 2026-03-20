# Stripe Integration Setup Guide

## Schritt 1: Stripe Dashboard - Products erstellen

1. Gehe zu https://dashboard.stripe.com/test/products
2. Klicke auf "Add Product"

### Produkt 1: ExamCraft Starter
- **Name**: ExamCraft Starter
- **Description**: For serious exam creators
- **Pricing Model**: Recurring
- **Price**: €19.00 EUR
- **Billing Period**: Monthly
- **After Creation**: Kopiere die **Price ID** (beginnt mit `price_...`)

### Produkt 2: ExamCraft Professional
- **Name**: ExamCraft Professional
- **Description**: Unlimited power for professional exam creation
- **Pricing Model**: Recurring
- **Price**: €149.00 EUR
- **Billing Period**: Monthly
- **After Creation**: Kopiere die **Price ID** (beginnt mit `price_...`)

## Schritt 2: API Keys kopieren

1. Gehe zu https://dashboard.stripe.com/test/apikeys
2. Kopiere:
   - **Publishable key** (beginnt mit `pk_test_...`) - Wird NICHT benötigt (Checkout Session Redirect)
   - **Secret key** (beginnt mit `sk_test_`) - WICHTIG! Zur .env hinzufügen

## Schritt 3: Webhook erstellen

1. Gehe zu https://dashboard.stripe.com/test/webhooks
2. Klicke auf "Add endpoint"
3. **Endpoint URL**: `http://localhost:8000/api/v1/webhooks/stripe` (für Development)
   - Für Production: `https://your-domain.com/api/v1/webhooks/stripe`
4. **Events to send**: Wähle diese Events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
5. **After Creation**: Kopiere den **Signing secret** (beginnt mit `whsec_`)

## Schritt 4: Environment Variables aktualisieren

Füge diese Variablen zu deiner `.env` Datei hinzu:

```env
# Stripe Configuration
STRIPE_SECRET_KEY=<YOUR_STRIPE_SECRET_KEY>  # Dein Secret Key von Schritt 2
STRIPE_WEBHOOK_SECRET=<YOUR_STRIPE_WEBHOOK_SECRET>  # Dein Webhook Secret von Schritt 3
```

## Schritt 5: Price IDs im Frontend aktualisieren

Öffne `packages/core/frontend/src/pages/BillingPage.tsx` und ersetze:

```typescript
const STARTER_PRICE_ID = 'price_...';  // Deine Starter Price ID von Schritt 1
const PROFESSIONAL_PRICE_ID = 'price_...';  // Deine Professional Price ID (wenn implementiert)
```

## Schritt 6: Test durchführen

1. Starte die Development-Umgebung:
   ```bash
   ./start-dev.sh --full
   ```

2. Öffne http://localhost:3000/billing

3. Klicke auf "Subscribe" beim Starter Plan

4. Du wirst zu Stripe Checkout weitergeleitet

5. Verwende Test Card: `4242 4242 4242 4242`
   - Expiry: Beliebiges zukünftiges Datum (z.B. 12/25)
   - CVC: Beliebige 3 Ziffern (z.B. 123)
   - ZIP: Beliebige 5 Ziffern (z.B. 12345)

6. Nach erfolgreicher Zahlung solltest du auf `/billing/success` weitergeleitet werden

7. Überprüfe in der Datenbank, ob eine Subscription erstellt wurde:
   ```bash
   docker exec -it examcraft-postgres-1 psql -U examcraft -d examcraft
   SELECT * FROM subscriptions;
   ```

## Wichtige Hinweise

### Stripe CLI für Webhook Testing (Lokal)

Wenn du lokal testest und Webhooks empfangen möchtest:

```bash
stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe
```

Dies gibt dir einen **Webhook Signing Secret** für lokale Tests. Füge diesen zu deiner `.env` hinzu:

```env
STRIPE_WEBHOOK_SECRET=<YOUR_STRIPE_WEBHOOK_SECRET>  # Von stripe listen Befehl
```

### Production Deployment

Für Production:
1. Verwende **Live Mode** Keys (nicht Test Mode)
2. Webhook URL muss öffentlich erreichbar sein (HTTPS!)
3. Stelle sicher, dass der Webhook Secret aus dem Stripe Dashboard kommt (nicht von `stripe listen`)

## Troubleshooting

### Problem: "Payment service is not configured"
- Lösung: Stelle sicher, dass `STRIPE_SECRET_KEY` in `.env` gesetzt ist
- Starte Backend neu: `docker compose restart backend`

### Problem: Webhook wird nicht empfangen
- Lösung: Verwende `stripe listen` für lokale Tests
- Prüfe, ob `STRIPE_WEBHOOK_SECRET` korrekt in `.env` gesetzt ist

### Problem: "Invalid signature" bei Webhook
- Lösung: Der Webhook Secret stimmt nicht mit der Signatur überein
- Verwende für lokale Tests den Secret von `stripe listen`
- Verwende für Production den Secret aus dem Stripe Dashboard

## Nächste Schritte

Nach erfolgreichem Test:
1. Implementiere Professional Tier Subscription
2. Füge Subscription Management hinzu (Cancel, Upgrade, Downgrade)
3. Implementiere Customer Portal für Rechnungen
4. Füge Email-Benachrichtigungen hinzu
