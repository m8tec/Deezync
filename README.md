
<p align="center">
   <img width="175" alt="deezync_350" src="https://github.com/user-attachments/assets/c3b2f24d-e277-4683-bc9c-9efa00d16681">
</p>
<h1 align="center">Deezync</h1>

<div align="center">
   
[![Static Badge](https://img.shields.io/badge/Join-Discord-blue?color=%237289da)](https://discord.gg/4cJczdyu9n)
[![Docker Pulls](https://img.shields.io/docker/pulls/m8tec/deezync)](https://hub.docker.com/repository/docker/m8tec/deezync)

Deezync syncs Deezer playlists to Plex and uses Deemix to download missing tracks.

</div>

## Installation
1. Bind container path `/music` to the location of your Plex music library
2. Bind container path `/config` to where you want to store the configs

## Setup
Deezync will create the needed config files at `/config` on its first run.
1. Paste your Plex credentials in.
   - Token: [Where is my Plex token?](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)
   - Server: The name of your Plex server
   - Library: The name of the Plex music library you want to sync
2. Add and configure monitored playlists
   - Id: Find the Deezer playlist id by opening it in a browser and inspect the end of the link
   - Bitrate: FLAC = 9, MP3_320 = 3, MP3_128 = 1
   - Delete unmatched from playlist: Delete tracks from Plex playlist if not matched with Deezer track
   - Active: Disable playlist for syncing. Active = 1, inactive = 0
   - Sync interval seconds: The interval in which Deezync should check for playlist changes
   - Make sure that your monitored playlists are not private!
5. Paste in your Deezer arl at `/config/Deemix/.arl`. [Where is my Deezer arl?](https://github.com/nathom/streamrip/wiki/Finding-Your-Deezer-ARL-Cookie)
6. Configure Plex to automatically detect new files. Tick the following settings:
   - Plex > Settings > Library > "Scan my library automatically"
   - Plex > Settings > Library > "Run a partial scan when changes are detected"
   - Plex > Settings > Library > "Include music libraries in automatic updates"
7. Configure Plex to prefer local metadata, so Deezync can find the downloaded tracks:
   - Plex > Your music library > Manage Library > Edit > Advanced > Agent > Personal Media Artists
   - Plex > Your music library > Manage Library > Edit > Advanced > Prefer local metadata

### Add to an existing library
By default Deemix will use the suggested file naming scheme and skip the download of missing tracks if their download path already exists. In order to prevent file duplicates, make sure to properly setup your naming conventions in the `/config/deemix/config.json` config.

## Contributing
I'll be happy to review pull requests
