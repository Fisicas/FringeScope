"""Browser regression checks; requires Playwright and an installed Chrome/Edge.

python web/tools/check_browser_repairs.py --browser-exe PATH --output QA_DIRECTORY
Run web/build_web.py first. This serves only localhost, downloads the pinned
Pyodide runtime, and never deploys. Test inspection hooks are added to browser
responses only; production files are not modified.
"""
from pathlib import Path
import argparse,http.server,threading,json,zipfile,time,traceback
from playwright.sync_api import sync_playwright


def main():
    p=argparse.ArgumentParser();p.add_argument('--browser-exe',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    qa=args.output.resolve();qa.mkdir(parents=True,exist_ok=True);site=Path(__file__).resolve().parents[1]/'site'
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):super().__init__(*a,directory=str(site),**kw)
        def translate_path(self,path):
            if path.startswith('/FringeScope/'):path=path[len('/FringeScope'):]
            return super().translate_path(path)
        def log_message(self,*a):pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{server.server_port}/FringeScope/';record={'status':'running','checks':[],'errors':[]}
    def exported(download,name):
        path=qa/name;download.save_as(str(path))
        with zipfile.ZipFile(path) as z:
            settings=json.loads(z.read(next(n for n in z.namelist() if n.endswith('settings_and_provenance.json'))))
            analysis=json.loads(z.read(next(n for n in z.namelist() if n.endswith('analysis_settings.json'))))
            return settings['settings'],analysis,len([n for n in z.namelist() if '/screen_' in n])
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=str(args.browser_exe),headless=True);record['browser']=browser.version
            context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);page=context.new_page()
            page.on('pageerror',lambda e:record['errors'].append(str(e)))
            hook=(site/'js/explore.js').read_text(encoding='utf-8')+'\nwindow.__FS_AUDIT={state,engine,recompute,gotoTourStep,finishTour};'
            page.route('**/js/explore.js*',lambda route:route.fulfill(status=200,content_type='text/javascript',body=hook))
            page.goto(url);page.wait_for_function('window.__FS_AUDIT?.state.result&&!__FS_AUDIT.state.running',timeout=180000)
            page.evaluate("""() => {window.frames=[];const orig=Plotly.toImage;window.gate=new Promise(r=>window.release=r);Plotly.toImage=async(gd,opts)=>{frames.push({id:gd.id,wobble:__FS_AUDIT.state.meta.settings.wobble});const png=await orig(gd,opts);if(frames.length===1)await gate;return png;};}""")
            with page.expect_download(timeout=60000) as first:
                page.locator('#export-button').click();page.wait_for_function('frames.length===1')
                box=page.locator('[data-setting="wobble"]').bounding_box();page.mouse.click(box['x']+20,box['y']+20)
                page.wait_for_timeout(300)
                assert page.evaluate('__FS_AUDIT.state.controls.wobble') is False
                assert page.locator('#theme-button').is_disabled()
                page.evaluate('release()')
            settings,meta,count=exported(first.value,'locked_export.zip')
            assert not settings['wobble'] and count==4
            frames=page.evaluate('frames');assert len(frames)==4 and all(not f['wobble'] for f in frames)
            record['checks'].append({'mid_export_edit_blocked':True,'all_four_captures_match_data':True,'committed_result_id':meta['committed_result_id']})
            page.evaluate("""() => {const orig=__FS_AUDIT.engine.call.bind(__FS_AUDIT.engine);window.computeGate=new Promise(r=>window.releaseCompute=r);let once=true;__FS_AUDIT.engine.call=async(...a)=>{const result=await orig(...a);if(a[0]==='compute'&&once){once=false;window.computeHeld=true;await computeGate;}return result;};}""")
            page.locator('[data-setting="wobble"]').click();page.wait_for_function('window.computeHeld')
            with page.expect_download(timeout=60000) as second:
                page.locator('#export-button').click();page.wait_for_function('document.querySelector("#main").inert')
                page.evaluate('releaseCompute()')
            settings,meta,count=exported(second.value,'pending_calculation_export.zip')
            assert settings['wobble'] and count==4
            assert all(f['wobble'] for f in page.evaluate('frames.slice(4)'))
            record['checks'].append({'export_waits_for_pending_calculation':True,'all_four_captures_match_data':True,'committed_result_id':meta['committed_result_id']})
            page.evaluate('async()=>{await __FS_AUDIT.recompute(true);window.savedFit=JSON.stringify({mode:__FS_AUDIT.state.meta.fit_mode,taus:__FS_AUDIT.state.meta.taus,das:Array.from(__FS_AUDIT.state.result.das.data)});}')
            page.evaluate('async()=>{await __FS_AUDIT.gotoTourStep(0);await __FS_AUDIT.gotoTourStep(3);await __FS_AUDIT.finishTour(false);}')
            assert page.evaluate('JSON.stringify({mode:__FS_AUDIT.state.meta.fit_mode,taus:__FS_AUDIT.state.meta.taus,das:Array.from(__FS_AUDIT.state.result.das.data)})===savedFit')
            with page.expect_download(timeout=60000) as third:page.locator('#export-button').click()
            settings,meta,count=exported(third.value,'restored_free_fit_export.zip');assert meta['fit_mode'].startswith('free')
            record['checks'].append({'tour_restores_exact_free_fit_and_worker_export':True})
            page.screenshot(path=str(qa/'desktop.png'),full_page=True)
            phone=browser.new_context(viewport={'width':375,'height':812},is_mobile=True,has_touch=True,device_scale_factor=1)
            mobile=phone.new_page();mobile.goto(url+'theory.html',wait_until='networkidle')
            dims=mobile.evaluate('({client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth})');assert dims['scroll']<=dims['client']
            record['checks'].append({'phone_theory_no_overflow':dims});mobile.screenshot(path=str(qa/'phone_theory.png'),full_page=False)
            parity=context.new_page();parity.goto(url+'validate.html');parity.locator('#run').click();parity.wait_for_function('window.FRINGESCOPE_PARITY',timeout=180000)
            record['parity']=parity.evaluate('FRINGESCOPE_PARITY');assert record['parity']['passed']==record['parity']['total']==20
            assert not record['errors'];record['status']='passed';browser.close()
    except Exception:record['exception']=traceback.format_exc();raise
    finally:
        server.shutdown();server.server_close();(qa/'checks.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record,indent=2))


if __name__=='__main__':main()
