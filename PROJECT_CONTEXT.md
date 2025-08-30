# YouTube Archiver - Project Context

## Overview
An automated tool to manage YouTube live stream visibility for LDS ward sacrament meeting recordings across multiple ward channels.

## Background
- **Role**: Stake Tech Specialist managing 7 ward YouTube channels
- **Problem**: Ward tech specialists frequently forget to change visibility of sacrament meeting live streams after the 24-hour church policy window
- **Solution**: Automated tool to change live video visibility from public to unlisted on a scheduled basis

## Church Policy Compliance
- Live sacrament meeting recordings can remain public for 24 hours after broadcast
- After 24 hours, videos should have visibility changed (not necessarily deleted)
- Videos can remain as unlisted or private for ward members to access if needed

## Technical Approach
- **Primary**: Local Python script that can be run manually
- **Secondary**: GitHub Actions workflow for automated scheduling (Monday evenings)
- **API**: YouTube Data API v3 for video management
- **Authentication**: Google OAuth2 with appropriate channel management permissions

## Scope
- Support for multiple ward YouTube channels (initially 7, but scalable)
- Focus on live stream videos (primary content type for sacrament meetings)
- Change visibility from public to unlisted
- Optional: Basic reporting of actions taken
- Safety-first approach (no deletion, just visibility changes)
- **Reusable design**: Enable other stake/ward tech specialists to use the same tool

## Success Criteria
- Automated identification and processing of sacrament meeting live streams
- Reliable visibility changes without manual intervention
- Configurable scheduling (Monday evenings)
- Safe operation with minimal risk of unintended changes
