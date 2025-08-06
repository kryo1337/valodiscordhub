#!/bin/bash

# Secret encoding helper script for ValoDiscordHub
echo "🔐 ValoDiscordHub Secret Encoder"
echo "This script will help you encode your secrets for Kubernetes"
echo ""

# Function to encode a secret
encode_secret() {
    local secret_name=$1
    local prompt_text=$2
    
    echo -n "$prompt_text: "
    read -s secret_value
    echo ""
    
    if [ -n "$secret_value" ]; then
        encoded_value=$(echo -n "$secret_value" | base64)
        echo "  $secret_name: $encoded_value"
    else
        echo "  $secret_name: <base64-encoded-value>"
    fi
}

echo "📝 Discord Secrets:"
encode_secret "DISCORD_TOKEN" "Enter your Discord Bot Token"
encode_secret "DISCORD_CLIENT_ID" "Enter your Discord Client ID"
encode_secret "DISCORD_CLIENT_SECRET" "Enter your Discord Client Secret"
encode_secret "BOT_API_TOKEN" "Enter your Bot API Token"
encode_secret "JWT_SECRET" "Enter your JWT Secret"

echo ""
echo "📝 MongoDB Secrets:"
encode_secret "MONGO_INITDB_ROOT_USERNAME" "Enter MongoDB Username"
encode_secret "MONGO_INITDB_ROOT_PASSWORD" "Enter MongoDB Password"

echo ""
echo "✅ Copy these values to k8s/secrets.yaml"
echo "⚠️  Make sure to keep your secrets secure!" 