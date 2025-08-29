#!/bin/bash
# TiDB Health Check Script - Secure password handling

# Create temporary MySQL config file with credentials
MYSQL_CONFIG=$(mktemp)
cat > "$MYSQL_CONFIG" << EOF
[client]
host=localhost
port=4000
user=root
password=${TIDB_PASSWORD}
EOF

# Set restrictive permissions on config file
chmod 600 "$MYSQL_CONFIG"

# Perform health check using config file
mysql --defaults-file="$MYSQL_CONFIG" -e "SELECT 1" >/dev/null 2>&1
RESULT=$?

# Clean up temporary config file
rm -f "$MYSQL_CONFIG"

exit $RESULT