#!/usr/bin/env bash
# OPTIONAL, LOCAL-ONLY adapter (macOS): export the API keys from your login Keychain into THIS shell, so the tools
# (which read env vars only) can use them. Nothing in tools/ calls this; no shipped code reads the Keychain.
#
# One-time setup (stores the key in your Keychain under a service name you choose):
#   security add-generic-password -a "$USER" -s ELEVENLABS_API_KEY -w      # prompts for the value
#   security add-generic-password -a "$USER" -s OPENAI_API_KEY -w
# Then, per shell:
#   source tools/local/keychain_env.sh
# Keys are exported, never printed. A key that is not in the Keychain is skipped with a one-line note.
for name in ELEVENLABS_API_KEY OPENAI_API_KEY; do
  if value=$(security find-generic-password -a "$USER" -s "$name" -w 2>/dev/null); then
    export "$name=$value"
    echo "exported $name from the Keychain"
  else
    echo "skipped $name (not in the Keychain under service '$name')"
  fi
done
unset value name
