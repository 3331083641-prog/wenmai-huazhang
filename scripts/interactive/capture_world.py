"""Real local browser evidence, without cloud calls or a persistent browser profile.

Install backend/requirements-review.txt. Edge is used by default; set
WENMAI_REVIEW_BROWSER_CHANNEL=chromium after `python -m playwright install chromium`
to use Playwright's optional browser. Invalid inputs raise ValueError; runtime
failures return evidence with failed checks, never an invented successful capture.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import unquote, urlsplit, urlunsplit

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[2]
EDGE = Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
CURATED_SLUGS = {
    'zhuxianzhen-ruimao': 'zhuxianzhen', 'bianxiu-xiutu': 'bianxiu',
    'songhua-yunhe': 'songhua', 'qinghua-dieyun': 'qinghua', 'jianzhi-linghu': 'jianzhi',
}
VIEWPORT = {'width': 1440, 'height': 1000}
HARD_CHECKS = (
    'canvas', 'slug_matches', 'not_degraded', 'no_page_errors', 'no_render_errors',
    'no_failed_requests', 'hotspots_visible', 'hotspot_click',
    'nonblank_frames', 'camera_changed', 'parallax',
)


def capture_checks_passed(checks: dict, errors: list | None = None) -> bool:
    """A static artwork need not move; preserve motion as informational evidence.

    Required geometry, rendering and interaction checks still must be explicitly
    true. Missing checks, earlier `passed` values or a measured motion change
    cannot compensate for a required failure.
    """
    return not errors and all(checks.get(key) is True for key in HARD_CHECKS)


def validate_case_id(case_id: str) -> str:
    if not isinstance(case_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', case_id):
        raise ValueError('case_id must be 1-128 safe ASCII letters, digits, underscores or hyphens')
    return case_id


def expected_world_slug(case_id: str) -> str:
    return CURATED_SLUGS.get(validate_case_id(case_id), case_id)


def _loopback(hostname: str | None) -> bool:
    if hostname == 'localhost':
        return True
    try:
        return ipaddress.ip_address(hostname or '').is_loopback
    except ValueError:
        return False


def world_url(case_id: str, base_url: str, route: str = 'wander') -> str:
    validate_case_id(case_id)
    if route not in ('wander', 'experience', 'story'):
        raise ValueError('unsupported local route')
    try:
        parsed = urlsplit(base_url)
        port = parsed.port
        valid = (parsed.scheme in ('http', 'https') and _loopback(parsed.hostname)
                 and parsed.username is None and parsed.password is None
                 and not parsed.query and parsed.fragment in ('', '/')
                 and '\\' not in base_url and not any(ord(c) < 33 for c in base_url)
                 and port != 0)
        decoded = unquote(parsed.path)
        valid = valid and not any(part == '..' for part in decoded.split('/'))
        valid = valid and decoded == parsed.path and '//' not in parsed.path
        if not valid:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise ValueError('base_url must be a credential-free loopback HTTP preview URL') from None
    prefix = urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip('/') + '/', '', ''))
    return prefix + ('#/' if '#' in base_url else '') + f'{route}/{case_id}'


def validate_output_dir(output_dir: str | Path) -> Path:
    output = Path(output_dir).resolve()
    if output.drive.upper() != 'D:' or not output.is_relative_to(ROOT):
        raise ValueError('capture output must remain in D:/wenmai-huazhang')
    return output


def image_evidence(path: str | Path) -> dict:
    path = Path(path)
    with Image.open(path) as image:
        rgb = image.convert('RGB')
        variance = max(ImageStat.Stat(rgb).var)
        return {'width': rgb.width, 'height': rgb.height, 'nonblank': variance > 1,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def image_difference(first: str | Path, second: str | Path) -> dict:
    """Report actual RGB pixel differences; no claim about 3D reconstruction or FPS."""
    with Image.open(first) as a, Image.open(second) as b:
        if a.size != b.size:
            raise ValueError('comparison frames must have identical dimensions')
        difference = ImageChops.difference(a.convert('RGB'), b.convert('RGB'))
        mean = sum(ImageStat.Stat(difference).mean) / 3
        channels = difference.split()
        maximum = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
        histogram = maximum.histogram()
        changed = sum(histogram[9:]) / (a.width * a.height)
        return {'mean_absolute_difference': round(mean, 6),
                'changed_pixel_ratio': round(changed, 6), 'pixel_threshold': 8}


def _request_label(url: str) -> str:
    # Never persist queries, fragments, authentication, or remote addresses.
    parsed = urlsplit(url)
    return parsed.path[:240] if _loopback(parsed.hostname) else '[non-loopback resource]'


def _ignorable_request(url: str, resource_type: str) -> bool:
    parsed = urlsplit(url)
    return (resource_type == 'websocket' or parsed.path.endswith('/favicon.ico')
            or parsed.path == '/@vite/client'
            or (not _loopback(parsed.hostname) and resource_type in ('stylesheet', 'font')))


@contextmanager
def _local_playwright(factory, output: Path):
    """Start the driver with D-drive temporary storage, restoring caller env immediately.

    Only driver startup briefly changes TEMP/TMP. Its child process retains these
    paths, including Chromium's automatically generated, disposable user profile.
    The review worker serializes capture calls globally.
    """
    with tempfile.TemporaryDirectory(prefix='.browser-', dir=output) as temporary:
        previous = {key: os.environ.get(key) for key in ('TEMP', 'TMP')}
        try:
            os.environ.update(TEMP=temporary, TMP=temporary)
            manager = factory().start()
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        try:
            yield manager, temporary
        finally:
            manager.stop()


def capture_world(case_id: str, output_dir: str | Path,
                  base_url: str = 'http://127.0.0.1:5173', *,
                  expected_slug: str | None = None, include_content: bool = True) -> dict:
    """Capture six canvas JPEGs plus real hotspot/content UI, bounded to ~90 seconds.

    The backend must expose the new case metadata before calling this function.
    All hard checks are separate booleans. Motion differences are measurements,
    not hardware performance scores. This synchronous function must be called
    from a worker thread/process rather than an active asyncio event loop.
    """
    url = world_url(case_id, base_url)
    output = validate_output_dir(output_dir)
    expected = validate_case_id(expected_slug) if expected_slug is not None else expected_world_slug(case_id)
    channel = os.environ.get('WENMAI_REVIEW_BROWSER_CHANNEL', 'msedge')
    if channel not in ('msedge', 'chromium'):
        raise ValueError('WENMAI_REVIEW_BROWSER_CHANNEL must be msedge or chromium')
    output.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    deadline = start + 90
    result = {'case_id': case_id, 'url': url, 'expected_slug': expected,
              'viewport': dict(VIEWPORT), 'device_scale_factor': 1,
              'frames': [], 'snapshots': {}, 'errors': [], 'failed_requests': [],
              'blocked_external_resources': [],
              'checks': {key: False for key in (*HARD_CHECKS, 'motion')},
              'measurements': {}, 'content': {}}
    page_errors = []
    render_errors = []
    stage = 'dependency'

    def budget(limit: int = 12000) -> int:
        remaining = int((deadline - time.monotonic()) * 1000)
        if remaining <= 0:
            raise TimeoutError('capture time budget exhausted')
        return min(limit, remaining)

    try:
        from playwright.sync_api import sync_playwright
        stage = 'launch'
        with _local_playwright(sync_playwright, output) as (playwright, browser_tmp):
            # An allowlist prevents backend API credentials entering the browser process.
            browser_env = {key: value for key, value in os.environ.items() if key.upper() in (
                'PATH', 'SYSTEMROOT', 'WINDIR', 'PROGRAMFILES', 'PROGRAMFILES(X86)',
                'LOCALAPPDATA', 'APPDATA', 'USERPROFILE', 'COMSPEC', 'TEMP', 'TMP')}
            browser_env.update(TEMP=browser_tmp, TMP=browser_tmp)
            launch = {'headless': True, 'timeout': budget(15000), 'env': browser_env,
                      'args': ['--enable-unsafe-swiftshader', '--no-first-run']}
            if channel == 'msedge':
                launch.update({'executable_path': str(EDGE)} if EDGE.is_file() else {'channel': 'msedge'})
            browser = playwright.chromium.launch(**launch)
            try:
                context = browser.new_context(viewport=VIEWPORT, device_scale_factor=1,
                                              reduced_motion='no-preference', service_workers='block')
                # Case artwork and backend resources stay local, including redirects.
                def local_only(route):
                    parsed = urlsplit(route.request.url)
                    if (parsed.scheme in ('http', 'https') and _loopback(parsed.hostname)
                            and parsed.username is None and parsed.password is None):
                        route.continue_()
                    else:
                        result['blocked_external_resources'].append({'type': route.request.resource_type})
                        route.abort('blockedbyclient')
                context.route('**/*', local_only)
                page = context.new_page()
                page.set_default_timeout(budget())
                page.on('pageerror', lambda error: page_errors.append(type(error).__name__))
                def console_error(message):
                    if message.type == 'error' and re.search(
                            r'WebGL|VALIDATE_STATUS|shader error|context lost|Error creating WebGL',
                            message.text, re.I):
                        render_errors.append('webgl_render_error')
                page.on('console', console_error)

                def failed(request):
                    if not _ignorable_request(request.url, request.resource_type):
                        result['failed_requests'].append({'path': _request_label(request.url),
                                                          'type': request.resource_type})
                page.on('requestfailed', failed)
                page.on('response', lambda response: failed(response.request) if response.status >= 400 else None)
                stage = 'navigation'
                page.goto(url, wait_until='domcontentloaded', timeout=budget(20000))
                page.wait_for_function('() => Boolean(window.__paintingWorld?.manifest)', timeout=budget(15000))
                manifest = page.evaluate('() => window.__paintingWorld.manifest')
                result['world_slug'] = manifest.get('slug')
                result['manifest_sha256'] = hashlib.sha256(json.dumps(
                    manifest, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
                result['asset_revision'] = manifest.get('provenance', {}).get('asset_revision')
                result['manifest'] = manifest
                result['checks']['slug_matches'] = result['world_slug'] == expected
                if not result['checks']['slug_matches']:
                    raise RuntimeError('world slug mismatch')
                canvas = page.locator('canvas').first
                canvas.wait_for(state='visible', timeout=budget())
                box = canvas.bounding_box(timeout=budget())
                result['checks']['canvas'] = bool(box and box['width'] > 100 and box['height'] > 100)
                stage = 'entry'
                # Manifest/API publication precedes suspense-loaded textures. CameraRig
                # initializes when textures finish and would otherwise erase enter().
                page.wait_for_function('() => { const s=window.__paintingWorld.snapshot(); return s.frame>2 && s.distance>0 && s.hotspots.length>0; }', timeout=budget(15000))
                result['snapshots']['ready'] = page.evaluate('() => window.__paintingWorld.snapshot()')
                page.evaluate('() => { window.__paintingWorld.reset(); window.__paintingWorld.enter(); }')
                page.wait_for_function("() => window.__paintingWorld.snapshot().phase === 'inside'", timeout=budget(12000))
                page.evaluate('() => { window.__paintingWorld.freeze(true); window.__paintingWorld.reset(); }')

                def settle(yaw=0, distance=None):
                    page.evaluate('([yaw, distance]) => { const w=window.__paintingWorld; w.setYawDeg(yaw); w.setPitchDeg(0); if(distance!==null) w.setDistance(distance); }', [yaw, distance])
                    page.wait_for_timeout(min(500, budget()))
                    page.wait_for_function('([yaw,distance]) => { const s=window.__paintingWorld.snapshot(); return Math.abs(s.yawDeg-yaw)<.06 && Math.abs(s.pitchDeg)<.06 && (distance===null || Math.abs(s.distance-distance)<.003); }', arg=[yaw, distance], timeout=budget(6000))

                def frame(label):
                    path = output / f'{label}.jpg'
                    canvas.screenshot(path=str(path), type='jpeg', quality=92, timeout=budget())
                    evidence = image_evidence(path)
                    result['frames'].append({'label': label, 'path': str(path), **evidence})
                    result['snapshots'][label] = page.evaluate('() => window.__paintingWorld.snapshot()')

                stage = 'views'
                settle()
                frame('front')
                front = result['snapshots']['front']
                rest = front['distance']
                if not isinstance(rest, (int, float)) or not math.isfinite(rest) or rest <= 0:
                    raise RuntimeError('invalid camera distance')
                yaw_limit = float(manifest['camera']['yaw_limit_deg'])
                if not math.isfinite(yaw_limit) or yaw_limit <= 0:
                    raise RuntimeError('invalid camera yaw limit')
                angle = min(8, yaw_limit * .8)
                settle(-angle, rest); frame('left')
                settle(angle, rest); frame('right')
                settle(0, rest * .88); frame('near')
                settle(0, rest)
                stage = 'hotspots'
                hotspots = front.get('hotspots', [])
                manifest_ids = {spot['id'] for spot in manifest.get('hotspots', [])}
                visible_ids = {spot['id'] for spot in hotspots if spot.get('visible')
                               and 0 < spot['x'] < 1 and 0 < spot['y'] < 1}
                result['checks']['hotspots_visible'] = bool(manifest_ids) and manifest_ids <= visible_ids
                if hotspots and result['checks']['hotspots_visible']:
                    spot = hotspots[0]
                    box = canvas.bounding_box(timeout=budget())
                    page.mouse.click(box['x'] + box['width'] * spot['x'], box['y'] + box['height'] * spot['y'])
                    try:
                        page.wait_for_function('(id) => window.__paintingWorld.snapshot().selectedId === id', arg=spot['id'], timeout=budget(2000))
                        result['checks']['hotspot_click'] = True
                        result['snapshots']['hotspot'] = page.evaluate('() => window.__paintingWorld.snapshot()')
                        path = output / 'hotspot.jpg'
                        page.screenshot(path=str(path), type='jpeg', quality=92, timeout=budget())
                        result['frames'].append({'label': 'hotspot', 'path': str(path), **image_evidence(path)})
                        result['content']['hotspot_text'] = page.locator('body').inner_text(timeout=budget())[:16000]
                    except Exception:
                        result['errors'].append('hotspot_click_not_selected')
                page.evaluate('() => { window.__paintingWorld.select(null); window.__paintingWorld.reset(); }')
                page.mouse.move(2, 2)
                settle(0, rest)
                stage = 'motion'
                page.evaluate('() => window.__paintingWorld.freeze(false)')
                page.wait_for_timeout(min(250, budget()))
                frame('motionBefore')
                page.wait_for_timeout(min(2000, budget()))
                frame('motionAfter')
                page.evaluate('() => window.__paintingWorld.freeze(true)')
                result['snapshots']['final'] = page.evaluate('() => window.__paintingWorld.snapshot()')
                result['checks']['not_degraded'] = all(not snapshot.get('degraded', True)
                    for snapshot in result['snapshots'].values())
                result['checks']['nonblank_frames'] = all(item['nonblank'] for item in result['frames'])
                result['checks']['camera_changed'] = (
                    result['snapshots']['left']['yawDeg'] < -.1
                    and result['snapshots']['right']['yawDeg'] > .1
                    and result['snapshots']['near']['distance'] < rest * .95)
                paths = {item['label']: item['path'] for item in result['frames']}
                for label, first, second in (('parallax', 'front', 'left'), ('motion', 'motionBefore', 'motionAfter')):
                    measure = image_difference(paths[first], paths[second])
                    result['measurements'][label] = measure
                    result['checks'][label] = measure['changed_pixel_ratio'] > 0
                before, after = result['snapshots']['motionBefore'], result['snapshots']['motionAfter']
                stationary = (abs(before['yawDeg'] - after['yawDeg']) < .06
                              and abs(before['distance'] - after['distance']) < .003)
                result['measurements']['motion_camera_stationary'] = stationary
                result['checks']['motion'] = result['checks']['motion'] and stationary
                if include_content:
                    stage = 'content'
                    for route_name in ('experience', 'story'):
                        page.goto(world_url(case_id, base_url, route_name), wait_until='networkidle', timeout=budget(12000))
                        page.wait_for_timeout(min(700, budget()))
                        path = output / f'{route_name}.jpg'
                        page.screenshot(path=str(path), type='jpeg', quality=85, full_page=True, timeout=budget())
                        result['frames'].append({'label': route_name, 'path': str(path), **image_evidence(path)})
                        result['content'][route_name] = page.locator('body').inner_text(timeout=budget())[:24000]
            finally:
                browser.close()
    except ImportError:
        result['errors'].append('playwright_missing: install backend/requirements-review.txt')
    except Exception as exc:
        # Raw browser messages can include URLs or local environment details.
        result['errors'].append(f'{stage}_failed:{type(exc).__name__}')
    result['checks']['no_page_errors'] = not page_errors
    result['checks']['no_render_errors'] = not render_errors
    result['checks']['no_failed_requests'] = not result['failed_requests']
    result['page_errors'] = page_errors
    if page_errors:
        result['errors'].append('browser_page_error')
    if render_errors:
        result['errors'].append('browser_render_error')
    if result['failed_requests']:
        result['errors'].append('browser_resource_failed')
    result['elapsed_seconds'] = round(time.monotonic() - start, 3)
    result['checks']['passed'] = capture_checks_passed(result['checks'], result['errors'])
    result['ok'] = result['checks']['passed']
    report_path = output / 'capture.json'
    result['report_path'] = str(report_path)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case_id')
    parser.add_argument('output_dir')
    parser.add_argument('--base-url', default='http://127.0.0.1:5173')
    parser.add_argument('--expected-slug')
    parser.add_argument('--skip-content', action='store_true')
    args = parser.parse_args()
    evidence = capture_world(args.case_id, args.output_dir, args.base_url,
                             expected_slug=args.expected_slug, include_content=not args.skip_content)
    print(json.dumps({'ok': evidence['ok'], 'checks': evidence['checks'],
                      'errors': evidence['errors'], 'report_path': evidence['report_path']}, ensure_ascii=False))
    raise SystemExit(0 if evidence['ok'] else 1)
