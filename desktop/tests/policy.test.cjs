const {test}=require('node:test');const assert=require('node:assert/strict');
const {allowedRequest,trustedURL}=require('../electron/policy.cjs');
test('only private reviewed API paths exposed',()=>{
  assert.equal(allowedRequest('GET','/health'),true);
  assert.equal(allowedRequest('POST','/v1/simulate/bench'),true);
  assert.equal(allowedRequest('GET','/v1/desktop/faults'),true);
  assert.equal(allowedRequest('POST','/v1/desktop/faults'),true);
  assert.equal(allowedRequest('DELETE','/v1/desktop/faults'),false);
  for(const p of ['https://example.com','/v1/desktop/import','/v1/telemetry','/health/../secrets','/v1/desktop/sessions/../../file'])assert.equal(allowedRequest('GET',p),false);
  assert.equal(allowedRequest('GET','/v1/desktop/sessions/'+'a'.repeat(32)+'/window?start=0&limit=120'),true);
});
test('IPC origin is the packaged application only',()=>{
  assert.equal(trustedURL('aerotrace://app/index.html'),true);
  for(const p of ['file:///x','https://app','aerotrace://evil/index.html','invalid'])assert.equal(trustedURL(p),false);
});
