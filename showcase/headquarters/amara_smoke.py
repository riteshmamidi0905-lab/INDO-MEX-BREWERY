"""Local browser validation only; no provider calls or business effects."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(base, code_file, out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    errors=[];audits=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1100},reduced_motion='reduce')
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(base)
        page.locator('#access-code').fill(Path(code_file).read_text().strip())
        page.get_by_role('button',name='Enter headquarters').click()
        page.locator('#view h1').wait_for()
        page.screenshot(path=str(out/'headquarters.png'),full_page=True)
        page.locator('#navigation a[href="#/operations"]').click()
        page.locator('#inventory-scenario').wait_for()
        assert 'shortfall of 60 units' in page.locator('.amara-answer').inner_text()
        page.get_by_text('Inspect supporting records (2)',exact=True).click()
        page.get_by_text('Inspect actual read activity',exact=True).click()
        assert 'showcase__read' in page.locator('.amara-governance').inner_text()
        page.screenshot(path=str(out/'amara-desktop.png'),full_page=True)
        axe=Path('/workspace/INDO-MEX-BREWERY/website/qa/node_modules/axe-core/axe.min.js')
        def audit(label):
            page.evaluate(axe.read_text())
            violations=page.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))")
            audits.append(dict(view=label,violations=violations))
        audit('desktop-expanded-evidence')
        for scenario,expected in [('budget-risk','shortfall of 80'),('no-gap','no discrepancy'),('missing-count','counted quantity is missing')]:
            page.locator('#inventory-scenario').select_option(scenario)
            page.wait_for_function('(text)=>document.querySelector(".amara-answer")?.innerText.includes(text)',arg=expected)
        page.screenshot(path=str(out/'amara-missing-count.png'),full_page=True)
        page.locator('#business-select').select_option('meridian-fitness')
        page.wait_for_function('()=>document.querySelector(".amara-body")?.innerText.includes("Meridian Fitness")')
        assert 'shortfall of 60' in page.locator('.amara-answer').inner_text()
        page.get_by_text('Inspect supporting records (2)',exact=True).click()
        assert 'meridian-fitness:count-gap' in page.locator('.amara-body').inner_text()
        assert 'nasha-brewery:count-gap' not in page.locator('.amara-body').inner_text()
        page.screenshot(path=str(out/'amara-meridian.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        audit('mobile-meridian')
        page.screenshot(path=str(out/'amara-mobile.png'),full_page=True)
        page.route('**/api/view/operations*',lambda r:r.fulfill(status=503,content_type='application/json',body=json.dumps({'error':'Source unavailable; no data was substituted'})))
        page.locator('#inventory-scenario').select_option('no-gap')
        page.locator('.error-state').wait_for()
        assert page.locator('.amara-answer').count()==0
        page.screenshot(path=str(out/'amara-unavailable.png'),full_page=True)
        page.unroute('**/api/view/operations*')
        page.get_by_role('button',name='Try again',exact=True).click()
        page.locator('#inventory-scenario').wait_for()
        assert 'no discrepancy' in page.locator('.amara-answer').inner_text()
        page.locator('#inventory-scenario').focus();page.keyboard.press('ArrowUp');page.keyboard.press('Tab')
        assert page.evaluate('document.activeElement.tagName')!='BODY'
        browser.close()
    result={'checks':['authenticated headquarters entry','scenario arithmetic','supporting evidence','actual gateway reads','missing-count abstention','balanced count','business switch and isolation','mobile reflow','reduced motion','keyboard focus','source failure and retry'],'page_errors':errors,'accessibility':audits,'screenshots':6}
    (out/'browser-results.json').write_text(json.dumps(result,indent=2)+'\n')
    assert not errors,errors
    assert not any(a['violations'] for a in audits),audits
    print('Browser checks passed; 6 screenshots; zero page errors and accessibility violations.')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--code-file',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();run(a.base,a.code_file,a.out)
