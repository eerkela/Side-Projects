import praw
import os
import urllib
from dotenv import load_dotenv
from pydrive.auth import GoogleAuth
from pydrive.auth import ServiceAccountCredentials
from pydrive.drive import GoogleDrive


# Create Drive Object:
gauth = GoogleAuth()
gauth.LoadCredentialsFile('drive_credentials.json')
if gauth.credentials is None:
    gauth.LocalWebserverAuth()
elif gauth.access_token_expired:
    gauth.Refresh()
else:
    gauth.Authorize()
gauth.SaveCredentialsFile('drive_credentials.json')
drive = GoogleDrive(gauth)

# Create Reddit user agent:
load_dotenv()
reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
reddit_user_agent = 'DnDBehindTheScreen Offline Backup Util 0.1.0 by /u/Arkaden42'
r = praw.Reddit(client_id=reddit_client_id,
                client_secret=reddit_client_secret,
                user_agent=reddit_user_agent)

def format_title(title):
    character_map = {
        '\\' : '-',
        '/' : '-',
        ':' : '-',
        '*' : '',
        '?' : '.',
        '"' : '\'',
        '<' : '(',
        '>' : ')',
        '|' : '.'
    }
    for (k, v) in character_map.items():
        title = title.replace(k, v)
    return title


def list_contents(parent):
    '''In: id of parent folder (str, ex: 19FkClYOyHTFeLCwatnPlEtcMo8SXENT0)
       Out: dict(str : str) mapping the names and ids of each of the parent
            folder's respective children.'''
    query = "'%s' in parents and trashed=false" % parent
    list = drive.ListFile({'q': query}).GetList()
    name_id_map = {}
    for f in list:
        name_id_map[f['title']] = f['id']
    return name_id_map

def process_img(post, drive_id, score_threshold=300):
    title = format_title(post.title)
    if len(title) > 250:
        title = title[:250]
    score = post.score
    link = post.url
    extension = link.split('.')[-1]
    exts = ['jpg', 'jpeg', 'png', 'gif', 'tiff']
    if (score > score_threshold and extension in exts):
        filename = '.'.join([title, extension])
        if (title not in list_contents(drive_id).keys()):
            try:
                urllib.request.urlretrieve(link, filename)
                file_properties = {
                    'title' : filename,
                    'mimeType' : 'image/' + extension,
                    'parents' : [{'kind': 'drive#fileLink', 'id': drive_id}]
                }
                drive_file = drive.CreateFile(file_properties)
                drive_file.SetContentFile(filename)
                drive_file.Upload()
                os.remove(filename)
                return True
            except urllib.error.HTTPError:
                print('failed to grab image: ' + link)
    return False

if __name__ == '__main__':
    # Directory to save subreddit contents to:
    drive_parent = '18uzYwHt35emCyku9J4_MuOUDNOs1Kl57'
    sub_name = 'battlemaps'

    # Stop script when <limit> consecutive redundancies are encountered:
    redundancies = 0
    limit = -1
    for submission in r.subreddit(sub_name).top('week', limit=None):
        if not process_img(submission, drive_parent):
            redundancies += 1
            if (redundancies == limit):
                print('Redundancy limit (%s) reached, stopping script.' % limit)
                break
        else:
            redundancies = 0
