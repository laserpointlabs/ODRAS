# WSL Internet Connectivity Fix

## Problem
WSL cannot access the internet - DNS resolution fails, `apt update` fails, `curl`/`wget` don't work.

## Solution
**Primary Fix**: Enable `networkingMode=mirrored` in Windows `.wslconfig` file. This is the main solution that fixes internet connectivity.

**Supporting Configuration**: Also configure DNS settings in WSL to prevent DNS issues.

## Steps

### 1. Enable Mirrored Networking Mode (Windows) ⭐ PRIMARY FIX

**This is the main fix** - enable mirrored networking mode in the Windows `.wslconfig` file:

**Location**: `C:\Users\<YourUsername>\.wslconfig`

**From Windows PowerShell**:
```powershell
notepad $env:USERPROFILE\.wslconfig
```

**Or from WSL**:
```bash
nano /mnt/c/Users/$USER/.wslconfig
```

Add or update with this content:

```ini
[wsl2]
networkingMode=mirrored
```

**What this does**: Enables mirrored networking mode, which fixes DNS and network connectivity issues by using the same network stack as Windows. **This is the key fix that resolves internet connectivity problems.**

### 2. Disable Auto-Generated DNS Configuration (WSL)

Edit `/etc/wsl.conf` in WSL:

```bash
sudo nano /etc/wsl.conf
```

Add this content:

```ini
[network]
generateResolvConf = false
```

**What this does**: Prevents WSL from automatically overwriting your DNS configuration.

### 3. Set Static DNS Server (WSL)

Edit `/etc/resolv.conf` in WSL:

```bash
sudo nano /etc/resolv.conf
```

Add this content:

```
nameserver 8.8.8.8
```

**What this does**: Uses Google's public DNS server (8.8.8.8) instead of Windows DNS.

**Alternative DNS servers** (if 8.8.8.8 doesn't work):
- Cloudflare: `1.1.1.1`
- Quad9: `9.9.9.9`
- OpenDNS: `208.67.222.222`

### 4. Restart WSL

From PowerShell (Windows):

```powershell
wsl --shutdown
```

Then reopen WSL.

### 5. Verify Fix

```bash
# Test DNS resolution
ping -c 3 google.com

# Test internet access
curl -I https://www.google.com

# Test package manager
sudo apt update
```

## Your Current Configuration

**Windows `.wslconfig`** (`C:\Users\<YourUsername>\.wslconfig`):
```ini
[wsl2]
networkingMode=mirrored
memory=16384MB
processors=16
```

**WSL `/etc/wsl.conf`**:
```ini
[network]
generateResolvConf = false
```

**WSL `/etc/resolv.conf`**:
```
nameserver 8.8.8.8
```

## Quick Reference

If you need to reapply this fix:

**Windows side** (create/edit `C:\Users\<YourUsername>\.wslconfig`):
```ini
[wsl2]
networkingMode=mirrored
```

**WSL side**:
```bash
# 1. Disable auto DNS generation
echo -e "[network]\ngenerateResolvConf = false" | sudo tee /etc/wsl.conf

# 2. Set static DNS
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf

# 3. Restart WSL from PowerShell
# wsl --shutdown
```

## Troubleshooting

### Still not working?

1. **Check if files exist**:
   ```bash
   cat /etc/wsl.conf
   cat /etc/resolv.conf
   ```

2. **Check if resolv.conf is immutable**:
   ```bash
   lsattr /etc/resolv.conf
   # Should show 'i' flag if immutable
   ```

3. **Try different DNS server**:
   ```bash
   sudo chattr -i /etc/resolv.conf  # Remove immutable flag
   echo "nameserver 1.1.1.1" | sudo tee /etc/resolv.conf
   sudo chattr +i /etc/resolv.conf
   wsl --shutdown  # Restart from PowerShell
   ```

4. **Check Windows DNS** (from PowerShell):
   ```powershell
   ipconfig /all
   # Look for DNS servers, try using Windows DNS IP in resolv.conf
   ```

## Why This Works

- **`networkingMode=mirrored`** ⭐ **PRIMARY FIX**: Uses the same network stack as Windows, fixing DNS and connectivity issues. This is the main solution.
- **`generateResolvConf = false`**: Prevents WSL from overwriting your DNS configuration
- **Static DNS**: Provides reliable DNS resolution when Windows DNS has issues
- Mirrored mode is especially helpful on corporate networks and VPNs

**Note**: The `networkingMode=mirrored` setting is the critical fix. The DNS configuration steps are supporting measures that help ensure reliable connectivity.
