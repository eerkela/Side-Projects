import json
import os
import urllib

import cv2
import numpy as np
from dotenv import load_dotenv
from imutils import paths
from py3pin.Pinterest import Pinterest


load_dotenv()
EMAIL = os.getenv('PINTEREST_EMAIL')
PASSWORD = os.getenv('PINTEREST_PASSWORD')
USERNAME = os.getenv('PINTEREST_USERNAME')
CREDENTIALS_ROOT_DIR = os.getenv('CREDENTIALS_ROOT_DIR')

def dhash(image, hash_size=8):
    # convert image to grayscale and resize, adding single column (width)
    # to compute the horizontal gradient
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (hash_size + 1, hash_size))

    # compute relative horizontal gradiant between adjacent column pixels
    diff = resized[:, 1:] > resized[:, :-1]

    # convert difference image to a hash and return it
    hash = sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])
    return hash



class Pin:

    def __init__(self, response, board, section=None):
        self.properties = {
            'title' : response['title'],
            'description' : response['description'],
            'id' : response['id'],
            'link' : response['link'],
            'board' : board,
            'section' : section
        }
        self.image = {
            'url' : response['images']['orig']['url'],
        }

    def get_id(self):
        return self.properties['id']

    def get_image_url(self):
        return self.image['url']

    def get_board(self):
        return self.properties['board']

    def get_section(self):
        return self.properties['section']

    def get_filetype(self):
        return '.' + self.image['url'].split('.')[-1]


class Feed:

    def __init__(self, client):
        self.client = client
        self.valid_filetypes = ['.jpg', '.jpeg', '.png', '.tiff']
        print('Getting Pinterest feed...')
        self.feed = self.get_feed()

    def get_feed(self, board_id=None):
        feed = {}
        if board_id:
            for section in self.client.get_board(board_id=board_id):
                section_name = section['title']
                feed[section_name] = {}
                for pin in self.client.get_section_pins(section_id=section['id']):
                    if not isinstance(pin['title'], dict):
                        p = Pin(pin, board, section_name)
                        if (p.get_filetype() in self.valid_filetypes):
                            feed[section_name][p.get_id()] = p
                        else:
                            self.client.delete_pin(pin_id=p.get_id())
            for pin in self.client.board_feed(board_id=board_id):
                if not isinstance(pin['title'], dict):
                    p = Pin(pin, board)
                    if (p.get_filetype() in self.valid_filetypes):
                        feed[p.get_id()] = p
                    else:
                        self.client.delete_pin(pin_id=p.get_id())
            return feed

        for board in self.client.boards():
            board_name = board['name']
            feed[board_name] = {}
            for section in self.client.get_board_sections(board_id=board['id']):
                section_name = section['title']
                feed[board_name][section_name] = {}
                for pin in self.client.get_section_pins(section_id=section['id']):
                    if not isinstance(pin['title'], dict):
                        p = Pin(pin, board_name, section_name)
                        if (p.get_filetype() in self.valid_filetypes):
                            feed[board_name][section_name][p.get_id()] = p
                        else:
                            self.client.delete_pin(pin_id=p.get_id())
            for pin in self.client.board_feed(board_id=board['id']):
                if not isinstance(pin['title'], dict):
                    p = Pin(pin, board_name)
                    if (p.get_filetype() in self.valid_filetypes):
                        feed[board_name][p.get_id()] = p
                    else:
                        self.client.delete_pin(pin_id=p.get_id())

        return feed

    def get_boards(self):
        return [k for (k, v) in self.feed.items() if not isinstance(v, Pin)]

    def get_sections(self, board):
        return [k for (k, v) in self.feed[board].items() if not isinstance(v, Pin)]

    def get_board(self, board):
        return self.feed[board]

    def get_section(self, board, section):
        return self.feed[board][section]

    def delete(self, id):
        for (k1, v1) in list(self.feed.items()):
            if not isinstance(v1, Pin):
                for (k2, v2) in list(v1.items()):
                    if not isinstance(v2, Pin):
                        for (k3, v3) in list(v2.items()):
                            if (k3 == id):
                                v2.pop(k3)
                    elif (k2 == id):
                        v1.pop(k2)
            elif (k1 == id):
                self.feed.pop(k1)
        self.client.delete_pin(pin_id=id)


class Image:

    def __init__(self, path):
        self.path = path

        components = path.split(os.sep)
        self.board = components[0]
        self.section = components[1]
        self.id = ''.join(components[-1].split('.')[:-1])

        self.image = cv2.imread(path)
        self.hash = dhash(self.image)

        (height, width, _) = self.image.shape
        self.height = height
        self.width = width
        self.size = height * width
        self.color = tuple(self.image.mean(axis=0).mean(axis=0))


class Manifest:

    def __init__(self):
        self.systemdirs = 'credentials'
        self.systemfiles = ['.env', 'PinSync.py', 'manifest.json', 'desktop.ini']
        print('Loading previous manifest...')
        with open('manifest.json') as f:
            self.old = json.load(f)
        print('Building current manifest...')
        self.current = self.build_manifest()

    def build_manifest(self):
        manifest = {}
        for f1 in os.listdir():
            if (os.path.isdir(f1) and f1 not in self.systemdirs):
                manifest[f1] = {}
                for f2 in os.listdir(f1):
                    sec_path = os.path.join(f1, f2)
                    if (os.path.isdir(sec_path) and f2 not in self.systemdirs):
                        manifest[f1][f2] = {}
                        for (dirpath, dirnames, filenames) in os.walk(sec_path):
                            for f3 in filenames:
                                if (f3 not in self.systemfiles):
                                    id = ''.join(f3.split('.')[:-1])
                                    image_path = os.path.join(dirpath, f3)
                                    manifest[f1][f2][id] = image_path
                    elif (os.path.isfile(sec_path) and f2 not in self.systemfiles):
                        id = ''.join(f2.split('.')[:-1])
                        image_path = os.path.join(f1, f2)
                        manifest[f1][id] = image_path
            elif (os.path.isfile(f1) and f1 not in self.systemfiles):
                id = ''.join(f1.split('.')[:-1])
                manifest[id] = f1
        return manifest

    def get_boards(self):
        boards = [k for (k, v) in self.current.items() if isinstance(v, dict)]
        return boards

    def get_boards_old(self):
        boards = [k for (k, v) in self.old.items() if isinstance(v, dict)]
        return boards

    def get_sections(self, board):
        sections = [k for (k, v) in self.current[board].items() if isinstance(v, dict)]
        return sections

    def get_sections_old(self, board):
        sections = [k for k in self.old[board].keys() if isinstance(k, dict)]
        return sections

    def get_section(self, board, section):
        return self.current[board][section]

    def get_section_old(self, board, section):
        return self.old[board][section]

    def get_board(self, board):
        return self.current[board]

    def get_board_old(self, board):
        return self.old[board]

    def search(self, item, board):
        for (k, v) in self.get_board(board).items():
            if isinstance(v, dict):
                for (id, path) in self.get_section(board, k).items():
                    if id == item:
                        return path
            else:
                if (k == item):
                    return v
        return False

    def search_old(self, item, board):
        for (k, v) in self.get_board_old(board).items():
            if isinstance(v, dict):
                for (id, path) in self.get_section_old(board, k).items():
                    if id == item:
                        return path
            else:
                if (k == item):
                    return v
        return False

    def delete(self, id, board, section=None):
        path = ''
        if section:
            path = self.current[board][section].pop(id)
        else:
            path = self.current[board].pop(id)
        print('\t- ' + path)
        os.remove(path)
        (head, tail) = os.path.split(path)
        while (len(os.listdir(head)) == 0):
            os.rmdir(head)
            (head, tail) = os.path.split(head)

    def download(self, url, path):
        components = path.split(os.sep)
        board = components[0]
        id = ''.join(components[-1].split('.')[:-1])
        if not os.path.exists(board):
            os.mkdir(board)
            self.current[board] = {}

        if (len(components) > 2):
            section = components[1]
            section_path = os.path.join(board, section)
            if not os.path.exists(section_path):
                os.mkdir(section_path)
                self.current[board][section] = {}
            self.current[board][section][id] = path
        else:
            self.current[board][id] = path

        print('\t+ ' + path)
        urllib.request.urlretrieve(url, path)

    def get_deleted_images(self, board):
        deleted_images = []
        for (k, v) in self.get_board_old(board).items():
            if isinstance(v, dict):
                for (id, path) in v.items():
                    if not self.search(id, board):
                        deleted_images.append(id)
            else:
                if not self.search(k, board):
                    deleted_images.append(k)
        return deleted_images

    def get_duplicate_images(self, board, section=None):
        duplicates = []
        hashes = {}

        images = self.process_images(board, section)
        for (k1, im1) in images.items():
            if isinstance(im1, dict):
                for (k2, im2) in im1.items():
                    hash = im2.hash
                    if hash not in hashes.keys():
                        hashes[hash] = []
                    hashes[hash].append(im2)
            else:
                hash = im1.hash
                if hash not in hashes.keys():
                    hashes[hash] = []
                hashes[hash].append(im1)

        for (hash, ims) in hashes.items():
            paths = [i.path for i in ims]
            if (len(paths) > 1):
                colors = set([i.color for i in ims])
                if (len(paths) > len(colors)):
                    # images are actually duplicate and not just recolors
                    ids = [i.id for i in ims]
                    if not all([id == ids[0] for id in ids]):
                        # images represent unique pins
                        duplicates.append(ims)

        return duplicates

    def remove_duplicates(self, board, section=None):
        deleted_pins = []
        for dup in self.get_duplicate_images(board, section):
            dup = sorted(dup, key=lambda im: im.id)
            choice = max(dup, key=lambda im: im.size)
            for image in dup:
                board = image.board
                if (image.id != choice.id):
                    self.delete(image.id, image.board, image.section)
                    deleted_pins.append(image.id)
        return deleted_pins

    '''
    # deprecated, but a useful code snippet to keep around
    def flatten(self, dict1):
        def generator(dict2):
            for (k, v) in dict2.items():
                if isinstance(v, dict):
                    yield from generator(v)
                else:
                    yield (k, v)

        flattened_dict = {}
        for (key, value) in generator(dict1):
            flattened_dict[key] = value
        return flattened_dict
    '''

    def process_images(self, board, section=None):
        images = {}
        if section:
            index = self.current[board][section]
            for (id, path) in index.items():
                images[id] = Image(path)
        else:
            index = self.current[board]
            for (k1, v1) in index.items():
                if isinstance(v1, dict):
                    images[k1] = {}
                    for (k2, v2) in v1.items():
                        images[k1][k2] = Image(v2)
                else:
                    images[k1] = Image(v1)
        return images

    def save(self):
        print('Saving manifest...')
        with open('manifest.json', 'w') as f:
            json.dump(self.current, f)


class Manager:

    def __init__(self, email, password, username, cred_root):
        print('Establishing connection to Pinterest...')
        self.client = Pinterest(email=email,
                                password=password,
                                username=username,
                                cred_root=cred_root)
        self.client.login()
        self.feed = Feed(self.client)
        self.manifest = Manifest()

    def sync_board(self, board):
        print('Syncing ' + board + '...')
        self.reflect_local_changes(board)

        local = self.manifest.get_board(board)
        cloud = self.feed.get_board(board)

        # remove local files which have been deleted from pinterest
        for (k, v) in list(local.items()):
            if isinstance(v, dict):
                cloud_section = {}
                if k in cloud.keys():
                    cloud_section = cloud[k]
                local_section = v
                for (id, path) in list(local_section.items()):
                    if (id not in list(cloud_section.keys())):
                        self.manifest.delete(id, board, k)
            else:
                if (k not in list(cloud.keys())):
                    self.manifest.delete(k, board)

        # download images which are not present on local storage
        for (k, v) in list(cloud.items()):
            if not isinstance(v, Pin):
                local_section = {}
                if k in local.keys():
                    local_section = local[k]
                cloud_section = v
                for (id, pin) in list(cloud_section.items()):
                    if (id not in list(local_section.keys())):
                        url = pin.get_image_url()
                        extension = pin.get_filetype()
                        section = pin.get_section()
                        path = os.path.join(board, section, id + extension)
                        self.manifest.download(url, path)
            else:
                if (k not in list(local.keys())):
                    url = v.get_image_url()
                    extension = v.get_filetype()
                    path = os.path.join(board, k + extension)
                    self.manifest.download(url, path)

        # delete duplicates
        for id in self.manifest.remove_duplicates(board):
            self.feed.delete(id)

    def sync(self):
        for board in self.feed.get_boards():
            self.sync_board(board)
        self.manifest.save()

    def reflect_local_changes(self, board):
        deleted_images = [id for id in self.manifest.get_deleted_images(board)]
        if (len(deleted_images) > 0):
            state = '\t> %d local files have been deleted since last sync.' \
                    % len(deleted_images)
            if (len(deleted_images) == 1):
                state = '\t> 1 local file has been deleted since last sync.'
            prompt = '\tDo you want to push these changes to Pinterest? (y/n) '
            print()
            print(state)
            response = input(prompt)
            affirmative = ['y', 'yes']
            negative = ['n', 'no']
            while (response.lower() not in affirmative + negative):
                response = input(prompt)
            if response.lower() in affirmative:
                for id in deleted_images:
                    self.feed.delete(id)
            print()


if __name__ == '__main__':

    #TODO: if a board/section is not found in manifest, create it

    p = Manager(EMAIL, PASSWORD, USERNAME, CREDENTIALS_ROOT_DIR)
    p.sync()
