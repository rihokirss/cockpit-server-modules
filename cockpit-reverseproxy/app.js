/* global cockpit */
const $ = id => document.getElementById(id);
let sites = [];
let certificates = [];

async function api(action, payload = {}) {
  const process = cockpit.spawn(['/usr/local/libexec/cockpit-reverseproxy-helper'], { superuser: 'require', err: 'message' });
  process.input(JSON.stringify({ action, ...payload }));
  const out = await process;
  const result = JSON.parse(out || '{}');
  if (result.error) throw new Error(result.error);
  return result;
}
function notice(text, error = false) {
  $('message').textContent = text;
  $('message').className = 'message' + (error ? ' error' : '');
  setTimeout(() => $('message').classList.add('hidden'), 6000);
}
function esc(value) { const node=document.createElement('div'); node.textContent=value ?? ''; return node.innerHTML; }

function render() {
  $('empty').classList.toggle('hidden', sites.length > 0);
  $('sites').innerHTML = sites.map(site => `<tr>
    <td><strong>${esc(site.domain)}</strong>${site.enabled ? '' : ' <span class="pill">väljas</span>'}</td>
    <td>${esc(site.scheme)}://${esc(site.host)}:${site.port}</td>
    <td>${site.https ? `<span class="pill yes" title="Kehtib kuni ${esc(site.cert_expiry || '')}">port ${site.https_port || 443}</span><small class="cert-name">${esc(site.certificate)}</small>` : '<span class="pill">HTTP</span>'}</td>
    <td>${site.websocket ? '<span class="pill yes">jah</span>' : 'ei'}</td>
    <td><button class="btn health" data-domain="${esc(site.domain)}">Testi</button> <button class="btn edit" data-domain="${esc(site.domain)}">Muuda</button> <button class="btn danger del" data-domain="${esc(site.domain)}">Kustuta</button></td>
  </tr>`).join('');
  document.querySelectorAll('.edit').forEach(button => button.onclick = () => openEditor(button.dataset.domain));
  document.querySelectorAll('.del').forEach(button => button.onclick = () => removeSite(button.dataset.domain));
  document.querySelectorAll('.health').forEach(button => button.onclick = () => health(button.dataset.domain));
}
async function refresh() {
  try {
    const result = await api('list'); sites = result.sites || []; certificates = result.certificates || []; render();
    $('status').textContent = result.active ? 'Nginx töötab' : 'Nginx ei tööta';
    $('status').className = 'badge ' + (result.active ? 'ok' : 'bad');
  } catch (error) { notice(error.message, true); $('status').textContent='Viga'; $('status').className='badge bad'; }
}
async function refreshLogs() { try { $('logs').textContent=(await api('logs')).logs || 'Logi on tühi.'; } catch (error) { $('logs').textContent=error.message; } }
function openEditor(domain='') {
  const site=sites.find(item => item.domain === domain) || {scheme:'http',host:'',port:80,https_port:443,certificate:'',websocket:true,enabled:true};
  $('form-title').textContent=domain ? 'Muuda teenust' : 'Lisa teenus'; $('original-domain').value=domain;
  ['domain','scheme','host','port'].forEach(key => $(key).value=site[key] || ''); $('https-port').value=site.https_port || 443;
  $('certificate').innerHTML='<option value="">Ilma HTTPS-ita</option>' + certificates.map(cert => `<option value="${esc(cert.name)}">${esc(cert.name)}</option>`).join('');
  $('certificate').value=site.certificate || ''; $('websocket').checked=site.websocket; $('enabled').checked=site.enabled; $('editor').showModal();
}
async function removeSite(domain) { if (!confirm(`Kustutada ${domain}?`)) return; try { await api('delete',{domain}); notice('Teenus kustutatud.'); await refresh(); } catch(error) { notice(error.message,true); } }
async function health(domain) { try { const result=await api('health',{domain}); notice(`${domain}: siht vastas HTTP ${result.code} (${result.time_ms} ms)`); } catch(error) { notice(`${domain}: ${error.message}`,true); } }

$('site-form').onsubmit=async event => {
  event.preventDefault();
  const site={domain:$('domain').value.trim().toLowerCase(),scheme:$('scheme').value,host:$('host').value.trim(),port:Number($('port').value),https_port:Number($('https-port').value),certificate:$('certificate').value,websocket:$('websocket').checked,enabled:$('enabled').checked};
  try { await api('save',{original_domain:$('original-domain').value,site}); $('editor').close(); notice('Konfiguratsioon salvestatud ja nginx uuesti laaditud.'); await refresh(); } catch(error) { notice(error.message,true); }
};
$('add').onclick=()=>openEditor(); $('cancel').onclick=()=>$('editor').close();
$('manage-certificates').onclick=()=>cockpit.jump('/certificates');
$('test').onclick=async()=>{try{notice((await api('test')).message)}catch(error){notice(error.message,true)}};
$('reload').onclick=async()=>{try{await api('reload');notice('Nginx laaditi uuesti.');await refresh()}catch(error){notice(error.message,true)}};
$('logs-refresh').onclick=refreshLogs;
refresh(); refreshLogs();
