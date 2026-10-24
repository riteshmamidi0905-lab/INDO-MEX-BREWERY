"""Real Chromium interaction checks. Uses existing local fixtures and a running host.
No credentials are printed, embedded in screenshots, or stored in reports.
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(port,code_file,out):
    output=Path(out);output.mkdir(parents=True,exist_ok=True)
    code=Path(code_file).read_text().strip()
    base=f'http://127.0.0.1:{port}'
    issues=[];visited=[];axe=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':1440,'height':1100},reduced_motion='reduce')
        page=context.new_page()
        page.on('pageerror',lambda error:issues.append(str(error)))
        page.on('console',lambda msg:issues.append(msg.text) if msg.type=='error' and '401' not in msg.text else None)
        page.goto(base,wait_until='networkidle')
        assert page.locator('#access').is_visible()
        assert page.locator('#app').is_hidden()
        page.locator('#access-code').fill(code)
        page.get_by_role('button',name='Enter headquarters').click()
        page.locator('#view h1').wait_for()
        assert page.locator('#access-code').input_value()==''
        assert page.locator('#view').inner_text().find('$988,636.79')>=0
        page.screenshot(path=str(output/'headquarters-desktop.png'),full_page=True)
        routes=['headquarters','executive','engineering','data','finance','operations','product','crm','people','creation','playbook']
        for route in routes:
            page.locator(f'#navigation a[href="#/{route}"]').click()
            page.locator('#view h1').wait_for()
            page.wait_for_function("() => document.querySelector('#view').innerText.length>100")
            assert page.locator('#view h1').count()==1
            assert not page.locator('.error-state').count(),route
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'),route
            visited.append(route)
        page.locator('#navigation a[href="#/finance"]').click()
        page.locator('#record-filters').wait_for()
        page.locator('select[name="kind"]').select_option('sale')
        page.get_by_role('button',name='Apply filters').click()
        page.locator('#record-filters').wait_for()
        assert page.locator('tbody .type-badge').first.inner_text()=='sale'
        first=page.locator('.table-button').first.inner_text()
        page.get_by_role('button',name='Next',exact=True).click()
        page.locator('#record-filters').wait_for()
        assert page.locator('.table-button').first.inner_text()!=first
        page.locator('.table-button').first.click()
        assert page.get_by_role('dialog').is_visible()
        assert 'Foundation event hash' in page.locator('#dialog-content').inner_text()
        page.keyboard.press('Escape')
        with page.expect_download() as dl:
            page.get_by_role('button',name='Export this view').click()
        assert 'finance-view' in dl.value.suggested_filename
        page.screenshot(path=str(output/'finance-desktop.png'),full_page=True)
        page.locator('#business-select').select_option('meridian-fitness')
        page.wait_for_function("() => document.querySelector('#view').innerText.includes('Meridian Fitness')")
        page.locator('#record-filters').wait_for()
        assert '$988,636.79' not in page.locator('#view').inner_text()
        assert 'membership' in page.locator('tbody').last.inner_text() or 'assumption:' in page.locator('tbody').last.inner_text()
        for route in routes:
            page.locator(f'#navigation a[href="#/{route}"]').click();page.locator('#view h1').wait_for()
            assert not page.locator('.error-state').count(),route
        page.locator('#navigation a[href="#/people"]').click();page.locator('#person-search').wait_for()
        assert page.locator('.staff-card').count()==15
        page.locator('#person-search').fill('Maya')
        assert page.locator('.staff-card').count()==1
        page.get_by_role('button',name='View profile').click()
        assert 'Maya Desai' in page.locator('#dialog-content').inner_text()
        assert 'Modeled annual salary' in page.locator('#dialog-content').inner_text()
        page.keyboard.press('Escape')
        page.locator('#person-search').fill('')
        page.screenshot(path=str(output/'people-desktop.png'),full_page=True)
        page.locator('#navigation a[href="#/engineering"]').click();page.locator('.evidence-menu').wait_for()
        page.get_by_role('button',name='SQL · relational records and journals').click()
        page.wait_for_function("() => document.querySelector('pre')?.innerText.includes('CREATE TABLE')")
        assert page.get_by_role('link',name='View on GitHub').get_attribute('href').find('6c177d7')>=0
        page.locator('#navigation a[href="#/creation"]').click();page.locator('#draft-name').wait_for()
        page.locator('#draft-name').fill('Aster <img src=x onerror=alert(1)>')
        page.locator('#draft-idea').fill('A fully synthetic wellness business for testing memberships.')
        page.get_by_role('button',name='Continue').click()
        page.locator('#draft-audience').fill('Fictional local members')
        page.locator('#draft-model').fill('Monthly memberships')
        page.locator('#draft-goal').fill('Explore modeled retention and operating costs.')
        page.get_by_role('button',name='Continue').click()
        assert page.locator('#blueprint-form img').count()==0
        assert 'Aster <img' in page.locator('#blueprint-form h2').inner_text()
        with page.expect_download() as dl:
            page.get_by_role('button',name='Export blueprint').click()
        exported=json.loads(Path(dl.value.path()).read_text())
        assert exported['status']=='LOCAL_DRAFT_NOT_PROVISIONED' and exported['synthetic']
        page.screenshot(path=str(output/'blueprint-desktop.png'),full_page=True)
        page.locator('#business-select').select_option('nasha-brewery')
        page.wait_for_function("() => document.querySelector('#view').innerText.includes('NASHA Brewery')")
        page.locator('#navigation a[href="#/headquarters"]').click();page.locator('.hero').wait_for()
        # Audit via debugger evaluation, without relaxing the app's production CSP.
        axe_file=Path('/workspace/INDO-MEX-BREWERY/website/qa/node_modules/axe-core/axe.min.js')
        if not axe_file.is_file(): raise RuntimeError('axe-core is required for this audit; install the existing website/qa lockfile dependencies')
        if axe_file.exists():
            for route in ['headquarters','finance','people','creation','engineering']:
                page.locator(f'#navigation a[href="#/{route}"]').click();page.locator('#view h1').wait_for()
                page.evaluate(axe_file.read_text())
                audit=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary})).slice(0,8)}))}")
                axe.append({'route':route,'violations':audit})
        # Small screen: nav toggle, finance, profiles, reflow and reduced motion.
        page.set_viewport_size({'width':390,'height':844})
        for route in ('headquarters','finance','people','engineering','creation'):
            page.get_by_role('button',name='Toggle department navigation').click()
            page.locator(f'#navigation a[href="#/{route}"]').click();page.locator('#view h1').wait_for()
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'),route
            assert page.locator('#menu-toggle').get_attribute('aria-expanded')=='false'
            if route=='headquarters':page.screenshot(path=str(output/'headquarters-mobile.png'),full_page=True)
        assert page.evaluate("matchMedia('(prefers-reduced-motion:reduce)').matches")
        # Keyboard command menu and logout boundary.
        page.set_viewport_size({'width':1440,'height':1000})
        page.keyboard.press('Control+k');page.locator('#department-search').fill('finance')
        page.locator('#search-results a').first.click();page.locator('#record-filters').wait_for()
        page.get_by_role('button',name='Sign out',exact=True).click()
        page.locator('#access-code').wait_for(state='visible')
        assert page.locator('#app').is_hidden()
        browser.close()
    report={'desktop_departments':visited,'businesses_checked':2,'mobile_width':390,'interaction_checks':['sign-in','navigation','business isolation','finance filters','pagination','provenance dialog','financial export','employee search and profile','immutable source evidence','blueprint steps and export','HTML injection rendered as text','mobile navigation and reflow','reduced motion','keyboard search','logout'],'page_errors':issues,'axe':axe,'axe_violations':sum(len(r['violations']) for r in axe)}
    (output/'browser-results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'departments':len(visited),'businesses':2,'page_errors':len(issues),'axe_violations':report['axe_violations']}))
    assert not issues,issues
    assert not report['axe_violations'],report['axe']

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8765);p.add_argument('--code-file',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();run(a.port,a.code_file,a.out)
