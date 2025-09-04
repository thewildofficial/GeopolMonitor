# Environment Configuration

## Required Environment Variables

### Frontend (Next.js)

The frontend requires the following environment variables to be set:

#### `NEXT_PUBLIC_WS_URL` (Required)
- **Description**: WebSocket server URL for real-time communication
- **Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com` (or your WebSocket server URL)
- **Example**: `NEXT_PUBLIC_WS_URL=https://api.geopolmonitor.com`

#### `NEXT_PUBLIC_API_URL` (Optional)
- **Description**: Backend API base URL
- **Default**: Same as WebSocket URL
- **Example**: `NEXT_PUBLIC_API_URL=https://api.geopolmonitor.com`

## Environment Setup

### Development
Create a `.env.local` file in the frontend directory:

```bash
# .env.local
NEXT_PUBLIC_WS_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
NODE_ENV=development
```

### Production
Set environment variables in your deployment platform:

```bash
NEXT_PUBLIC_WS_URL=https://your-websocket-server.com
NEXT_PUBLIC_API_URL=https://your-api-server.com
NODE_ENV=production
```

## Important Notes

1. **Production Requirement**: The `NEXT_PUBLIC_WS_URL` environment variable is **required** in production. The application will throw an error if it's not set.

2. **No Localhost Fallback**: In production environments, the application will not fall back to localhost URLs to prevent connection issues.

3. **Development Fallback**: In development mode, the application will use `http://localhost:8000` as a fallback if no environment variable is set.

4. **Error Handling**: The application provides clear error messages when WebSocket connections fail, especially in production environments.

## Troubleshooting

### WebSocket Connection Issues

If you see connection errors:

1. **Check Environment Variables**: Ensure `NEXT_PUBLIC_WS_URL` is set correctly
2. **Verify Server**: Make sure the WebSocket server is running and accessible
3. **Check Network**: Ensure there are no firewall or network issues
4. **Review Logs**: Check browser console for detailed error messages

### Common Error Messages

- `"WebSocket URL not configured for production environment"`: Set `NEXT_PUBLIC_WS_URL` in production
- `"Failed to connect to WebSocket server"`: Check server availability and URL configuration
