# GCP Deployment Guide for SAM 3D Objects

This guide explains how to deploy and run the SAM 3D Objects web application on Google Cloud Platform (GCP).

## Prerequisites

- GCP Compute Engine VM instance
- Ubuntu 20.04 or later
- GPU instance (recommended: NVIDIA T4 or better)
- Python 3.10+
- Node.js 18+
- CUDA drivers installed (for GPU support)

## Firewall Configuration

### Ports to Open in GCP Firewall

You need to open the following ports in your GCP firewall rules:

1. **Port 8000** - Backend API server
2. **Port 5173** - Frontend development server (or your custom port)

### Creating Firewall Rules in GCP

```bash
# Allow Backend API traffic
gcloud compute firewall-rules create allow-backend-api \
  --allow tcp:8000 \
  --source-ranges 0.0.0.0/0 \
  --description "Allow SAM 3D Backend API"

# Allow Frontend traffic
gcloud compute firewall-rules create allow-frontend \
  --allow tcp:5173 \
  --source-ranges 0.0.0.0/0 \
  --description "Allow SAM 3D Frontend"
```

Or via GCP Console:
1. Go to **VPC Network** > **Firewall**
2. Click **Create Firewall Rule**
3. Name: `allow-sam3d-ports`
4. Direction: Ingress
5. Action on match: Allow
6. Targets: All instances (or specific tags)
7. Source IP ranges: `0.0.0.0/0` (or your specific IP)
8. Protocols and ports: `tcp:8000,5173`

## Deployment Steps

### 1. Clone Repository

```bash
git clone https://github.com/your-repo/sam-3d-objects.git
cd sam-3d-objects
```

### 2. Install Model Checkpoints

Follow the instructions in `doc/setup.md` to download model weights from HuggingFace.

### 3. Configure for Remote Access

#### Backend Configuration

The backend now automatically allows all origins. For production, set specific origins:

```bash
# On your GCP VM
export ALLOWED_ORIGINS="http://YOUR_GCP_EXTERNAL_IP:5173,http://YOUR_GCP_EXTERNAL_IP:8000"
```

Or edit `backend/main.py` to specify your domains.

#### Frontend Configuration

Create a `.env` file in the `frontend/` directory:

```bash
cd frontend
cat > .env << EOF
VITE_API_URL=http://YOUR_GCP_EXTERNAL_IP:8000
EOF
```

Replace `YOUR_GCP_EXTERNAL_IP` with your actual GCP external IP address.

### 4. Start Backend Server

```bash
cd backend
pip install -r requirements.txt

# Run with uvicorn (allows external access)
uvicorn main:app --host 0.0.0.0 --port 8000
```

Or use the Python script directly (already configured for 0.0.0.0):

```bash
python main.py
```

### 5. Start Frontend Server

In a new terminal:

```bash
cd frontend
npm install

# Development mode (accessible from external IPs)
npm run dev
```

The frontend Vite config is now set to listen on `0.0.0.0`, allowing external access.

## Accessing from Your Local PC

Once both servers are running on GCP:

1. **Get your GCP instance external IP:**
   ```bash
   gcloud compute instances list
   ```
   Or check the GCP Console.

2. **Access the application:**
   - Frontend: `http://YOUR_GCP_EXTERNAL_IP:5173`
   - Backend API: `http://YOUR_GCP_EXTERNAL_IP:8000`
   - API Docs: `http://YOUR_GCP_EXTERNAL_IP:8000/docs`

## Production Deployment (Recommended)

For production use, instead of exposing both ports, use **Nginx as a reverse proxy**.

### Option 2: Production with Nginx (Single Port)

This is more secure and only exposes port 80 (HTTP) or 443 (HTTPS).

#### 1. Build Frontend for Production

```bash
cd frontend
npm run build
```

This creates optimized files in `frontend/dist/`.

#### 2. Install and Configure Nginx

```bash
sudo apt update
sudo apt install nginx -y
```

Create Nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/sam3d
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name YOUR_GCP_EXTERNAL_IP;

    # Frontend (static files)
    location / {
        root /home/YOUR_USERNAME/sam-3d-objects/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/sam3d /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 3. Update Frontend Environment

For production with Nginx, the frontend should use relative URLs:

```bash
# frontend/.env.production
VITE_API_URL=
```

Or remove the `.env` file entirely (defaults to relative paths).

#### 4. Update Firewall for Production

```bash
# Allow HTTP (port 80)
gcloud compute firewall-rules create allow-http \
  --allow tcp:80 \
  --source-ranges 0.0.0.0/0

# Optional: Allow HTTPS (port 443)
gcloud compute firewall-rules create allow-https \
  --allow tcp:443 \
  --source-ranges 0.0.0.0/0
```

#### 5. Start Backend with Systemd (Production)

Create a systemd service for auto-restart:

```bash
sudo nano /etc/systemd/system/sam3d-backend.service
```

Add:

```ini
[Unit]
Description=SAM 3D Objects Backend
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/sam-3d-objects
ExecStart=/usr/bin/python3 backend/main.py
Restart=always
RestartSec=10
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sam3d-backend
sudo systemctl start sam3d-backend
sudo systemctl status sam3d-backend
```

#### 6. Access Your Application

Now you can access the application at:
- `http://YOUR_GCP_EXTERNAL_IP`

Only port 80 is exposed, and Nginx handles routing to both frontend and backend.

## Summary: Which Ports to Expose

### Development Mode (Quick Testing)
- **Port 8000** - Backend API
- **Port 5173** - Frontend
- Total: 2 ports

### Production Mode (Recommended)
- **Port 80** - HTTP (Nginx serves both frontend and backend)
- **Port 443** - HTTPS (if using SSL)
- Total: 1-2 ports

## Security Recommendations

1. **Use HTTPS**: Get a free SSL certificate with Let's Encrypt
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

2. **Restrict Source IPs**: Instead of `0.0.0.0/0`, use your specific IP range

3. **Use Authentication**: Add API key or JWT authentication

4. **Set up monitoring**: Use Google Cloud Monitoring or other tools

5. **Regular updates**: Keep dependencies and system packages updated

6. **Backup data**: Regularly backup generated models and user data

## Troubleshooting

### Cannot Connect to Frontend
- Check firewall rules: `gcloud compute firewall-rules list`
- Verify Vite is listening on `0.0.0.0`: Check terminal output
- Test locally first: `curl http://localhost:5173`

### Cannot Connect to Backend
- Check if backend is running: `ps aux | grep python`
- Verify port is open: `sudo netstat -tulpn | grep 8000`
- Check backend logs for errors

### CORS Errors
- Verify `ALLOWED_ORIGINS` is set correctly
- Check browser console for specific CORS error
- Ensure frontend `.env` has correct API URL

### API Requests Failing
- Verify `VITE_API_URL` in frontend `.env`
- Check network tab in browser dev tools
- Test API directly: `curl http://YOUR_IP:8000/health`

### GPU Not Being Used
- Check CUDA installation: `nvidia-smi`
- Verify PyTorch sees GPU: `python -c "import torch; print(torch.cuda.is_available())"`
- Check GPU drivers are loaded

## Cost Optimization

GCP GPU instances can be expensive. To reduce costs:

1. **Use Preemptible VMs**: Up to 80% cheaper
2. **Stop instance when not in use**: Only pay for storage
3. **Use Spot VMs**: Similar to preemptible but newer
4. **Choose appropriate GPU**: T4 is cheaper than V100/A100
5. **Set up budget alerts**: Get notified before overspending

## Next Steps

- Set up HTTPS with Let's Encrypt
- Configure domain name instead of IP
- Implement user authentication
- Set up automatic backups
- Configure monitoring and alerts
- Optimize for production workload
