import praw
import os
from dotenv import load_dotenv
from markdown2 import Markdown
from pydrive.auth import GoogleAuth
from pydrive.auth import ServiceAccountCredentials
from pydrive.drive import GoogleDrive


## TODO: Build dependency package to import into lambda
#  (don't need an efs system I don't think)
#  Dependencies: praw, pydrive, markdown2


'''
This script will iterate through the 'hot' posts of a given subreddit,
gathering the contents of each post and uploading them into a structured
Google Drive format, converting each post into an editable google doc.
'''

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

def convert_to_html(content_string):
    m = Markdown()
    content_string = m.convert(content_string)
    content_string = content_string.replace('</p>', '</p><br>')
    return content_string

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

def upload_doc(post, parent_id, score_threshold=300):
    '''In: post (reddit post obj), parent_id (str)
       Out: True if file is unique and is successfully uploaded
            False if file is redundant'''
    title = format_title(post.title)
    flair = post.link_flair_text.split('/')
    content = post.selftext
    score = post.score
    link = post.url
    author = '[deleted]' if post.author is None else post.author.name
    header = 'Original author: ' + author + '<br>' \
           + 'Permalink to original post: ' + link + '<br>' \
           + '<br><br>'

    content = convert_to_html(content)

    if (score > score_threshold):
        # Create parent folder for post based on flair
        id = parent_id
        for f in flair:
            parent_contents = list_contents(id)
            if (f and f not in parent_contents.keys()):
                print('Creating folder: ' + f)
                folder_metadata = {
                    'title' : f,
                    'parents' : [{'kind': 'drive#fileLink', 'id': id}],
                    'mimeType' : 'application/vnd.google-apps.folder'
                }
                folder = drive.CreateFile(folder_metadata)
                folder.Upload()
                id = folder['id']
            else:
                id = parent_contents[f]

        # Upload file to parent folder and convert to Google doc
        if title not in list_contents(id).keys():
            print('Creating file: ' + title)
            doc_metadata = {
                'title' : title,
                'parents' : [{'kind': 'drive#fileLink', 'id': id}],
                'mimeType' : 'text/html'
            }
            doc = drive.CreateFile(doc_metadata)
            doc.SetContentString(header + content)
            doc.Upload({'convert' : True})

            print('Done!')
            print()
            return True

    return False


if __name__ == '__main__':
    # Directory to save subreddit contents to:
    drive_parent = '19FkClYOyHTFeLCwatnPlEtcMo8SXENT0'
    sub_name = 'dndbehindthescreen'

    # Stop script when <limit> consecutive redundancies are encountered:
    redundancies = 0
    limit = -1
    for submission in r.subreddit(sub_name).top(limit=None):
        if not upload_doc(submission, drive_parent):
            redundancies += 1
            if (redundancies == limit):
                print('Redundancy limit (%s) reached, stopping script.' % limit)
                break
        else:
            redundancies = 0
