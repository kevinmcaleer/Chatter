# Raspberry Pi 5 Deployment Guide

This guide covers deploying Chatter on a Raspberry Pi 5 (ARM64 architecture).

## Prerequisites

### Hardware
- Raspberry Pi 5 (4GB or 8GB RAM recommended)
- 32GB+ SD card (64GB recommended for production)
- Stable power supply (official Raspberry Pi 5 power supply recommended)
- Network connection (Ethernet preferred for stability)

### Software
- Raspberry Pi OS 64-bit (Bookworm or later)
- Docker 20.10+
- docker-compose 1.29+

## Quick Setup

### 1. Install Docker on Raspberry Pi

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Install docker-compose
sudo apt-get install -y docker-compose

# Verify installation
docker --version
docker-compose --version

# Reboot to apply group changes
sudo reboot
```

### 2. Deploy Chatter

```bash
# Clone or copy the Chatter directory to your Pi
# If using git:
git clone https://github.com/kevinmcaleer/chatter.git
cd chatter

# Configure environment
cp .env.docker .env
nano .env  # Set your SECRET_KEY and database credentials

# Build for ARM64 (will use correct architecture automatically)
docker build -t chatter:latest .

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f app
```

### 3. Verify Deployment

```bash
# Check health
curl http://localhost:8000/health

# Check API docs
# Open in browser: http://your-pi-ip:8000/docs
```

## Architecture Compatibility

The Chatter Docker image is **multi-architecture compatible**:

- ✅ **ARM64** (Raspberry Pi 5, 4, 3)
- ✅ **AMD64** (x86_64, regular PCs/servers)
- ✅ **ARM/v7** (Raspberry Pi 2, older models)

The base image `python:3.13-slim` automatically selects the correct architecture when built on the Pi.

## Performance Considerations

### Raspberry Pi 5 Specifications
- CPU: 4-core ARM Cortex-A76 @ 2.4GHz
- RAM: 4GB or 8GB LPDDR4X
- Storage: MicroSD or NVMe (via HAT)

### Recommended Settings

**For 4GB Pi:**
```yaml
# In docker-compose.yml, limit resources:
services:
  app:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  postgres:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

**For 8GB Pi:**
- Default settings work fine
- Can handle more concurrent users
- Better for production use

### Storage Performance

**MicroSD Card:**
- Works but slower
- Use Class 10 or UHS-I for better performance
- Enable log rotation to prevent SD card wear

**NVMe SSD (Recommended for production):**
- Much faster than SD card
- Better for database performance
- More reliable for production

```bash
# If using NVMe, mount at /opt/chatter
sudo mkdir -p /opt/chatter
# Mount your NVMe drive here
# Then deploy from /opt/chatter instead of home directory
```

## Using External Database

Since Raspberry Pi has limited resources, you might want to use an external PostgreSQL server:

```bash
# In .env, set:
DB_HOST=your_database_host
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password

# In docker-compose.yml, comment out the postgres service
```

This saves ~512MB RAM on the Pi.

## Building Multi-Architecture Images

### Option 1: Build on Raspberry Pi (Recommended)
```bash
# Build natively on the Pi
docker build -t chatter:latest .

# This automatically builds ARM64 image
```

### Option 2: Cross-Build from x86_64 Machine

```bash
# On your development machine (Mac/PC)

# Set up buildx
docker buildx create --name multiarch --use
docker buildx inspect --bootstrap

# Build for ARM64
docker buildx build \
  --platform linux/arm64 \
  -t chatter:latest-arm64 \
  --load \
  .

# Or build for multiple architectures
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t 192.168.2.1:5000/kevsrobots/chatter:latest \
  --push \
  .
```

## Raspberry Pi Optimizations

### 1. Reduce Logging (Prevent SD Card Wear)

```yaml
# In docker-compose.yml:
services:
  app:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 2. Use RAM for Temporary Files

```yaml
# In docker-compose.yml:
services:
  app:
    tmpfs:
      - /tmp
```

### 3. Enable Swap (If needed)

```bash
# Check current swap
free -h

# Increase swap if needed (for 4GB Pi)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set: CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### 4. Monitoring

```bash
# Install monitoring tools
sudo apt-get install -y htop iotop

# Monitor resources
htop

# Monitor disk I/O
sudo iotop

# Check Docker stats
docker stats
```

## Networking on Raspberry Pi

### Access from Local Network

```bash
# Find your Pi's IP
hostname -I

# Access from another device on same network
http://192.168.x.x:8000
```

### Port Forwarding (Optional)

If you want to access from outside your network:

```bash
# In your router, forward port 80/443 to Pi's port 8000
# Or use nginx reverse proxy with SSL
```

## Automatic Startup on Boot

```bash
# Enable Docker to start on boot
sudo systemctl enable docker

# Containers set with restart: unless-stopped will auto-start
# This is already configured in docker-compose.yml
```

## Troubleshooting on Raspberry Pi

### Container Won't Start

```bash
# Check system resources
free -h
df -h

# Check Docker logs
docker-compose logs app

# Check system logs
journalctl -u docker -n 50
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Reduce container memory limits
# Edit docker-compose.yml and reduce memory limits

# Or use external database to free up RAM
```

### Slow Performance

```bash
# Check if SD card is bottleneck
sudo iotop

# Consider upgrading to NVMe SSD

# Or use external database on a more powerful machine
```

### Database Connection Issues

```bash
# If using external PostgreSQL, check network
ping 192.168.2.3

# Check if port is open
telnet 192.168.2.3 5433

# Check Docker network
docker network inspect chatter_chatter-network
```

## Backup Strategy for Raspberry Pi

### Automated Backups

```bash
# Create backup script
cat > /home/pi/backup-chatter.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="/home/pi/backups"
mkdir -p $BACKUP_DIR

# Backup database
docker-compose exec -T postgres pg_dump -U chatter_user kevsrobots_cms \
  > $BACKUP_DIR/chatter-$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "chatter-*.sql" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/chatter-$DATE.sql"
EOF

chmod +x /home/pi/backup-chatter.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/pi/backup-chatter.sh") | crontab -
```

### SD Card Backup (Full System)

```bash
# From another computer, backup entire SD card
ssh pi@raspberrypi "sudo dd if=/dev/mmcblk0 bs=1M | gzip -" > pi-backup.img.gz

# Restore (be careful!)
gunzip -c pi-backup.img.gz | ssh pi@raspberrypi "sudo dd of=/dev/mmcblk0 bs=1M"
```

## Production Checklist for Raspberry Pi

- [ ] Use Raspberry Pi 5 with at least 4GB RAM
- [ ] Use NVMe SSD instead of SD card for production
- [ ] Configure external PostgreSQL for better performance
- [ ] Set up automated backups
- [ ] Enable Docker logging limits
- [ ] Monitor resource usage (RAM, CPU, disk)
- [ ] Use UPS or stable power supply
- [ ] Set up monitoring/alerting
- [ ] Configure firewall rules
- [ ] Enable automatic security updates

## Security Considerations

```bash
# Update regularly
sudo apt-get update
sudo apt-get upgrade -y

# Configure firewall
sudo apt-get install -y ufw
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # Chatter
sudo ufw enable

# Disable SSH password authentication (use keys only)
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart ssh
```

## Performance Benchmarks

Expected performance on Raspberry Pi 5:

| Metric | Value |
|--------|-------|
| Startup time | ~10-15 seconds |
| Request latency | <100ms |
| Concurrent users | 50-100 (4GB), 100-200 (8GB) |
| Database queries/sec | 500-1000 |

## Support

- **General Docker issues**: See `DOCKER_DEPLOYMENT.md`
- **Database issues**: See `TROUBLESHOOTING_DB.md`
- **ARM64 builds**: Use `docker buildx` for cross-compilation
- **Performance issues**: Monitor with `htop` and `docker stats`

## Example Production Deployment

Complete example for Raspberry Pi 5 with external database:

```bash
# 1. Install Docker (as shown above)

# 2. Clone repository
cd /opt
sudo git clone https://github.com/kevinmcaleer/chatter.git
sudo chown -R pi:pi chatter
cd chatter

# 3. Configure for external DB
cp .env.docker .env
nano .env
# Set:
# SECRET_KEY=<generated>
# DB_HOST=192.168.2.3
# DB_PORT=5433
# ENVIRONMENT=production
# ALLOWED_ORIGINS=https://kevsrobots.com

# 4. Update docker-compose.yml to remove postgres service
nano docker-compose.yml
# Comment out entire postgres section

# 5. Build and start
docker build -t chatter:latest .
docker-compose up -d

# 6. Verify
curl http://localhost:8000/health

# 7. Set up automated backups
./setup-backups.sh

# 8. Monitor
docker-compose logs -f app
```

That's it! Your Chatter application is now running on Raspberry Pi 5.
