const GET = [/^\/health$/, /^\/v1\/schema$/, /^\/v1\/model$/, /^\/v1\/capabilities$/,
  /^\/v1\/desktop\/faults$/, /^\/v1\/desktop\/sessions$/, /^\/v1\/desktop\/sessions\/[a-f0-9]{32}\/(window|overview|report)(\?start=\d+&limit=\d+)?$/];
function allowedRequest(method, path) {
  return typeof path === 'string' && path.length < 240 && (method === 'GET' ? GET.some(r => r.test(path)) : method === 'POST' && ['/v1/simulate/bench','/v1/desktop/faults'].includes(path));
}
function trustedURL(value) { try { const u = new URL(value); return u.protocol === 'aerotrace:' && u.host === 'app'; } catch { return false; } }
module.exports = {allowedRequest, trustedURL};
