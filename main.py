from deemix.downloader import Downloader
from deemix import generateDownloadObject
from deemix.itemgen import GenerationError
from deemix.settings import load as load_deemix_settings

from deezer import Deezer as deemixDeezer

from plexapi.myplex import MyPlexAccount

import yaml

from pathlib import Path
import os
import shutil
import time

import logging

# Configure the logging format
logging.basicConfig(
    format='[%(levelname)s] %(asctime)s: %(message)s',
    datefmt='%H:%M:%S',
    level=logging.INFO)
logger = logging.getLogger(__name__)


def deezer_login():
    deezer = deemixDeezer()
    deezer.login_via_arl(downloadArl.strip())

    if not deezer.current_user:
        logging.error("Couldn't log in to Deezer, check arl")
        quit()

    logging.info(f"Logged in to Deezer as {deezer.current_user['name']}")

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


def load_deezync_config():
    config_path = '/config/config.yaml'

    # copy template config if no config exists
    if not os.path.isfile(config_path):
        shutil.copy('config.yaml', config_path)  # Deezync config
        shutil.copy('deemix/config.json', '/config/deemix/config.json')  # Deemix config

        logging.info(f"Restored template deemix/config.yaml, please set up configs!")
        logging.info("Quit for user to set up configs")

        quit()

    logging.debug(f"Loading config from {config_path}")
    with open(config_path, 'r') as deezync_config:
        loaded_config = yaml.safe_load(deezync_config)

    logging.info("Loaded config")
    return loaded_config


# Deemix
deemix_folder = Path('/config/deemix')
settings = load_deemix_settings(deemix_folder)
downloadArl = load_download_arl()

# login to deezer download account
dz: deemixDeezer = deezer_login()
plex_server = None

downloaded_tracks = []
cached_deezer_playlists = {}
playlist_last_sync_time = {}


def connect_plex():
    global plex_server

    if not config['plex_token'] or not config['plex_token'] or not config['plex_token']:
        logging.error("Missing Plex credentials, won't sync")
        return

    if not plex_server:
        logging.debug("Logging in to Plex")
        account = MyPlexAccount(token=config['plex_token'])
        logging.info("Logged in to Plex")

        logging.debug(f"Connecting to server {config['plex_server']}")
        plex_server = account.resource(config['plex_server']).connect()

        logging.info(f"Connected to Plex server {config['plex_server']}")


def deezer_plex_sync(deezer_playlists):
    global plex_server

    # get all tracks + playlists in Plex library
    plex_playlists = plex_server.playlists()
    all_library_tracks = plex_server.library.section(config['plex_library']).all(libtype='track')

    missing_by_playlist = {}

    sync_playlist_counter = 1
    for deezer_playlist in deezer_playlists:
        for looped_config in deezer_playlist_configs:
            if looped_config['id'] == deezer_playlist['id']:
                playlist_config = looped_config
                break

        logging.info(f"Syncing {sync_playlist_counter}/{len(deezer_playlists)} Deezer playlist "
                     f"'{deezer_playlist['title']}' to Plex...")
        sync_playlist_counter += 1

        # check if Plex playlist already exists
        plex_playlist = None
        plex_playlist_tracks = None
        plex_playlist_unmatched_tracks = None

        for playlist in plex_playlists:
            if deezer_playlist['title'] == playlist.title:
                plex_playlist = playlist
                plex_playlist_tracks = plex_playlist.items()
                plex_playlist_unmatched_tracks = plex_playlist_tracks.copy()
                break

        missing_by_playlist[deezer_playlist['id']] = deezer_playlist['tracks']['data']
        found_plex_tracks = []

        # search track match in Plex library
        for track in all_library_tracks:
            matching_tracks = [
                t for t in missing_by_playlist[deezer_playlist['id']]
                if (t['title'].lower() == track.title.lower() or
                    t['title'].lower().replace('?', '_').replace('/', '_').replace('[', '(').replace(']', ')')
                    == track.title.lower()) and
                   (t['artist']['name'].lower() in track.artist().title.replace('’', '\'').lower() or
                    t['artist']['name'].lower() in str(track.originalTitle).replace('’', '\'').lower())
            ]

            # process matching track if found
            if matching_tracks:
                # use first match
                matching_track = matching_tracks[0]

                # remove matching track from missing_tracks
                missing_by_playlist[deezer_playlist['id']].remove(matching_track)

                # remove matching track from unmatched tracks in Plex playlist
                if (plex_playlist_unmatched_tracks and
                        any(playlist_track.title == track.title for playlist_track in plex_playlist_unmatched_tracks)):
                    plex_playlist_unmatched_tracks.remove(track)

                # add matching track to found_plex_tracks if not already in playlist
                if not plex_playlist_tracks or track.title not in plex_playlist_tracks:
                    found_plex_tracks.append(track)

            # for matching_track in matching_tracks:
            # logging.debug(f"Matching track title: {matching_track['title']}")
            # logging.debug(f"Matching track artist: {matching_track['artist']['name']}/{track.artist().title}")

        removed_counter = 0

        # add missing tracks to the end of the playlist
        if len(found_plex_tracks) > 0:
            if plex_playlist:
                plex_playlist.addItems(found_plex_tracks)
                if playlist_config['delete_unmatched_from_playlist'] == 1:
                    plex_playlist.removeItems(plex_playlist_unmatched_tracks)
                    removed_counter = len(plex_playlist_unmatched_tracks)
            else:
                # if the playlist does not exist, create it
                plex_playlist = plex_server.createPlaylist(deezer_playlist['title'], items=found_plex_tracks)
                logging.info(f"Created Plex playlist: {deezer_playlist['title']}")

            # update playlist cover
            if playlist_config['sync_cover_description'] == 1:
                plex_playlist.uploadPoster(deezer_playlist['picture_xl'])
                # update description
                if deezer_playlist['description']:
                    plex_playlist.editSummary(deezer_playlist['description'])

        # logging
        logging.info(
            f"Synced '{deezer_playlist['title']}' playlist. Added: {len(found_plex_tracks)}, removed: "
            f"{removed_counter}, missing: {len(missing_by_playlist[deezer_playlist['id']])}")
        for track in missing_by_playlist[deezer_playlist['id']]:
            logging.debug(f"Missing title: {track['title']}, artist: {track['artist']['name']}")

        # remove empty playlist from missing tracks if no tracks missing
        if len(missing_by_playlist[deezer_playlist['id']]) < 1:
            missing_by_playlist.pop(deezer_playlist['id'])

    logging.info("Synced Deezer playlists to Plex")
    return missing_by_playlist


def download(links, bitrate):
    # generate download objects for URLs
    downloadObjects = []
    for link in links:
        try:
            # attempt to generate download object for the current URL
            downloadObject = generateDownloadObject(dz, link, bitrate)
        except GenerationError as e:
            # skip link if errors occurs
            logging.error(f"{e.link}: {e.message}")
            continue
        # append single object to the downloadObjects list
        downloadObjects.append(downloadObject)

    # download objects
    for obj in downloadObjects:
        Downloader(dz, obj, settings).start()


def download_deezer_playlists(deezer_playlist_missing_tracks):
    download_count = 0
    for playlist_config in deezer_playlist_configs:
        playlist_id = playlist_config['id']

        for track in deezer_playlist_missing_tracks.get(playlist_id, []):
            # skip download if track has already been attempted before
            if downloaded_tracks.__contains__(track['id']):
                continue
            downloaded_tracks.append(track['id'])

            logging.info(f"Download {track['title']} by {track['artist']['name']}...")

            # download track
            download([track['link']], playlist_config['bitrate'])
            download_count = download_count + 1

            logging.info(f"Downloaded {track['title']} by {track['artist']['name']}")

    logging.info(f"Downloaded {download_count} new tracks")


def file_contains_string(folder_path, search_string):
    matching_files = []

    # Walk through all files and directories in the given folder and its subdirectories
    for root, dirs, files in os.walk(folder_path):
        # Check files in the current directory for the search string
        matching_files.extend([os.path.join(root, file) for file in files if search_string in file])

        # Check subdirectories for the search string in their names
        matching_files.extend([os.path.join(root, directory) for directory in dirs if search_string in dir])

    return matching_files


def loop():
    connect_plex()
    if not plex_server:
        logging.error("Can't sync because no Plex server provided")

    cycleCount = 1
    while True:
        logging.info(f"Starting sync cycle {cycleCount}")

        # check playlists for updates
        changed_deezer_playlists = update_playlists()
        logging.info(f"Detected {len(changed_deezer_playlists)} playlist changes on Deezer")

        # skip further sync if no changes detected
        if not changed_deezer_playlists:
            intervalSeconds = 20
            logging.info(f"No changes detected, sleeping for {intervalSeconds} seconds...")
            time.sleep(intervalSeconds)
            pass

        # sync playlists to Plex and find missing tracks
        deezer_playlist_missing_tracks = deezer_plex_sync(changed_deezer_playlists)

        if deezer_playlist_missing_tracks:
            # download missing tracks
            logging.info(f"Downloading missing tracks")
            download_deezer_playlists(deezer_playlist_missing_tracks)

            # give Plex time to index new files
            seconds = 60
            logging.info(f"Wait {seconds} seconds until syncing playlist with new downloads")
            time.sleep(seconds)

            # resync playlists with new files
            deezer_plex_sync(changed_deezer_playlists)

        logging.info(f"Finished sync cycle {cycleCount}")
        cycleCount = cycleCount + 1


def update_playlists():
    global cached_deezer_playlists
    global playlist_last_sync_time

    logging.info("Update playlist info from Deezer...")

    playlists = []
    update_count = 0
    for playlist_config in deezer_playlist_configs:
        # skip if set inactive by user
        if playlist_config['active'] == 0:
            continue

        # skip if sync interval not reached yet
        if playlist_last_sync_time.__contains__(playlist_config['id']):
            seconds_between = time.time() - playlist_last_sync_time[playlist_config['id']]
            if seconds_between < playlist_config['sync_interval_seconds']:
                continue

        # fetch playlist
        try:
            playlist = dz.api.get_playlist(playlist_config['id'])

            # detect changes to playlist using checksum
            if (not cached_deezer_playlists.__contains__(playlist_config['id']) or
                    cached_deezer_playlists[playlist_config['id']] != playlist['checksum']):

                # save changes and add to changed playlist queue
                playlists.append(playlist)
                cached_deezer_playlists[playlist_config['id']] = playlist['checksum']

            playlist_last_sync_time[playlist_config['id']] = time.time()
            update_count += 1
        except Exception as e:
            logging.info(f"Failed to fetch playlist {playlist_config['id']}: {e}")

    logging.info(f"Updated {update_count} playlists")
    return playlists


# load Deezync configuration from the YAML file
config = load_deezync_config()
deezer_playlist_configs = config['deezer_playlists']

# check music path
music_path = "/music"
if not os.path.exists(music_path):
    raise FileNotFoundError(f"The specified music path '{music_path}' does not exist.")

# quit if no playlists to sync
if len(deezer_playlist_configs) < 1:
    logging.info("No sync playlist configured, quitting...")
    quit()

loop()
