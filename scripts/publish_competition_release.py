"""Build the clean source archive and publish the authorized competition release."""
from pathlib import Path
import hashlib, http.client, json, mimetypes, select, socket, ssl, sys, time
import urllib.request, urllib.parse, urllib.error, zipfile
from publish_open_source import ROOT, OWNER, REPO, git, credentials, api

DEST = ROOT / 'iCAN_应用方案/07_最终提交'
SOURCE = DEST / '03_纹脉华章_应用程序源代码.zip'
PDF = DEST / '01_纹脉华章_应用方案.pdf'
VIDEO = DEST / '02_纹脉华章_演示视频.mp4'
BASE = f'/repos/{OWNER}/{REPO}'
REMOTE_NAMES = {
    SOURCE.name: 'Wenmai_Huazhang_Source_Code_v1.0.0.zip',
    PDF.name: 'Wenmai_Huazhang_Application_Proposal.pdf',
    VIDEO.name: 'Wenmai_Huazhang_2026_iCAN_Demo.mp4',
}
UPLOAD_TIMEOUT = 900
UPLOAD_ATTEMPTS = 3
STREAM_BLOCK_BYTES = 256 * 1024


class StreamingHTTPSConnection(http.client.HTTPSConnection):
    """Preserve partial-write progress when SSL applies backpressure."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('blocksize', STREAM_BLOCK_BYTES)
        super().__init__(*args, **kwargs)

    def send(self, data):
        if self.sock is None:
            if self.auto_open:
                self.connect()
            else:
                raise http.client.NotConnected()
        if hasattr(data, 'read'):
            while block := data.read(self.blocksize):
                self.send(block)
            return
        if not isinstance(data, (bytes, bytearray, memoryview)):
            for block in data:
                self.send(block)
            return
        pending = memoryview(data)
        deadline = time.monotonic() + (self.sock.gettimeout() or UPLOAD_TIMEOUT)
        while pending:
            try:
                written = self.sock.send(pending)
                if not written:
                    raise ConnectionError('HTTPS connection closed during upload')
                pending = pending[written:]
            except (ssl.SSLWantWriteError, ssl.SSLWantReadError) as exc:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise socket.timeout('HTTPS upload stalled') from None
                readable = [self.sock] if isinstance(exc, ssl.SSLWantReadError) else []
                writable = [self.sock] if isinstance(exc, ssl.SSLWantWriteError) else []
                select.select(readable, writable, [], min(remaining, 1.0))


class StreamingHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, request):
        return self.do_open(StreamingHTTPSConnection, request, context=self._context)


def file_sha256(path):
    checksum = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            checksum.update(block)
    return checksum.hexdigest()


def owned_asset(asset, path, remote_name):
    """Recognize this task's exact names and earlier normalized Chinese names."""
    name = asset.get('name', '')
    legacy_names = {SOURCE.name: '03_._.zip', PDF.name: '01_._.pdf', VIDEO.name: '02_._.mp4'}
    return name in (remote_name, path.name, legacy_names.get(path.name))


def delete_asset(asset_id, token):
    # GitHub DELETE returns HTTP 204 with no JSON body.
    request = urllib.request.Request(
        'https://api.github.com' + BASE + f'/releases/assets/{asset_id}',
        headers={'Authorization': 'Bearer ' + token, 'User-Agent': 'wenmai-publication',
                 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'},
        method='DELETE',
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        response.read()


def matching_asset(assets, path, remote_name):
    preferred = sorted(assets, key=lambda asset: asset.get('name') != remote_name)
    return next((asset for asset in preferred
                 if owned_asset(asset, path, remote_name)
                 and asset.get('state', 'uploaded') == 'uploaded'
                 and asset.get('size') == path.stat().st_size), None)


def upload_asset(release, path, token):
    """Stream raw octets, reuse successful assets, and retry at most three times."""
    remote_name = REMOTE_NAMES[path.name]
    endpoint = release['upload_url'].split('{')[0] + '?' + urllib.parse.urlencode({
        'name': remote_name, 'label': path.stem,
    })
    opener = urllib.request.build_opener(StreamingHTTPSHandler())
    for attempt in range(UPLOAD_ATTEMPTS):
        assets = api(BASE + f'/releases/{release["id"]}/assets', token=token)
        existing = matching_asset(assets, path, remote_name)
        if existing:
            if existing['name'] != remote_name:
                conflicts = [asset for asset in assets if asset.get('name') == remote_name
                             and asset['id'] != existing['id']]
                if conflicts and not release.get('draft'):
                    raise RuntimeError('Refusing to replace assets on an already published release')
                for asset in conflicts:
                    delete_asset(asset['id'], token)
                existing = api(BASE + f'/releases/assets/{existing["id"]}',
                               {'name': remote_name, 'label': path.stem},
                               method='PATCH', token=token)
            return existing
        stale = [asset for asset in assets if owned_asset(asset, path, remote_name)]
        if stale and not release.get('draft'):
            raise RuntimeError('Refusing to replace assets on an already published release')
        for asset in stale:
            delete_asset(asset['id'], token)
        headers = {
            'Authorization': 'Bearer ' + token,
            'User-Agent': 'wenmai-publication',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': mimetypes.guess_type(path.name)[0] or 'application/octet-stream',
            'Content-Length': str(path.stat().st_size),
        }
        try:
            # A file object makes http.client read bounded raw-octet blocks.
            # Reopen the file for each attempt; no entire-video byte buffer.
            with path.open('rb') as stream:
                request = urllib.request.Request(endpoint, data=stream, headers=headers, method='POST')
                with opener.open(request, timeout=UPLOAD_TIMEOUT) as response:
                    asset = json.load(response)
            if asset.get('state') != 'uploaded' or asset.get('size') != path.stat().st_size:
                raise ConnectionError('GitHub did not confirm a complete asset upload')
            return asset
        except urllib.error.HTTPError as exc:
            if exc.code not in (408, 422, 429, 500, 502, 503, 504):
                raise RuntimeError(f'Asset upload rejected by GitHub (HTTP {exc.code})') from None
            reason = f'HTTP {exc.code}'
        except (urllib.error.URLError, OSError, ConnectionError, http.client.HTTPException):
            reason = 'connection interrupted'
        if attempt + 1 < UPLOAD_ATTEMPTS:
            print(f'Upload retry {attempt + 2}/{UPLOAD_ATTEMPTS}: {path.name} ({reason})', flush=True)
            time.sleep(5 * (attempt + 1))
    # The final response can be lost after GitHub completed the upload.
    assets = api(BASE + f'/releases/{release["id"]}/assets', token=token)
    existing = matching_asset(assets, path, remote_name)
    if existing:
        return existing
    raise RuntimeError(f'Asset upload failed after {UPLOAD_ATTEMPTS} attempts: {path.name}')


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    git('archive', '--format=zip', '--prefix=wenmai-huazhang/', '--output=' + str(SOURCE), 'HEAD')
    with zipfile.ZipFile(SOURCE) as archive:
        names = archive.namelist()
        for name in names:
            parts = Path(name).parts
            if (any(part in ('node_modules', 'venv', '.cache', '.git') for part in parts)
                    or (Path(name).name.startswith('.env') and Path(name).name != '.env.example')):
                raise RuntimeError('Archive scope check failed')
    print(json.dumps({'sourceArchive': str(SOURCE), 'commit': git('rev-parse', 'HEAD'),
                      'files': len(names)}, ensure_ascii=False), flush=True)
    preparing = '--prepare-release' in sys.argv
    if '--publish' not in sys.argv and not preparing:
        return
    upload_files = (SOURCE, PDF, VIDEO) if VIDEO.exists() or not preparing else (SOURCE, PDF)
    for path in upload_files:
        if not path.is_file():
            raise RuntimeError('Final submission asset missing: ' + path.name)
    token = credentials()
    try:
        release = api(BASE + '/releases/tags/v1.0.0', token=token)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        releases = api(BASE + '/releases', token=token)
        release = next((item for item in releases if item.get('tag_name') == 'v1.0.0'), None)
        if release is None:
            release = api(BASE + '/releases', {
                'tag_name': 'v1.0.0', 'target_commitish': 'main',
                'name': '纹脉华章 v1.0.0 · 2026 iCAN 演示与源代码',
                'body': '传统文化视觉智能创作与文创应用平台。\n\n- 17页应用方案，含正式封面。\n- 4分25秒真实产品操作演示，1080p / 30fps / H.264 / AAC，中文配音与字幕。\n- MIT开源应用源代码；第三方模型和素材分别遵守原许可。\n\n运行前请阅读源码中的 README.md，并自行配置模型服务凭据。发行包不包含 API Key、虚拟环境、依赖目录或模型权重。',
                'draft': True, 'prerelease': False,
            }, token=token)
    manifest = []
    for path in upload_files:
        asset = upload_asset(release, path, token)
        manifest.append({'name': path.name, 'remoteName': asset['name'],
                         'bytes': path.stat().st_size, 'sha256': file_sha256(path),
                         'url': asset['browser_download_url']})
        print('Prepared asset: ' + path.name, flush=True)
    if not preparing:
        review = json.loads((ROOT / 'iCAN_应用方案/视频/08_review/final_video_verification.json').read_text(encoding='utf-8'))
        if (len(review.get('playbacks', [])) != 2 or review.get('completeDecode') != 'passed'
                or review.get('blackIntervals')):
            raise RuntimeError('Video final verification incomplete')
        if review.get('sha256') != file_sha256(VIDEO):
            raise RuntimeError('Submission video differs from the verified export')
        if VIDEO.stat().st_size >= 200_000_000:
            raise RuntimeError('Video exceeds the user size limit')
        release = api(BASE + f'/releases/{release["id"]}', {'draft': False}, method='PATCH', token=token)
        # Draft download URLs can change after the final tag becomes public.
        published_assets = api(BASE + f'/releases/{release["id"]}/assets', token=token)
        for entry in manifest:
            published = next(item for item in published_assets if item['name'] == entry['remoteName'])
            entry['url'] = published['browser_download_url']
    (DEST / '发行文件校验.json').write_text(json.dumps({
        'release': release['html_url'], 'release_id': release['id'],
        'draft': release.get('draft', False), 'commit': git('rev-parse', 'HEAD'), 'files': manifest,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'release': release['html_url'], 'assets': len(manifest),
                      'draft': release.get('draft', False)}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
