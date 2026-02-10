# Deployment Guide

## GitHub Actions CI/CD

This project uses GitHub Actions to automatically build and push Docker images to GitHub Container Registry (ghcr.io).

### Automatic Builds

Images are automatically built and pushed when:
- **Push to `main` branch**: Tagged as `latest` and `main`
- **Push to `auto-scheduling` branch**: Tagged as `auto-scheduling`
- **Pull Request**: Tagged as `pr-<number>`
- **Release**: Tagged with version number (e.g., `v1.0.0`)
- **Every push**: Tagged with commit SHA (e.g., `main-abc1234`)

### Image Tags

The workflow creates the following tags:
- `latest` - Latest build from main branch
- `main` - Latest build from main branch
- `auto-scheduling` - Latest build from auto-scheduling branch
- `<branch>-<sha>` - Specific commit (e.g., `main-abc1234`)
- `v1.0.0` - Release version (when creating GitHub releases)

### Pulling the Image

Once the workflow runs, you can pull the image:

```bash
# Pull latest version
docker pull ghcr.io/<your-username>/patient-scheduling:latest

# Pull specific branch
docker pull ghcr.io/<your-username>/patient-scheduling:auto-scheduling

# Pull specific commit
docker pull ghcr.io/<your-username>/patient-scheduling:main-abc1234
```

Replace `<your-username>` with your GitHub username or organization.

### Running the Image

```bash
# Run the pulled image
docker run -p 8080:8080 ghcr.io/<your-username>/patient-scheduling:latest

# Or use docker-compose with the registry image
# Update docker-compose.yml:
# services:
#   app:
#     image: ghcr.io/<your-username>/patient-scheduling:latest
#     ports:
#       - "8080:8080"
```

### Making the Image Public

By default, GitHub Container Registry images are private. To make them public:

1. Go to your GitHub repository
2. Click on **Packages** (in the right sidebar)
3. Click on the **patient-scheduling** package
4. Click **Package settings**
5. Scroll down to **Danger Zone**
6. Click **Change visibility** → **Public**

### Required Secrets

The workflow uses `GITHUB_TOKEN` which is automatically provided by GitHub Actions. No additional secrets are needed.

### Workflow File

The workflow is defined in [`.github/workflows/docker-build.yml`](.github/workflows/docker-build.yml).

### Build Cache

The workflow uses Docker BuildKit caching to speed up builds:
- Layer cache is stored in the registry
- Subsequent builds reuse unchanged layers
- Significantly faster rebuild times

### Monitoring Builds

View build status:
1. Go to your repository on GitHub
2. Click the **Actions** tab
3. See all workflow runs and their status

### Troubleshooting

**Build fails:**
- Check the Actions logs for detailed error messages
- Ensure Dockerfile builds successfully locally: `docker build -t test .`

**Can't pull image:**
- Verify the image is public (see "Making the Image Public" above)
- Check you're using the correct registry URL and tag
- Ensure you're logged in: `echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin`

**Permission denied:**
- The workflow needs `packages: write` permission (already configured)
- If running in an organization, verify organization settings allow package creation
