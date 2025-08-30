# Initial Setup Guide

This guide helps you prepare for and execute your first run of the YouTube Archiver, which will likely process a significant backlog of videos.

## Understanding the Initial Backlog

### What to Expect

When you first deploy the YouTube Archiver, you'll likely encounter:

- **50-200+ videos per channel** that need visibility changes
- **Processing time**: 5-15 minutes for all channels (depending on backlog size)
- **API usage**: Higher than normal due to the volume of videos to process

### Why This Happens

Most wards haven't been consistently changing video visibility after the 24-hour window, so there's typically a backlog of:
- Old sacrament meeting recordings still set to "public"
- Videos from several months or even years ago
- Multiple videos per week that should have been changed to "unlisted"

## Pre-Flight Checklist

### 1. Configuration Review

Before processing the backlog, review your configuration:

```yaml
# Increase limits for initial backlog processing
processing:
  max_videos_per_channel: 200  # Temporarily increase from default 50
  dry_run: true  # Start with dry-run mode
  
# Consider processing one channel at a time initially
channels:
  - name: "1st Ward"
    channel_id: "UC_EXAMPLE_CHANNEL_ID_1"
    enabled: true  # Enable only one channel initially
  - name: "2nd Ward"
    channel_id: "UC_EXAMPLE_CHANNEL_ID_2"
    enabled: false  # Disable others for initial testing
```

### 2. YouTube API Quotas

The YouTube Data API has daily quotas. For initial backlog processing:

- **Default quota**: 10,000 units per day
- **Typical usage**: ~3-5 units per video processed
- **Backlog capacity**: ~2,000-3,000 videos per day (well above typical needs)

If you have 7 channels with 100+ videos each, you may need to:
- Process channels in batches over multiple days, or
- Request a quota increase from Google (usually approved quickly)

## Step-by-Step Initial Setup

### Step 1: Dry Run Assessment

First, see what you're dealing with:

```bash
# Check all channels in dry-run mode
youtube-archiver --config config/config.yml --dry-run

# Or check one channel at a time
youtube-archiver --config config/config.yml --channels UC_CHANNEL_ID_1 --dry-run
```

**Expected output:**
```
📊 Processing Summary:
├── 1st Ward: 127 videos found, 89 eligible for processing
├── 2nd Ward: 156 videos found, 134 eligible for processing
├── 3rd Ward: 98 videos found, 67 eligible for processing
└── Total: 381 videos found, 290 eligible for processing

⚠️  DRY RUN MODE: No changes were made
```

### Step 2: Gradual Processing

For large backlogs, consider processing gradually:

#### Option A: One Channel at a Time
```bash
# Process first channel
youtube-archiver --config config/config.yml --channels UC_CHANNEL_ID_1

# Wait and verify, then continue
youtube-archiver --config config/config.yml --channels UC_CHANNEL_ID_2
```

#### Option B: Batch Processing with Limits
```bash
# Process with conservative limits
youtube-archiver --config config/config.yml --max-videos 100
```

### Step 3: Monitor and Verify

After processing:

1. **Check a few channels manually** to verify videos were changed correctly
2. **Review the processing logs** for any errors or rate limiting
3. **Confirm API quota usage** in Google Cloud Console

## Common Initial Setup Issues

### Issue: Too Many Videos to Process

**Symptoms:**
- Dry run shows 500+ videos per channel
- API quota warnings

**Solutions:**
```yaml
# Temporarily reduce scope
processing:
  max_videos_per_channel: 100  # Process in smaller batches
  age_threshold_hours: 168     # Only process videos older than 1 week initially
```

### Issue: Rate Limiting

**Symptoms:**
- "Rate limit exceeded" errors
- Processing stops partway through

**Solutions:**
```yaml
# Increase retry delays
retry_settings:
  max_attempts: 5
  backoff_factor: 3.0  # Slower backoff
  max_delay: 600       # Wait up to 10 minutes
```

### Issue: Mixed Content Types

**Symptoms:**
- Non-sacrament meeting videos being processed
- Unexpected videos in the eligible list

**Solutions:**
- Review the video titles in dry-run output
- Consider adding title filtering (future feature)
- Process channels individually to verify content

## Post-Initial Setup

### Ongoing Maintenance

After the initial backlog is cleared:

```yaml
# Return to normal settings
processing:
  max_videos_per_channel: 50   # Back to default
  age_threshold_hours: 24      # Standard 24-hour window
  dry_run: false              # Normal operation
```

### Expected Weekly Volume

After initial setup, expect:
- **1-3 videos per channel per week**
- **Processing time**: 30 seconds to 2 minutes
- **API usage**: Minimal (10-50 units per week)

### Monitoring

Set up regular monitoring to ensure:
- Weekly runs complete successfully
- No videos are missed due to configuration issues
- API quotas remain sufficient

## Troubleshooting

### High API Usage

If you're approaching quota limits:

1. **Reduce max_videos_per_channel** temporarily
2. **Process fewer channels per run**
3. **Request quota increase** from Google Cloud Console
4. **Spread processing across multiple days**

### Authentication Issues

If you encounter auth errors during large batch processing:
1. **Refresh OAuth tokens** may be needed for long-running operations
2. **Service account credentials** might be more reliable for automated runs
3. **Check token expiration** in Google Cloud Console

### Performance Optimization

For large backlogs:
1. **Run during off-peak hours** to avoid rate limiting
2. **Use batch API calls** where possible (implemented in the tool)
3. **Monitor processing speed** and adjust retry settings

## Success Metrics

Your initial setup is successful when:

- ✅ All eligible videos have been processed without errors
- ✅ Manual spot-checks confirm correct visibility changes
- ✅ API usage is within acceptable limits
- ✅ Processing logs show no critical errors
- ✅ Subsequent runs find only 1-3 new videos per channel

## Getting Help

If you encounter issues during initial setup:

1. **Check the logs** for specific error messages
2. **Run with increased verbosity**: `--log-level DEBUG`
3. **Test with a single channel** first
4. **Review API quotas** in Google Cloud Console
5. **Open an issue** on GitHub with logs and configuration (redacted)
