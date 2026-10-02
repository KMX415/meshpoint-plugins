const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function panel(kind, fetch) {
    const window = { meshpointReadOnly: false, registerPageHook(hook) { this.hook = hook; } };
    const context = { window, fetch, console, localStorage: { getItem() { return null; } },
        setInterval, clearInterval, setTimeout, clearTimeout };
    vm.createContext(context);
    const files = { pager: 'rtlsdr/frontend/pager_panel.js', adsb: 'adsb/frontend/adsb_panel.js', dab: 'dab/frontend/dab_panel.js' };
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../apps', files[kind]), 'utf8'), context);
    const instance = kind === 'pager' ? new window.PagerPanel('rtl433', 'Sensors', '/api/rtl433') : window.hook.make();
    instance._refresh = () => {};
    instance._showError = () => {};
    instance._setStatus = () => {};
    return { instance, window };
}

for (const kind of ['pager', 'adsb', 'dab']) {
    test(`${kind}: saves boolean, restores failed toggle, and rejects Viewer changes`, async () => {
        let requests = [];
        let ok = true;
        const { instance, window } = panel(kind, async (url, options) => {
            requests.push({ url, options });
            return { ok, status: 403, json: async () => ({ detail: 'denied' }) };
        });
        const box = { checked: true, disabled: false };
        await instance._setKeepRunning(box);
        assert.equal(requests.length, 1);
        assert.equal(requests[0].options.method, 'PUT');
        assert.deepEqual(JSON.parse(requests[0].options.body), { keep_running: true });
        assert.equal(box.disabled, false);
        ok = false;
        box.checked = false;
        await instance._setKeepRunning(box);
        assert.equal(box.checked, true);
        window.meshpointReadOnly = true;
        await instance._setKeepRunning(box);
        assert.equal(requests.length, 2);
    });
}
