/* global cockpit */
const $ = id => document.getElementById(id);
let certificates = [];
let synology = {};
let issueDomains = [];

async function api(action, payload = {}) {
  const process = cockpit.spawn(['/usr/local/libexec/cockpit-certificates-helper'], { superuser: 'require', err: 'message' });
  process.input(JSON.stringify({ action, ...payload }));
  const output = await process;
  const result = JSON.parse(output || '{}');
  if (result.error) throw new Error(result.error);
  return result;
}

function esc(value) { const node = document.createElement('div'); node.textContent = value ?? ''; return node.innerHTML; }
function formatDate(value) {
  if (!value) return 'teadmata';
  const date = new Date(value);
  return new Intl.DateTimeFormat('et-EE', { day:'numeric', month:'long', year:'numeric' }).format(date);
}
function formatDateTime(value) {
  if (!value) return 'pole veel edastatud';
  return new Intl.DateTimeFormat('et-EE', { dateStyle:'medium', timeStyle:'short' }).format(new Date(value));
}
function notice(text, error = false) {
  $('message').textContent = text;
  $('message').className = 'message' + (error ? ' error' : '');
  clearTimeout(notice.timer);
  notice.timer = setTimeout(() => $('message').classList.add('hidden'), 7000);
}
function setBusy(button, busy, label = 'Töötan…') {
  if (busy) { button.dataset.label = button.textContent; button.textContent = label; button.disabled = true; }
  else { button.textContent = button.dataset.label || button.textContent; button.disabled = false; }
}

function statusFor(cert) {
  if (cert.days_left == null) return ['neutral', 'Teadmata'];
  if (cert.days_left < 0) return ['bad', 'Aegunud'];
  if (cert.days_left < 21) return ['warn', `${cert.days_left} päeva`];
  return ['good', `${cert.days_left} päeva`];
}

function renderCertificates() {
  $('empty').classList.toggle('hidden', certificates.length > 0);
  $('certificates').innerHTML = certificates.map(cert => {
    const [tone, days] = statusFor(cert);
    const deployment = cert.synology || {};
    const deployState = deployment.enabled
      ? (deployment.last_status === 'error' ? '<span class="state bad">Edastusviga</span>' : '<span class="state good">Synology automaatne</span>')
      : '<span class="state neutral">Ainult selles serveris</span>';
    return `<article class="certificate-row">
      <div class="cert-icon ${tone}">▣</div>
      <div class="cert-main"><div class="cert-title"><strong>${esc(cert.name)}</strong><span class="state ${tone}">${esc(days)}</span>${deployState}</div>
        <div class="domains">${cert.domains.map(domain => `<span>${esc(domain)}</span>`).join('')}</div>
        <div class="cert-meta"><span>Kehtib kuni <strong>${esc(formatDate(cert.expiry_iso))}</strong></span>${cert.in_use_by.length ? `<span>Reverse Proxy: ${esc(cert.in_use_by.join(', '))}</span>` : ''}${deployment.enabled ? `<span title="${esc(deployment.last_message || '')}">DSM: ${esc(formatDateTime(deployment.last_deployed))}</span>` : ''}</div>
      </div>
      <div class="row-actions"><button class="btn deploy-config" data-name="${esc(cert.name)}">Synology</button><button class="btn edit-domains" data-name="${esc(cert.name)}">Domeenid</button><button class="btn renew" data-name="${esc(cert.name)}">Uuenda</button><button class="btn danger delete" data-name="${esc(cert.name)}">Kustuta</button></div>
    </article>`;
  }).join('');
  document.querySelectorAll('.deploy-config').forEach(button => button.onclick = () => openDeployment(button.dataset.name));
  document.querySelectorAll('.edit-domains').forEach(button => button.onclick = () => openIssue(button.dataset.name));
  document.querySelectorAll('.renew').forEach(button => button.onclick = () => renew(button));
  document.querySelectorAll('.delete').forEach(button => button.onclick = () => removeCertificate(button.dataset.name));
}

function renderSummary(result) {
  const valid = certificates.filter(cert => cert.days_left >= 0).length;
  $('valid-count').textContent = String(valid);
  $('renewal-summary').textContent = result.timer.enabled && result.timer.active ? 'aktiivne' : 'väljas';
  $('deploy-count').textContent = String(certificates.filter(cert => cert.synology?.enabled).length);
  $('renewal-toggle').checked = result.timer.enabled;
  $('next-run').textContent = result.timer.enabled ? `Järgmine kontroll: ${result.timer.next_run ? formatDateTime(result.timer.next_run) : 'ajakava järgi'}` : 'Automaatne kontroll on peatatud';
  $('status').textContent = result.nginx_active ? 'Süsteem töötab' : 'Nginx ei tööta';
  $('status').className = 'badge ' + (result.nginx_active ? 'ok' : 'bad');
  $('synology-summary').textContent = synology.username ? `${synology.username} @ ${synology.host}:${synology.port}` : `${synology.host || 'seadistamata'} — sisesta konto`;
  $('synology-state').className = 'dot ' + (synology.password_set && synology.username ? 'good' : 'neutral');
}

async function refresh() {
  try {
    const result = await api('list');
    certificates = result.certificates || [];
    synology = result.synology || {};
    renderCertificates(); renderSummary(result);
  } catch (error) {
    notice(error.message, true); $('status').textContent = 'Viga'; $('status').className = 'badge bad';
  }
}

async function refreshLogs() {
  try { $('logs').textContent = (await api('logs')).logs || 'Sündmusi pole.'; }
  catch (error) { $('logs').textContent = error.message; }
}

function renderDomainChips() {
  $('domain-chips').innerHTML = issueDomains.map((domain, index) => `<span class="chip">${esc(domain)}<button type="button" data-index="${index}" aria-label="Eemalda ${esc(domain)}">×</button></span>`).join('');
  $('domain-chips').querySelectorAll('button').forEach(button => button.onclick = () => { issueDomains.splice(Number(button.dataset.index), 1); renderDomainChips(); });
}
function addDomain() {
  const value = $('domain-input').value.trim().toLowerCase();
  if (!value) return;
  if (!/^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/.test(value)) { notice('Sisesta korrektne domeeninimi.', true); return; }
  if (!issueDomains.includes(value)) issueDomains.push(value);
  $('domain-input').value = ''; renderDomainChips(); $('domain-input').focus();
}
function openIssue(name = '') {
  const cert = certificates.find(item => item.name === name);
  $('issue-title').textContent = cert ? 'Muuda sertifikaadi domeene' : 'Taotle sertifikaat';
  $('cert-name').value = name;
  issueDomains = cert ? [...cert.domains] : [];
  $('domain-input').value = ''; renderDomainChips(); $('issue-dialog').showModal();
  setTimeout(() => $('domain-input').focus(), 50);
}

function currentSynologySettings() {
  return {
    host: $('synology-host').value.trim(), port: Number($('synology-port').value),
    https: $('synology-https').value === 'true', verify_tls: $('synology-verify').checked,
    username: $('synology-username').value.trim(), password: $('synology-password').value,
  };
}
function openSynology() {
  $('synology-host').value = synology.host || '';
  $('synology-port').value = synology.port || 5001;
  $('synology-https').value = String(synology.https !== false);
  $('synology-verify').checked = synology.verify_tls === true;
  $('synology-username').value = synology.username || '';
  $('synology-password').value = '';
  $('synology-test-result').className = 'inline-result hidden';
  $('synology-dialog').showModal();
}

function openDeployment(name) {
  const cert = certificates.find(item => item.name === name);
  if (!cert) return;
  $('deployment-cert').value = name;
  $('deployment-name').textContent = name;
  $('deployment-enabled').checked = cert.synology?.enabled || false;
  $('deployment-description').value = cert.synology?.description || name;
  $('deployment-default').checked = cert.synology?.make_default || false;
  $('deployment-dialog').showModal();
}
function deploymentPayload() {
  return { enabled: $('deployment-enabled').checked, description: $('deployment-description').value.trim(), make_default: $('deployment-default').checked };
}

async function renew(button) {
  const name = button.dataset.name;
  if (!confirm(`Uuendada sertifikaat “${name}” kohe? Let's Encrypt väljastab uue sertifikaadi.`)) return;
  setBusy(button, true, 'Uuendan…');
  try { await api('renew', { name }); notice(`${name} uuendati edukalt.`); await Promise.all([refresh(), refreshLogs()]); }
  catch (error) { notice(error.message, true); }
  finally { setBusy(button, false); }
}
async function removeCertificate(name) {
  const cert = certificates.find(item => item.name === name);
  if (cert?.in_use_by?.length) { notice(`Sertifikaat on Reverse Proxy kasutuses: ${cert.in_use_by.join(', ')}`, true); return; }
  if (!confirm(`Kustutada sertifikaat “${name}” sellest serverist? Synology koopiat ei kustutata.`)) return;
  try { await api('delete', { name }); notice('Sertifikaat kustutati.'); await Promise.all([refresh(), refreshLogs()]); }
  catch (error) { notice(error.message, true); }
}

$('add').onclick = () => openIssue();
$('refresh').onclick = async event => {
  const button = event.currentTarget;
  setBusy(button, true, '↻ Värskendan…');
  try { await Promise.all([refresh(), refreshLogs()]); }
  finally { setBusy(button, false); }
};
$('logs-refresh').onclick = refreshLogs;
$('domain-add').onclick = addDomain;
$('domain-input').onkeydown = event => { if (event.key === 'Enter') { event.preventDefault(); addDomain(); } };
document.querySelectorAll('[data-close]').forEach(button => button.onclick = () => $(button.dataset.close).close());

$('issue-form').onsubmit = async event => {
  event.preventDefault(); addDomain();
  if (!issueDomains.length) { notice('Lisa vähemalt üks domeeninimi.', true); return; }
  const button = event.submitter; setBusy(button, true, 'Taotlen…');
  try {
    await api('issue', { name: $('cert-name').value, domains: issueDomains });
    $('issue-dialog').close(); notice('Sertifikaat väljastati ja paigaldati.'); await Promise.all([refresh(), refreshLogs()]);
  } catch (error) { notice(error.message, true); }
  finally { setBusy(button, false); }
};

$('renewal-toggle').onchange = async event => {
  event.target.disabled = true;
  try { await api('timer_set', { enabled: event.target.checked }); notice(event.target.checked ? 'Automaatne uuendamine on aktiivne.' : 'Automaatne uuendamine on peatatud.'); await refresh(); }
  catch (error) { notice(error.message, true); await refresh(); }
  finally { event.target.disabled = false; }
};
$('renew-all').onclick = async event => {
  const button = event.currentTarget;
  setBusy(button, true, 'Kontrollin…');
  try { await api('renew_all'); notice('Uuenduskontroll lõpetati.'); await Promise.all([refresh(), refreshLogs()]); }
  catch (error) { notice(error.message, true); }
  finally { setBusy(button, false); }
};

$('synology-settings').onclick = openSynology;
$('synology-test').onclick = async event => {
  const button = event.currentTarget;
  const resultBox = $('synology-test-result'); setBusy(button, true, 'Testin…');
  try { const result = await api('synology_test', { settings: currentSynologySettings() }); resultBox.textContent = result.message; resultBox.className = 'inline-result success'; }
  catch (error) { resultBox.textContent = error.message; resultBox.className = 'inline-result error'; }
  finally { setBusy(button, false); }
};
$('synology-form').onsubmit = async event => {
  event.preventDefault(); const button = event.submitter; setBusy(button, true, 'Salvestan…');
  try { await api('synology_save', { settings: currentSynologySettings() }); $('synology-dialog').close(); notice('Synology ühenduse seadistus salvestati.'); await refresh(); }
  catch (error) { notice(error.message, true); }
  finally { setBusy(button, false); }
};

$('deployment-form').onsubmit = async event => {
  event.preventDefault(); const button = event.submitter; setBusy(button, true, 'Salvestan…');
  try { await api('deployment_save', { name: $('deployment-cert').value, deployment: deploymentPayload() }); $('deployment-dialog').close(); notice('Edastuse seadistus salvestati.'); await refresh(); }
  catch (error) { notice(error.message, true); }
  finally { setBusy(button, false); }
};
$('deploy-now').onclick = async event => {
  const button = event.currentTarget;
  const name = $('deployment-cert').value; setBusy(button, true, 'Edastan…');
  try {
    await api('deployment_save', { name, deployment: deploymentPayload() });
    const result = await api('deploy', { name }); $('deployment-dialog').close(); notice(result.message); await Promise.all([refresh(), refreshLogs()]);
  } catch (error) { notice(error.message, true); }
  finally { setBusy(button, false); }
};

refresh(); refreshLogs();
