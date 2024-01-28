from deemix.downloader import Downloader
from deemix import generateDownloadObject
from deemix.itemgen import GenerationError
from deemix.settings import load as load_deemix_settings

from deezer import Deezer as deemixDeezer

from plexapi.myplex import MyPlexAccount

import yaml

from pathlib import Path
import os
import time


def deezer_login():
    deezer = deemixDeezer()
    deezer.login_via_arl(downloadArl.strip())

    return deezer


def load_download_arl():
    if (deemix_folder / '.arl').is_file():
        with open(deemix_folder / '.arl', 'r', encoding="utf-8") as f:
            arl = f.readline().rstrip("\n").strip()
    else:
        raise Exception("No arl provided")
    with open(deemix_folder / '.arl', 'w', encoding="utf-8") as f:
        f.write(arl)

    return arl


# Deemix
deemix_folder = Path('./deemix')
settings = load_deemix_settings(deemix_folder)
downloadArl = load_download_arl()

# login to deezer download account
dz: deemixDeezer = deezer_login()


def download(links, bitrate):
    # generate download objects for URLs
    downloadObjects = []
    for link in links:
        try:
            # attempt to generate download object for the current URL
            downloadObject = generateDownloadObject(dz, link, bitrate)
        except GenerationError as e:
            # skip link if errors occurs
            print(f"{e.link}: {e.message}")
            continue
        # append single object to the downloadObjects list
        downloadObjects.append(downloadObject)

    # download objects
    for obj in downloadObjects:
        Downloader(dz, obj, settings).start()


def file_contains_string(folder_path, search_string):
    matching_files = []

    # Walk through all files and directories in the given folder and its subdirectories
    for root, dirs, files in os.walk(folder_path):
        # Check files in the current directory for the search string
        matching_files.extend([os.path.join(root, file) for file in files if search_string in file])

        # Check subdirectories for the search string in their names
        matching_files.extend([os.path.join(root, directory) for directory in dirs if search_string in dir])

    return matching_files


def download_deezer_playlists():
    download_count = 0
    for playlist_config in deezer_playlist_configs:
        playlist_id = playlist_config['id']

        for track in deezer_playlist_missing_tracks.get(playlist_id, []):
            # skip download if track has already been attempted before
            if downloaded_tracks.__contains__(track['id']):
                continue
            downloaded_tracks.append(track['id'])

            print(f"Downloading {track['title']} by {track['artist']['name']}...")

            # download track
            download([track['link']], playlist_config['bitrate'])
            download_count = download_count + 1

            print(f"Downloaded {track['title']} by {track['artist']['name']}")

    print(f"Downloaded {download_count} new tracks")


def fetch_deezer_playlists():
    print("Fetching playlists...")
    playlists = []
    for playlist_config in deezer_playlist_configs:
        # skip if set inactive by user
        if playlist_config['active'] == 0:
            continue

        # fetch playlist
        try:
            playlist = dz.api.get_playlist(playlist_config['id'])
            playlists.append(playlist)
        except Exception as e:
            print(f"Failed to fetch playlist {playlist_config['id']}: {e}")

    print(f"Fetched {len(playlists)} playlists")
    return playlists


def deezer_plex_sync():
    print("Logging in to Plex...")
    account = MyPlexAccount(token=config['plex_token'])
    print(f"Connecting to server {config['plex_server']}...")
    plex_server = account.resource(config['plex_server']).connect()
    print("Connected to Plex")

    missing_by_playlist = {}

    for deezer_playlist in deezer_playlists:
        print(f"Syncing Deezer playlist '{deezer_playlist['title']}' to Plex...")

        # check if Plex playlist already exists
        plex_playlist = None
        plex_playlist_titles = None
        for playlist in plex_server.playlists():
            if deezer_playlist['title'] == playlist.title:
                plex_playlist = playlist
                plex_playlist_titles = {item.title for item in plex_playlist.items()}
                break

        missing_by_playlist[deezer_playlist['id']] = deezer_playlist['tracks']['data']
        found_plex_tracks = []

        for track in plex_server.library.section(config['plex_library']).all(libtype='track'):
            matching_tracks = [
                t for t in missing_by_playlist[deezer_playlist['id']]
                if (t['title'].lower() == track.title.lower() or
                    t['title'].lower().replace('?', '_').replace('/', '_') == track.title.lower()) and
                   (t['artist']['name'].lower() in track.artist().title.replace('’', '\'').lower() or
                    t['artist']['name'].lower() in str(track.originalTitle).replace('’', '\'').lower())
            ]
            if matching_tracks:
                matching_track = matching_tracks[0]
                # remove the matching track from missing_tracks
                missing_by_playlist[deezer_playlist['id']].remove(matching_track)
                if not plex_playlist_titles or track.title not in plex_playlist_titles:
                    # append the matching track to found_plex_tracks
                    found_plex_tracks.append(track)
            # for matching_track in matching_tracks:
            # print(f"Matching track title: {matching_track['title']}")
            # print(f"Matching track artist: {matching_track['artist']['name']}/{track.artist().title}")

        # add missing tracks to the end of the playlist
        if len(found_plex_tracks) > 0:
            if plex_playlist:
                plex_playlist.addItems(found_plex_tracks)
            else:
                # if the playlist does not exist, create it
                plex_playlist = plex_server.createPlaylist(deezer_playlist['title'], items=found_plex_tracks)
                print(f"Created Plex playlist: {deezer_playlist['title']}")

        # update playlist cover
        plex_playlist.uploadPoster(deezer_playlist['picture_xl'])
        # update description
        if deezer_playlist['description']:
            plex_playlist.editSummary(deezer_playlist['description'])

        print(
            f"Finished syncing '{deezer_playlist['title']}' playlist, added: {len(found_plex_tracks)} items. "
            f"Missing tracks ({len(missing_by_playlist[deezer_playlist['id']])}):")
        for track in missing_by_playlist[deezer_playlist['id']]:
            print(f"Title: {track['title']}, artist: {track['artist']['name']}")

    print("Synced Deezer playlists to Plex")
    return missing_by_playlist


# Load Deezync configuration from the YAML file
with open('config.yaml', 'r') as deezync_config:
    config = yaml.safe_load(deezync_config)
deezer_playlist_configs = config['deezer_playlists']

# check music path
music_path = "/music"
if not os.path.exists(music_path):
    raise FileNotFoundError(f"The specified music path '{music_path}' does not exist.")

downloaded_tracks = []

# fetch playlists to sync
deezer_playlists = fetch_deezer_playlists()
# sync playlists to plex and find missing tracks
deezer_playlist_missing_tracks = deezer_plex_sync()
# download missing tracks
download_deezer_playlists()

# resync playlists after 10 minutes, give Plex time to index new files
seconds = 600
print(f"Waiting {seconds} seconds until playlist sync...")
time.sleep(seconds)
deezer_plex_sync()

print("Finished script run")
