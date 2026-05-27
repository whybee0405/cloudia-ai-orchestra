# CloudIA Content & Marketing Agent System

Multi-agent content creation and marketing system for CloudIA — a South African digital agency serving SMEs.

Handles the complete lifecycle: campaign planning → content creation (text, images, video) → editing and brand consistency → human approval → scheduling → publishing → analytics.

## Quick Start (Dev)

```bash
cp .env.example .env
# Fill in API keys and passwords in .env
# Generate an ENCRYPTION_KEY:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

cd docker
docker compose up --build
```

Services:
- API: http://localhost:8001
- Frontend: http://localhost:5174
- MinIO Console: http://localhost:9001
- PostgreSQL: localhost:5433
- Redis: localhost:6380

## Architecture

See `docs/ARCHITECTURE.md` for the full system design.

## Build Phases

1. Foundation — Docker, DB models, config
2. AI + Context Layer — Claude, DALL-E, ElevenLabs wrappers
3. Director + Planner agents
4. Text agents — copywriter, SEO, ad copy
5. Image agents — generation, sourcing, editing
6. Video agents — script, voiceover, b-roll, assembly, editing
7. OAuth + Platform connectors
8. Publishing pipeline — formatter, scheduler, publisher
9. Analytics agent
10. Full API + Frontend GUI
11. Documentation

## Platform Priority

Primary: Instagram, Facebook, WhatsApp Business, Google Business  
Secondary: LinkedIn, TikTok  
Tertiary: YouTube, Twitter/X

## Security

- Per-client OAuth tokens (Option B) — never shared between clients
- All tokens encrypted at rest with Fernet
- `ENCRYPTION_KEY` required at startup — application refuses to run without it
- OAuth state tokens cryptographically random, consumed on first use
