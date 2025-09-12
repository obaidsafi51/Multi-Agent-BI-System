# TiDB MCP Server Bootstrap Guide

## Initial Setup for New Deployments

### 1. Environment Configuration

Create a `.env` file with admin credentials:

```bash
# Database Configuration
TIDB_HOST=your-tidb-host.clusters.tidb-cloud.com
TIDB_PORT=4000
TIDB_USER=your-username
TIDB_PASSWORD=your-password
TIDB_DATABASE=your-database-name

# Admin Bootstrap Configuration
ADMIN_BOOTSTRAP_ENABLED=true
ADMIN_BOOTSTRAP_TOKEN=your-secure-bootstrap-token-here
ADMIN_DEFAULT_EMAIL=admin@yourcompany.com
ADMIN_DEFAULT_PASSWORD=change-this-secure-password

# LLM Configuration
LLM_API_KEY=your-kimi-api-key

# Security
JWT_SECRET=your-jwt-secret-key
ENCRYPT_KEY=your-32-char-encryption-key
```

### 2. First Time Setup

1. **Start the server:**

   ```bash
   uv run python -m src.tidb_mcp_server.main
   ```

2. **Bootstrap the admin user (one-time only):**

   ```bash
   curl -X POST http://localhost:8000/admin/bootstrap \
     -H "Content-Type: application/json" \
     -d '{
       "bootstrap_token": "your-secure-bootstrap-token-here",
       "admin_email": "admin@yourcompany.com",
       "admin_password": "change-this-secure-password"
     }'
   ```

3. **Initialize the MCP server:**
   ```bash
   curl -X POST http://localhost:8000/admin/initialize \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
   ```

### 3. Subsequent Access

After bootstrap, all admin operations require authentication:

```bash
# Login to get JWT token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourcompany.com",
    "password": "your-password"
  }'

# Use token for admin operations
curl -X POST http://localhost:8000/admin/initialize \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4. Security Considerations

- **Disable Bootstrap**: Set `ADMIN_BOOTSTRAP_ENABLED=false` after initial setup
- **Change Default Passwords**: Always change default admin passwords
- **Use Strong Tokens**: Generate cryptographically secure bootstrap tokens
- **Environment Variables**: Never commit `.env` files to version control
- **Network Security**: Restrict admin endpoints to authorized networks
