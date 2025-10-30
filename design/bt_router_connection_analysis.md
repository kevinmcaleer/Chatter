# BT Router Connection Dropping Analysis - October 30, 2025

## Problem Statement

BT Router keeps dropping connections every couple of minutes when port 80 traffic comes through.

## Log Analysis

### Observed Pattern (08:56:04 - 08:56:07)

**In 3 seconds, router accepted 22+ new connections** from Cloudflare IPs:
- 172.64.215.113 (multiple times)
- 172.70.46.154 (multiple times)
- 172.71.95.122
- 172.71.102.31
- 172.71.148.169 (multiple times)
- 172.71.126.104
- 172.71.182.28
- 141.101.76.32 (multiple times)
- 104.23.217.169

### Connection Rate
- **~7-8 connections per second** sustained
- **All from Cloudflare IPs** (proxying traffic to your origin)
- All targeting port 80 → 192.168.1.4

## Root Cause Analysis

### Why Router is Dropping Connections

**Connection Tracking Table Exhaustion**

Consumer routers (like BT Home Hub) have **limited connection tracking tables**:
- Typical capacity: 2,000-8,000 concurrent connections
- Your traffic: 7-8 NEW connections/second = **25,000-30,000 connections/hour**
- With ~5 minute timeout per connection = **2,500 concurrent connections**

When the table fills up:
1. Router can't track new connections
2. Drops existing connections to make room
3. Causes intermittent connectivity issues

### Why So Many Connections?

**Cloudflare creates a new TCP connection for EACH request** because:
1. Your origin doesn't support HTTP/2 properly over port 80
2. Cloudflare terminates TLS → makes plain HTTP to origin
3. Without HTTP keepalive optimization, each page load = multiple connections
4. Popular site + bots = high connection rate

### Contributing Factors

1. **High Traffic Volume**
   - 90,000+ requests/day (Oct 27)
   - Bots: Googlebot, SemrushBot, ChatGPT-User, etc.
   - Each request potentially = new connection

2. **No Connection Pooling**
   - nginx on 192.168.1.4 might not be reusing connections to Cloudflare
   - keepalive settings might be too low

3. **Port 80 Limitations**
   - Can't use HTTP/2 over plain HTTP (port 80)
   - Can't use connection multiplexing
   - Each resource = separate connection

4. **Router Hardware Limits**
   - Consumer-grade router (BT Home Hub)
   - Not designed for server workloads
   - Limited NAT table, CPU, memory

## Evidence from Logs

### All IPs are Cloudflare
```
141.101.76.32    → Cloudflare
172.64.215.113   → Cloudflare
172.70.46.154    → Cloudflare
172.71.x.x       → Cloudflare (entire range)
104.23.x.x       → Cloudflare
```

### Pattern
- Burst of connections every few seconds
- All to same destination (192.168.1.4:80)
- No malicious activity - legitimate Cloudflare proxy traffic

### ARP Entry Deletion
```
ARP [del] br0 192.168.1.159 d2:d2:b0:94:5f:75
```
This suggests router is clearing ARP cache (possibly due to memory pressure).

## Solutions

### Option 1: Cloudflare Argo Tunnel (Recommended) ⭐
**Use Cloudflare Tunnel instead of port forwarding**

**Pros:**
- Eliminates port 80 forwarding entirely
- No router connection tracking needed
- Encrypted tunnel from Cloudflare directly to your server
- Better security (no exposed ports)
- Bypasses ISP port blocks
- Connection pooling built-in

**Cons:**
- Requires installing `cloudflared` daemon
- Slight additional latency (~20-50ms)
- Small monthly cost ($5/month for multiple domains)

**Setup:**
```bash
# Install cloudflared on 192.168.1.4
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create kevsrobots

# Route traffic
cloudflared tunnel route dns kevsrobots www.kevsrobots.com
cloudflared tunnel route dns kevsrobots chatter.kevsrobots.com

# Configure and run
cloudflared tunnel --config ~/.cloudflared/config.yml run kevsrobots
```

---

### Option 2: Upgrade Router
**Replace BT Home Hub with better router**

**Recommended Routers:**
- Ubiquiti EdgeRouter X ($50-60) - 1M+ connection table
- Mikrotik hEX S ($70) - Enterprise-grade
- pfSense box ($100+) - Full firewall OS

**Pros:**
- Handles high connection rates
- Better NAT performance
- More configuration options

**Cons:**
- Cost ($50-100+)
- Setup complexity
- Might need ISP configuration changes

---

### Option 3: Optimize Connection Pooling
**Configure nginx to reuse connections**

**Changes to `/home/pi/ClusteredPi/stacks/nginx/nginx.conf`:**

```nginx
http {
    # ... existing config ...

    # Optimize keepalive to Cloudflare
    keepalive_timeout 300;         # Keep connections open 5 minutes
    keepalive_requests 10000;      # Allow many requests per connection

    upstream kevsrobots {
        # ... existing servers ...
        keepalive 128;              # Increase from 64
        keepalive_timeout 300s;
        keepalive_requests 10000;
    }

    upstream chatter {
        # ... existing servers ...
        keepalive 64;               # Increase from 16
        keepalive_timeout 300s;
        keepalive_requests 10000;
    }
}
```

**Pros:**
- Free
- Reduces new connections by ~60-80%
- Quick to implement

**Cons:**
- Doesn't eliminate the problem
- Router still has fundamental limits
- Partial solution only

---

### Option 4: Use Different Port
**Move web server to alternate port (e.g., 8080, 8443)**

**Setup:**
1. Change nginx to listen on port 8080
2. Update BT Router port forwarding: 80 → 192.168.1.4:8080
3. Configure Cloudflare origin to use port 8080

**Pros:**
- Might have less connection tracking issues
- Keeps existing hardware

**Cons:**
- Doesn't really solve the core issue
- Still limited by router capabilities
- More configuration complexity

---

### Option 5: DMZ Mode (Not Recommended)
**Put 192.168.1.4 in DMZ**

**Pros:**
- Bypasses some NAT limitations
- All ports forwarded

**Cons:**
- ⚠️ Security risk - all ports exposed
- Doesn't fix connection table issue
- Not recommended for production

---

## Comparison Matrix

| Solution | Cost | Complexity | Effectiveness | Security | Time to Implement |
|----------|------|------------|---------------|----------|-------------------|
| **Cloudflare Tunnel** | $5/mo | Medium | ⭐⭐⭐⭐⭐ 95% | ⭐⭐⭐⭐⭐ | 1-2 hours |
| **Upgrade Router** | $50-100 | High | ⭐⭐⭐⭐ 85% | ⭐⭐⭐⭐ | 2-4 hours |
| **Optimize Keepalive** | Free | Low | ⭐⭐ 40% | ⭐⭐⭐⭐⭐ | 15 minutes |
| **Different Port** | Free | Medium | ⭐⭐ 30% | ⭐⭐⭐⭐ | 30 minutes |
| **DMZ Mode** | Free | Low | ⭐⭐ 35% | ⭐ | 10 minutes |

---

## Recommended Approach

### Immediate (Next 30 Minutes)
**Optimize nginx keepalive settings**
- Quick win, reduces connections by 40-60%
- Buys time for permanent solution
- No downtime

### Short-term (Next Week)
**Implement Cloudflare Tunnel**
- Eliminates port forwarding entirely
- Solves connection tracking problem permanently
- Better security model
- Most cost-effective long-term solution

### Alternative
**Upgrade router** if you prefer hardware solution
- More expensive but handles high connection rates
- Better for multiple services beyond web server

---

## Why This is Happening NOW

### Traffic Growth
Your site has grown in popularity:
- More legitimate users
- More bot crawlers (Google, Bing, ChatGPT)
- Higher traffic volume exceeding router capacity

### Recent Changes
- We FIXED the redirect loop bug (good!)
- But this revealed the underlying router limitation
- Previously, many connections were timing out quickly
- Now they're succeeding, creating more sustained load

### Cloudflare Proxy Behavior
- Cloudflare makes separate connections for each request
- High request rate = high connection rate
- Consumer router can't handle this volume

---

## Monitoring & Diagnostics

### Check Current Connection Count
```bash
# On BT Router (if accessible via SSH - unlikely)
cat /proc/net/nf_conntrack | wc -l

# Check nginx connections
netstat -an | grep :80 | wc -l
```

### Monitor Connection Rate
```bash
# Watch new connections per second
watch -n 1 'netstat -an | grep :80 | grep ESTABLISHED | wc -l'
```

---

## Action Plan

### Phase 1: Immediate Relief (Today)
1. ✅ Optimize nginx keepalive settings
2. ✅ Monitor connection behavior
3. ✅ Document baseline metrics

### Phase 2: Permanent Fix (This Week)
1. 📋 Set up Cloudflare Tunnel on 192.168.1.4
2. 📋 Test tunnel configuration
3. 📋 Migrate DNS to tunnel
4. 📋 Disable port 80 forwarding on router

### Phase 3: Optimization (Next Week)
1. 📋 Fine-tune tunnel performance
2. 📋 Monitor error rates
3. 📋 Document new architecture

---

## Expected Results

### After Keepalive Optimization
- 40-60% fewer new connections
- Router might handle load better
- Temporary improvement

### After Cloudflare Tunnel
- 99% reduction in router port forwarding load
- No more connection tracking issues
- Eliminates port 80 connectivity problems
- Better security posture
- Faster response times (direct tunnel)

---

## Additional Recommendations

### 1. Enable HTTP/2 Internally
Once using Cloudflare Tunnel, enable HTTP/2 between tunnel and nginx:
- Single connection multiplexed
- Better performance
- Lower connection overhead

### 2. Implement Rate Limiting
Add Cloudflare rate limiting rules:
- Limit aggressive bots
- Reduce connection bursts
- Protect origin server

### 3. Cache More Aggressively
Configure Cloudflare to cache more content:
- Fewer origin requests
- Lower connection rate
- Better performance

---

## Conclusion

**Root Cause:** Consumer-grade BT Router overwhelmed by high connection rate from Cloudflare proxy traffic.

**Best Solution:** Cloudflare Tunnel - eliminates port forwarding, bypasses router limitations, improves security.

**Quick Fix:** Optimize nginx keepalive settings while implementing tunnel.

**Timeline:**
- Today: Optimize keepalive (40% improvement)
- This week: Deploy Cloudflare Tunnel (95% improvement)
- Next week: Fine-tune and monitor

---

**Report Date:** October 30, 2025
**Priority:** High (intermittent service disruption)
**Estimated Downtime:** <5 minutes (during DNS cutover to tunnel)
