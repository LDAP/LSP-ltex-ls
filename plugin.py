from LSP.plugin import AbstractPlugin
from LSP.plugin import register_plugin
from LSP.plugin import unregister_plugin
from LSP.plugin import Response
from LSP.plugin import ClientConfig
from LSP.plugin import WorkspaceFolder
from LSP.plugin.core.typing import Optional, Dict, List
import os
import sublime
import shutil
import tempfile
import requests
import time
import tarfile


GITHUB_DL_URL = 'https://github.com/valentjn/ltex-ls/releases/download/'\
                    '{0}/ltex-ls-{0}.tar.gz'  # Format with Release-Tag
GITHUB_RELEASES_API_URL = 'https://api.github.com/repos/valentjn/ltex-'\
                          'ls/releases/latest'
SERVER_FOLDER_NAME = 'ltex-ls-{}'  # Format with Release-Tag
LATEST_RELEASE_TAG = None
STORAGE_FOLDER_NAME = 'LSP-ltex-ls'
SETTINGS_FILENAME = 'LSP-ltex-ls.sublime-settings'


def show_download_progress(finished, total) -> None:
    """
    Shows the download progress in the Sublime status bar

    :param      finished:  A measure how much is finished
    :type       finished:  double or None
    :param      total:     A measure of the total amount to download
    :type       total:     double or None

    :returns:   Nothing
    :rtype:     None
    """
    if finished and total:
        percent = finished * 100 / total
        sublime.status_message('ltex-ls: downloading: {0:2.2f}%'
                               .format(percent))
    else:
        sublime.status_message('ltex-ls: downloading...')


def download_file(url, file_name, show_progress) -> None:
    """
    Downloads a file and shows the progress.

    :param      url:            The url to download drom
    :type       url:            string
    :param      file_name:      The path to the file to download to
    :type       file_name:      string
    :param      show_progress:  The show progress
    :type       show_progress:  a function taking to doubles

    :returns:   Nothing
    :rtype:     None
    """
    r = requests.get(url, stream=True)
    total_length = r.headers.get('content-length')

    with open(file_name, 'wb') as out_file:
        if total_length:
            finished = 0
            total_length = int(total_length)
            last_displayed = 0
            for chunk in r.iter_content(chunk_size=4096):
                if last_displayed != int(time.time()):
                    show_progress(finished, total_length)
                    last_displayed = int(time.time())
                finished += len(chunk)
                out_file.write(chunk)
        else:
            out_file.write(r.content)
            show_progress(None, None)
    show_progress(1, 1)


def fetch_latest_release() -> None:
    """
    Fetches a the latest release via GitHub API.

    :returns:   Nothing.
    :rtype:     None
    """
    global LATEST_RELEASE_TAG

    if (LATEST_RELEASE_TAG is None):
        try:
            resp = requests.get(GITHUB_RELEASES_API_URL)
            data = resp.json()
            LATEST_RELEASE_TAG = data['tag_name']
        except requests.ConnectionError:
            LATEST_RELEASE_TAG = None


fetch_latest_release()


class LTeXLs(AbstractPlugin):
    @classmethod
    def name(cls) -> str:
        return "ltex-ls"

    @classmethod
    def serverversion(cls) -> str:
        """
        Returns the versionof ltex-ls to use. Can be None if
        no connection is available and no version is set in settings.

        :param      cls:  The class
        :type       cls:  type

        :returns:   The version of ltex-ls to use. Can be None.
        :rtype:     str
        """
        settings = sublime.load_settings(SETTINGS_FILENAME)
        version = settings.get('version')
        return version or LATEST_RELEASE_TAG

    @classmethod
    def basedir(cls) -> str:
        """
        The directry of this plugin in Package Storage.

        :param      cls:  The class
        :type       cls:  type

        :returns:   The path this plugins base directory
        :rtype:     str
        """
        return os.path.join(cls.storage_path(), STORAGE_FOLDER_NAME)

    @classmethod
    def serverdir(cls) -> str:
        """
        The directory of the server. In here are the "bin" and "lib"
        folders.

        :param      cls:  The class
        :type       cls:  type

        :returns:   The server directory if a version can be determined.
                    If not the last used server directory or None if none
                    if found.
        :rtype:     str
        """
        if cls.serverversion():
            return os.path.join(cls.basedir(), SERVER_FOLDER_NAME
                                .format(cls.serverversion()))
        else:
            if not os.path.isdir(cls.basedir()):
                return None
            offline = os.listdir(cls.basedir())
            if offline:
                return os.path.join(cls.basedir(), offline[0])
        return None

    @classmethod
    def needs_update_or_installation(cls) -> bool:
        return not cls.serverdir() or not os.path.isdir(cls.serverdir())

    @classmethod
    def additional_variables(cls) -> Optional[Dict[str, str]]:
        #  settings = sublime.load_settings("LSP-ltex-ls.sublime-settings")
        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            java_executable = os.path.join(java_home, "bin", "java")
        else:
            java_executable = "java"
        return {
            "java_executable": java_executable,
            "serverdir": cls.serverdir()
        }

    @classmethod
    def install_or_update(cls) -> None:
        if not cls.serverversion():
            return
        if os.path.isdir(cls.basedir()):
            shutil.rmtree(cls.basedir())
        os.makedirs(cls.basedir())
        with tempfile.TemporaryDirectory() as tempdir:
            tar_path = os.path.join(tempdir, 'server.tar.gz')
            download_file(GITHUB_DL_URL.format(cls.serverversion()),
                          tar_path,
                          show_download_progress)
            sublime.status_message('ltex-ls: extracting')
            tar = tarfile.open(tar_path, "r:gz")
            tar.extractall(tempdir)
            tar.close()
            shutil.move(os.path.join(tempdir, SERVER_FOLDER_NAME
                                     .format(cls.serverversion())),
                        cls.basedir())
            sublime.status_message('ltex-ls: installed ltex-ls {}'.format(
                                    cls.serverversion()))

    @classmethod
    def can_start(cls, window: sublime.Window, initiating_view: sublime.View,
                  workspace_folders: List[WorkspaceFolder],
                  configuration: ClientConfig) -> Optional[str]:
        if not cls.serverdir():
            return 'Download failed or version could not be determined.'
        return None

    # Handle protocol extensions
    def m_ltex_workspaceSpecificConfiguration(self, params, request_id):
        session = self.weaksession()
        if not session:
            return
        result = []
        for item in params['items']:
            print(item)
            result.append({
                "dictionary": {},
                "disabledRules": {},
                "enabledRules": {},
                "hiddenFalsePositives": {},
                })
        session.send_response(Response(request_id, result))

    def m_ltex_progress(self, params):
        # notification do not require a response
        settings = sublime.load_settings(SETTINGS_FILENAME)
        if not settings.get('settings').get('ltex.statusBarItem'):
            return
        if not params or not params['operation']:
            return
        if params['operation'] == 'checkDocument':
            if (params['progress'] == 0):
                sublime.status_message('ltex-ls: checking: {}'
                                       .format(params['uri']))
            else:
                sublime.status_message('ltex-ls: finished: {}'
                                       .format(params['uri']))
        else:
            sublime.status_message('ltex-ls: unknown operation')


def plugin_loaded() -> None:
    register_plugin(LTeXLs)


def plugin_unloaded() -> None:
    unregister_plugin(LTeXLs)
