# Configuration

The web UI is configured via environment variables or a `.env` file.

## Environment Variables

All variables are prefixed with `UPTIMER_`.

| Variable | Default | Description |
|----------|---------|-------------|
| `UPTIMER_USERNAME` | `admin` | Login username |
| `UPTIMER_PASSWORD` | `admin` | Login password |
| `UPTIMER_SECRET_KEY` | `change-me-in-production` | Secret key for session signing |
| `UPTIMER_HOST` | `127.0.0.1` | Default server host |
| `UPTIMER_PORT` | `8000` | Default server port |

## .env File

Create a `.env` file in the project root:

```bash
# Copy the example
cp .env.example .env

# Edit with your settings
nano .env
```

Example `.env`:

```ini
UPTIMER_USERNAME=admin
UPTIMER_PASSWORD=secure-password-here
UPTIMER_SECRET_KEY=your-random-secret-key
UPTIMER_HOST=0.0.0.0
UPTIMER_PORT=8080
```

## Security Recommendations

### Secret Key

Generate a secure random secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Production Checklist

1. **Change default credentials** - Never use `admin/admin` in production
2. **Set a strong secret key** - Use a randomly generated key
3. **Use HTTPS** - Put behind a reverse proxy with TLS
4. **Restrict host binding** - Use `127.0.0.1` if behind a proxy

### Reverse Proxy

Example nginx configuration:

```nginx
server {
    listen 443 ssl;
    server_name uptimer.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Session Management

- Sessions are stored in cookies
- Session lifetime: 24 hours
- Sessions are signed with the secret key
- Logout clears the session cookie
