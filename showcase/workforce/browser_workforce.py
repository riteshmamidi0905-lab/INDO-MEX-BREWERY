"""Chromium end-to-end governed workflow validation; never logs access/session secrets."""
import argparse
import json
from pathlib import Path
import uuid
from playwright.sync_api import sync_playwright


def run(port,code_file,out):
    output=Path(out);output.mkdir(parents=True,exist_ok=True)
    base=f'http://127.0.0.1:{port}'
    results={'mode':'DETERMINISTIC_REPLAY','live_model':False,'checks':[],'errors':[],'axe':[]}
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':1440,'height':1100},reduced_motion='reduce')
        page=context.new_page()
        page.on('pageerror',lambda e:results['errors'].append(str(e)))
        page.goto(base,wait_until='networkidle')
        page.locator('#access-code').fill(Path(code_file).read_text().strip())
        page.get_by_role('button',name='Enter headquarters').click();page.locator('.hero').wait_for()
        page.locator('#navigation a[href="#/operations"]').click()
        page.locator('#workflow-start').wait_for()
        def begin(scenario,expected):
            page.locator('#workflow-scenario').select_option(scenario)
            page.get_by_role('button',name='Start authorized workflow',exact=True).click()
            page.wait_for_function('(text)=>document.querySelector(".workflow-status")?.innerText.includes(text)',arg=expected)
            assert page.locator('.workflow-status').inner_text().find(expected)>=0
        begin('count-gap','Pending human approval')
        assert page.locator('.workflow-agent').count()==3
        assert page.locator('.workflow-agent').filter(has_text='Recorded deterministic result').count()==3
        assert '$280.00' in page.locator('.workflow-finance').inner_text()
        assert 'REVIEW_REQUIRED' in page.locator('.workflow-finance').inner_text()
        assert not page.locator('#workflow-area').get_by_text('Simulated action recorded',exact=True).count()
        page.screenshot(path=str(output/'phase4-pending-approval.png'),full_page=True)
        pending_id=page.locator('.workflow-status .hash').inner_text().split(' · ')[0]
        page.locator('[data-wf="agent"][data-agent="amara"]').click()
        assert 'discrepancy' in page.locator('#dialog-content').inner_text()
        assert 'tool_call' in page.locator('#dialog-content').inner_text()
        page.screenshot(path=str(output/'phase4-agent-workspace.png'),full_page=True)
        page.keyboard.press('Escape')
        page.get_by_role('button',name='Approve simulated draft',exact=True).click()
        page.wait_for_function('()=>document.querySelector(".workflow-status")?.innerText.includes("Approved simulated execution")')
        assert 'DRAFT_NOT_SENT' in page.locator('#workflow-area').inner_text()
        assert page.get_by_role('button',name='Approve simulated draft').is_disabled()
        page.screenshot(path=str(output/'phase4-approved-simulation.png'),full_page=True)
        results['checks'].append('Real role-bound tools -> WEIR hold -> authenticated approval -> one simulated draft')
        begin('count-gap','Pending human approval')
        page.get_by_role('button',name='Reject proposed action').click()
        page.wait_for_function('()=>document.querySelector(".workflow-status")?.innerText.includes("Rejected execution")')
        assert not page.locator('#workflow-area').get_by_text('Simulated action recorded',exact=True).count()
        results['checks'].append('Human rejection creates no draft')
        begin('budget-risk','Blocked by finance')
        assert not page.get_by_role('button',name='Approve simulated draft').count()
        results['checks'].append('Finance budget gate blocks approval')
        begin('missing-count','Failed execution')
        assert 'Recorded error:' in page.locator('#workflow-area').inner_text()
        results['checks'].append('Missing inventory data fails closed')
        begin('no-gap','No replenishment required')
        assert page.locator('.workflow-agent').filter(has_text='Not executed in this run').count()==2
        results['checks'].append('Balanced count abstains without fictional downstream activity')
        page.locator('#business-select').select_option('meridian-fitness')
        page.wait_for_function('()=>document.querySelector("#view")?.innerText.includes("Meridian Fitness")')
        page.locator('#workflow-start').wait_for()
        assert 'No workflow selected.' in page.locator('#workflow-area').inner_text()
        assert page.locator('#workflow-history option').count()==1
        response=page.request.get(base+'/api/workflows?run='+pending_id)
        assert response.status==401
        begin('count-gap','Pending human approval')
        assert 'meridian-fitness' in page.locator('.workflow-status').inner_text()
        page.get_by_role('button',name='Approve simulated draft',exact=True).click()
        page.wait_for_function('()=>document.querySelector(".workflow-status")?.innerText.includes("Approved simulated execution")')
        results['checks'].append('Separate Meridian workflow and refusal of NASHA run access')
        # Actual automated accessibility audit; CSP remains enabled.
        axe=Path('/workspace/INDO-MEX-BREWERY/website/qa/node_modules/axe-core/axe.min.js')
        assert axe.is_file(),'Existing axe-core is required'
        page.evaluate(axe.read_text())
        violations=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}});return r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary})).slice(0,5)}))}")
        results['axe']=violations
        assert not violations,violations
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('()=>document.documentElement.scrollWidth<=window.innerWidth')
        page.screenshot(path=str(output/'phase4-workforce-mobile.png'),full_page=True)
        results['checks'].append('Workflow mobile reflow and zero automated WCAG violations')
        # Logout erases the in-memory workflow as well as the visible DOM.
        page.get_by_role('button',name='Sign out',exact=True).click();page.locator('#access').wait_for(state='visible')
        page.locator('#access-code').fill(Path(code_file).read_text().strip())
        page.get_by_role('button',name='Enter headquarters').click();page.locator('#workflow-start').wait_for()
        assert 'No workflow selected.' in page.locator('#workflow-area').inner_text()
        assert page.locator('#workflow-history option').count()==1
        results['checks'].append('New authenticated session cannot inherit previous reviewer workflows')
        browser.close()
    assert not results['errors'],results['errors']
    (output/'workforce-browser-results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps({'checks':len(results['checks']),'page_errors':len(results['errors']),'axe_violations':len(results['axe']),'mode':results['mode']}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8767);p.add_argument('--code-file',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();run(a.port,a.code_file,a.out)
