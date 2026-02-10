# Portainer Deployment Guide

This guide covers deploying the Patient Scheduling application to a remote Docker host managed by Portainer.

## Docker Compose Files

This project includes two Docker Compose configurations:
- **`docker-compose.yml`** - For local development (builds from source)
- **`docker-compose.portainer.yml`** - For production/Portainer deployment (uses registry image)

## Prerequisites

- Portainer instance running and accessible
- Docker host connected to Portainer
- GitHub Container Registry image built (via GitHub Actions) OR ability to build locally

## Deployment Options

### Option 1: Using GitHub Container Registry (Recommended)

This is the easiest method for remote deployment.

#### Step 1: Make Image Public (One-time setup)

1. Push code to GitHub to trigger the build workflow
2. Go to your GitHub repository
3. Click **Packages** in the right sidebar
4. Click the **patient-scheduling** package
5. Click **Package settings**
6. Scroll to **Danger Zone**
7. Click **Change visibility** → **Public**

#### Step 2: Update docker-compose.portainer.yml

Edit `docker-compose.portainer.yml` and replace `<your-username>` with your actual GitHub username:

```yaml
image: ghcr.io/your-actual-username/patient-scheduling:latest
```

#### Step 3: Deploy in Portainer

1. Log into Portainer
2. Select your Docker environment
3. Go to **Stacks** → **Add stack**
4. Choose one of these methods:

   **Method A: Git Repository (Recommended)**
   - Name: `patient-scheduling`
   - Build method: **Repository**
   - Repository URL: `https://github.com/your-username/patient-scheduling`
   - Repository reference: `refs/heads/main`
   - Compose path: `docker-compose.portainer.yml`
   - Click **Deploy the stack**

   **Method B: Web editor**
   - Name: `patient-scheduling`
   - Build method: **Web editor**
   - Paste the contents of your `docker-compose.portainer.yml`
   - Click **Deploy the stack**

#### Step 4: Verify Deployment

1. Go to **Containers** in Portainer
2. Find `patient-scheduling_app_1` (or similar)
3. Check that status is **running**
4. Click **Quick actions** → **Logs** to verify startup
5. Access the application at `http://your-docker-host:8080`

---

### Option 2: Using Private Registry (If Image is Private)

If you don't want to make your image public, you'll need to configure registry authentication.

#### Step 1: Create GitHub Personal Access Token

1. Go to GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Click **Generate new token** → **Generate new token (classic)**
3. Name: `Portainer Registry Access`
4. Scopes: Check `read:packages`
5. Click **Generate token**
6. **Copy the token** (you won't see it again!)

#### Step 2: Add Registry in Portainer

1. In Portainer, go to **Registries** → **Add registry**
2. Choose **Custom registry**
3. Fill in:
   - Name: `GitHub Container Registry`
   - Registry URL: `ghcr.io`
   - Authentication: **ON**
   - Username: Your GitHub username
   - Password: Paste the Personal Access Token
4. Click **Add registry**

#### Step 3: Deploy Stack

Follow the same deployment steps as Option 1, Step 3. Portainer will now automatically authenticate to pull the private image.

---

### Option 3: Build on Remote Host

If you prefer to build the image on your Docker host (not recommended for production):

1. Make sure your Docker host has:
   - Node.js 18+ installed
   - Python 3.11+ installed
   - Git access to your repository

2. Use `docker-compose.yml` instead of `docker-compose.portainer.yml` for the Compose path

3. In Portainer, use **Method A: Git Repository** (as shown above)
   - Repository reference: `refs/heads/main`
   - Compose path: `docker-compose.yml` (local dev version)
   - Portainer will clone the repo and build the image on the host

**Note**: This method is slower and requires build dependencies on the remote host.

---

## Managing Data Persistence

The `docker-compose.yml` uses a named volume `patient-scheduling-data` to persist schedules between container updates.

### Backup Data

In Portainer:
1. Go to **Volumes**
2. Find `patient-scheduling_patient-scheduling-data`
3. Click **Browse** to view files
4. Download `schedules.json` and `specialties.json` to back up

### Restore Data

1. Stop the stack: **Stacks** → `patient-scheduling` → **Stop**
2. Go to **Volumes** → `patient-scheduling_patient-scheduling-data` → **Browse**
3. Upload your backup files
4. Restart the stack: **Stacks** → `patient-scheduling` → **Start**

---

## Updating the Application

### Using GitHub Container Registry

1. Push updates to GitHub (triggers automatic build)
2. Wait for GitHub Actions to complete (~2-5 minutes)
3. In Portainer:
   - **Stacks** → `patient-scheduling`
   - Click **Pull and redeploy**
   - Select **Re-pull image and redeploy**
   - Click **Update**

### Using Build Method

1. Push updates to GitHub
2. In Portainer:
   - **Stacks** → `patient-scheduling`
   - Scroll to **Stack file** section
   - Click **Update the stack**

---

## Monitoring

### View Logs

In Portainer:
- **Containers** → `patient-scheduling_app_1`
- Click **Logs**
- Toggle **Auto-refresh** to watch live logs

### Resource Usage

- **Containers** → `patient-scheduling_app_1`
- Click **Stats** to see CPU, memory, and network usage

### Health Check

Access `http://your-docker-host:8080` to verify the application is running.

---

## Troubleshooting

### Container won't start

1. Check logs: **Containers** → `patient-scheduling_app_1` → **Logs**
2. Common issues:
   - Port 8080 already in use: Change port in docker-compose.yml to `"8081:8080"`
   - Volume permission issues: Check volume browse functionality

### Can't pull image

1. Verify the image exists:
   ```bash
   docker pull ghcr.io/your-username/patient-scheduling:latest
   ```
2. If private, verify registry authentication is configured
3. Check image name matches exactly (case-sensitive)

### Application not accessible

1. Check firewall rules on Docker host (port 8080 must be open)
2. Verify container is running: **Containers** list
3. Check port mapping: Should show `0.0.0.0:8080->8080/tcp`

### Data not persisting

1. Verify named volume is created: **Volumes** → `patient-scheduling_patient-scheduling-data`
2. Check volume is mounted: **Containers** → `patient-scheduling_app_1` → **Inspect** → Mounts

---

## Advanced Configuration

### Custom Port

Edit docker-compose.yml:
```yaml
ports:
  - "8081:8080"  # Host port 8081, container port 8080
```

### Environment Variables

Add to docker-compose.yml under `environment:`:
```yaml
environment:
  - PYTHONUNBUFFERED=1
  - API_BASE_URL=http://your-domain.com/api  # If using reverse proxy
```

### Using with Reverse Proxy (nginx, Traefik)

Add labels for Traefik:
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.patient-scheduling.rule=Host(`scheduling.yourdomain.com`)"
  - "traefik.http.services.patient-scheduling.loadbalancer.server.port=8080"
```

---

## Security Best Practices

1. **Use HTTPS**: Place behind a reverse proxy with SSL/TLS
2. **Restrict Access**: Use firewall rules or VPN to limit who can access port 8080
3. **Regular Updates**: Keep the application updated via GitHub Actions
4. **Backup Data**: Regular backups of the `patient-scheduling-data` volume
5. **Monitor Logs**: Check logs regularly for suspicious activity

---

## Support

- GitHub Issues: https://github.com/your-username/patient-scheduling/issues
- Docker Documentation: https://docs.docker.com/
- Portainer Documentation: https://docs.portainer.io/
