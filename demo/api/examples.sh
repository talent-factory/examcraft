# Login und Token erhalten
PASSWORD="YOUR_PASSWORD"  # pragma: allowlist secret
TOKEN=$(curl -X 'POST' \
  'http://localhost:8000/api/auth/login' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d "{
  \"email\": \"daniel.senften@talent-factory.ch\",
  \"password\": \"$PASSWORD\"
}" | jq -r '.access_token')

# Subscription abrufen
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/billing/subscription | jq


stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe 2>&1
