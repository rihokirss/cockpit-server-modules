/* global cockpit */
const $ = id => document.getElementById(id);
let sites = [];
let routes = [];
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
    <td><button class="btn health" data-id="${esc(site.id)}">Testi</button> <button class="btn edit" data-id="${esc(site.id)}">Muuda</button> <button class="btn danger del" data-id="${esc(site.id)}">Kustuta</button></td>
  </tr>`).join('');
  document.querySelectorAll('.edit').forEach(button => button.onclick = () => openEditor(button.dataset.id));
  document.querySelectorAll('.del').forEach(button => button.onclick = () => removeSite(button.dataset.id));
  document.querySelectorAll('.health').forEach(button => button.onclick = () => health(button.dataset.id));
  $('routes-empty').classList.toggle('hidden', routes.length > 0);
  $('routes').innerHTML = routes.map(route => `<tr>
    <td><strong>${esc(route.domain)}${esc(route.path)}/</strong>${route.enabled ? '' : ' <span class="pill">väljas</span>'}<small class="route-url">${route.https ? 'HTTPS' : 'HTTP'} · port ${route.https_port || 443}</small></td>
    <td>${esc(route.scheme)}://${esc(route.host)}:${route.port}</td>
    <td>${route.strip_prefix ? '<span class="pill yes">eemaldatakse</span>' : '<span class="pill">säilitatakse</span>'}</td>
    <td>${route.websocket ? '<span class="pill yes">jah</span>' : 'ei'}</td>
    <td><button class="btn route-health" data-id="${esc(route.id)}">Testi</button> <button class="btn route-edit" data-id="${esc(route.id)}">Muuda</button> <button class="btn danger route-delete" data-id="${esc(route.id)}">Kustuta</button></td>
  </tr>`).join('');
  document.querySelectorAll('.route-edit').forEach(button => button.onclick = () => openRouteEditor(button.dataset.id));
  document.querySelectorAll('.route-delete').forEach(button => button.onclick = () => removeRoute(button.dataset.id));
  document.querySelectorAll('.route-health').forEach(button => button.onclick = () => routeHealth(button.dataset.id));
}
async function refresh() {
  try {
    const result = await api('list'); sites = result.sites || []; routes = result.routes || []; certificates = result.certificates || []; render();
    $('status').textContent = result.active ? 'Nginx töötab' : 'Nginx ei tööta';
    $('status').className = 'badge ' + (result.active ? 'ok' : 'bad');
  } catch (error) { notice(error.message, true); $('status').textContent='Viga'; $('status').className='badge bad'; }
}
async function refreshLogs() { try { $('logs').textContent=(await api('logs')).logs || 'Logi on tühi.'; } catch (error) { $('logs').textContent=error.message; } }
function openEditor(id='') {
  const site=sites.find(item => item.id === id) || {id:'',scheme:'http',host:'',port:80,https_port:443,certificate:'',websocket:true,enabled:true};
  $('form-title').textContent=id ? 'Muuda teenust' : 'Lisa teenus'; $('site-id').value=site.id || '';
  ['domain','scheme','host','port'].forEach(key => $(key).value=site[key] || ''); $('https-port').value=site.https_port || 443;
  $('certificate').innerHTML='<option value="">Ilma HTTPS-ita</option>' + certificates.map(cert => `<option value="${esc(cert.name)}">${esc(cert.name)}</option>`).join('');
  $('certificate').value=site.certificate || ''; $('websocket').checked=site.websocket; $('enabled').checked=site.enabled; $('editor').showModal();
}
function openRouteEditor(id='') {
  const route=routes.find(item => item.id === id) || {id:'',domain:'',path:'',scheme:'http',host:'127.0.0.1',port:'',https_port:443,certificate:'',description:'',strip_prefix:true,websocket:true,enabled:true};
  $('route-title').textContent=id ? 'Muuda alamrada' : 'Lisa alamrada'; $('route-original-id').value=id; $('route-id').value=route.id || '';
  $('route-domain').value=route.domain; $('route-path').value=route.path; $('route-scheme').value=route.scheme; $('route-host').value=route.host; $('route-port').value=route.port; $('route-https-port').value=route.https_port || 443; $('route-description').value=route.description || '';
  $('route-certificate').innerHTML='<option value="">Automaatne või HTTP</option>' + certificates.map(cert => `<option value="${esc(cert.name)}">${esc(cert.name)} · ${esc((cert.domains||[]).join(', '))}</option>`).join('');
  $('route-certificate').value=route.certificate || ''; $('route-strip').checked=route.strip_prefix; $('route-websocket').checked=route.websocket; $('route-enabled').checked=route.enabled; $('route-editor').showModal();
}
async function removeSite(id) { const site=sites.find(item=>item.id===id); if (!site || !confirm(`Kustutada ${site.domain}:${site.https_port || 443}?`)) return; try { await api('delete',{id}); notice('Teenus kustutatud.'); await refresh(); } catch(error) { notice(error.message,true); } }
async function health(id) { const site=sites.find(item=>item.id===id); try { const result=await api('health',{id}); notice(`${site.domain}:${site.https_port || 443}: siht vastas HTTP ${result.code} (${result.time_ms} ms)`); } catch(error) { notice(`${site?.domain || 'Teenus'}: ${error.message}`,true); } }
async function removeRoute(id) { const route=routes.find(item=>item.id===id); if (!route || !confirm(`Kustutada ${route.domain}${route.path}/ marsruut?`)) return; try { await api('route_delete',{id}); notice('Alamraja marsruut kustutatud.'); await refresh(); } catch(error) { notice(error.message,true); } }
async function routeHealth(id) { const route=routes.find(item=>item.id===id); try { const result=await api('route_health',{id}); notice(`${route.domain}${route.path}/: siht vastas HTTP ${result.code} (${result.time_ms} ms)`); } catch(error) { notice(`${route?.domain || 'Marsruut'}: ${error.message}`,true); } }

$('site-form').onsubmit=async event => {
  event.preventDefault();
  const site={id:$('site-id').value,domain:$('domain').value.trim().toLowerCase(),scheme:$('scheme').value,host:$('host').value.trim(),port:Number($('port').value),https_port:Number($('https-port').value),certificate:$('certificate').value,websocket:$('websocket').checked,enabled:$('enabled').checked};
  try { await api('save',{original_id:$('site-id').value,site}); $('editor').close(); notice('Konfiguratsioon salvestatud ja nginx uuesti laaditud.'); await refresh(); } catch(error) { notice(error.message,true); }
};
$('route-form').onsubmit=async event => {
  event.preventDefault();
  const route={id:$('route-id').value,domain:$('route-domain').value.trim().toLowerCase(),path:$('route-path').value.trim().toLowerCase(),scheme:$('route-scheme').value,host:$('route-host').value.trim(),port:Number($('route-port').value),https_port:Number($('route-https-port').value),certificate:$('route-certificate').value,description:$('route-description').value.trim(),strip_prefix:$('route-strip').checked,websocket:$('route-websocket').checked,enabled:$('route-enabled').checked};
  try { await api('route_save',{original_id:$('route-original-id').value,route}); $('route-editor').close(); notice('Alamraja marsruut salvestatud ja Nginx uuesti laaditud.'); await refresh(); } catch(error) { notice(error.message,true); }
};
$('add').onclick=()=>openEditor(); $('cancel').onclick=()=>$('editor').close();
$('route-add').onclick=()=>openRouteEditor(); $('route-cancel').onclick=()=>$('route-editor').close();
$('manage-certificates').onclick=()=>cockpit.jump('/certificates');
$('test').onclick=async()=>{try{notice((await api('test')).message)}catch(error){notice(error.message,true)}};
$('reload').onclick=async()=>{try{await api('reload');notice('Nginx laaditi uuesti.');await refresh()}catch(error){notice(error.message,true)}};
$('logs-refresh').onclick=refreshLogs;
refresh(); refreshLogs();
